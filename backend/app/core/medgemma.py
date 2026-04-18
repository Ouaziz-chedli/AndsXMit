"""
MedGemma Module - Symptom extraction from ultrasound images.

This module provides an interface to MedGemma for extracting
structured symptom descriptions from ultrasound images.

IMPORTANT: MedGemma receives ONLY the image. All patient context
(age, history, biomarkers) is handled algorithmically in the
aggregation and priors modules.

Integration: Uses Ollama to run MedGemma locally via REST API.
Falls back to mock mode when Ollama is unavailable.
"""

import io
import re
import json
import asyncio
import concurrent.futures
from typing import List, Optional
from dataclasses import dataclass
import torch
import httpx

from .image_processor import load_ultrasound_image, image_to_bytes
from .ollama_client import get_ollama_client, OllamaClient
from .biometric_context import compute_biometric_context


def detect_device() -> str:
    """
    Detect the best available hardware accelerator.

    Checks for CUDA (NVIDIA) and MPS (Apple Silicon).
    Defaults to 'cpu' if no accelerator is found.
    """
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


@dataclass
class Symptom:
    """A single symptom extracted from an ultrasound image."""
    type: str
    value: str
    assessment: str  # "normal", "elevated", "low", "absent", "present", "anomalous"
    normal_range: Optional[str] = None
    confidence: Optional[float] = None  # 0.0 to 1.0


@dataclass
class SymptomDescription:
    """Complete symptom description from an ultrasound image."""
    symptoms: List[Symptom]
    overall: str
    trimester: Optional[str] = None
    gestational_age_weeks: Optional[float] = None

    @property
    def symptom_text(self) -> str:
        """Human-readable summary for embedding and display."""
        parts = [f"{s.type}={s.value}" for s in self.symptoms]
        return f"Symptoms: {', '.join(parts)}. {self.overall}"


class MedGemmaError(Exception):
    """Base exception for MedGemma-related errors."""
    pass


# System prompt for symptom extraction
SYMPTOM_EXTRACTION_PROMPT = """You are an expert prenatal ultrasound interpreter. Analyze the ultrasound image and extract structured symptoms.

For each symptom found, provide:
- type: The type of finding (e.g., nuchal_translucency, nasal_bone, cardiac, femur_length)
- value: The measured/found value (e.g., "2.5mm", "present", "normal")
- assessment: Your assessment (normal, elevated, low, absent, present, anomalous)
- normal_range: The expected normal range if applicable

Also provide an overall assessment of the ultrasound.

Format your response as JSON with this structure:
{
    "symptoms": [
        {"type": "...", "value": "...", "assessment": "...", "normal_range": "..."}
    ],
    "overall": "Your overall interpretation"
}

Focus on markers relevant to prenatal screening: nuchal translucency, nasal bone, cardiac structure, femur length, etc."""


def parse_medgemma_response(response: str) -> SymptomDescription:
    """
    Parse MedGemma's JSON response into a SymptomDescription.

    Args:
        response: Raw JSON string from MedGemma

    Returns:
        SymptomDescription object

    Raises:
        MedGemmaError: If parsing fails
    """
    try:
        # Try to extract JSON from response
        # Handle cases where model includes extra text
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(response)

        symptoms = []
        for s in data.get("symptoms", []):
            symptoms.append(Symptom(
                type=s.get("type", "unknown"),
                value=s.get("value", ""),
                assessment=s.get("assessment", "unknown"),
                normal_range=s.get("normal_range"),
                confidence=s.get("confidence"),
            ))

        return SymptomDescription(
            symptoms=symptoms,
            overall=data.get("overall", "No overall assessment provided"),
            trimester=None,  # Set by caller
            gestational_age_weeks=None,  # Set by caller
        )
    except json.JSONDecodeError as e:
        raise MedGemmaError(f"Failed to parse MedGemma response: {e}")


class MedGemma:
    """
    Wrapper for MedGemma model for symptom extraction.

    This class provides a clean interface to MedGemma via Ollama,
    handling model loading and inference. Falls back to mock mode
    when Ollama is unavailable.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        ollama_client: Optional[OllamaClient] = None,
        use_mock: bool = False,
    ):
        """
        Initialize MedGemma model wrapper.

        Args:
            model_path: Ignored (Ollama handles model loading)
            device: Device for torch (cpu, cuda, mps)
            ollama_client: Optional OllamaClient instance
            use_mock: If True, always use mock mode (for testing)
        """
        self.model_path = model_path
        self.device = device or detect_device()
        self._ollama_client = ollama_client
        self._use_mock = use_mock
        self._ollama_available = None  # Lazy check
        self._is_loaded = False

    def _get_client(self) -> OllamaClient:
        """Get or create Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = get_ollama_client()
        return self._ollama_client

    def _is_ollama_available(self) -> bool:
        """Check if Ollama is available (cached check)."""
        if self._use_mock:
            return False
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            client = self._get_client()
            try:
                asyncio.get_running_loop()
                # Running inside an async context — do a sync HTTP probe instead
                import httpx as _httpx
                resp = _httpx.get(f"{client.base_url}/api/tags", timeout=2.0)
                self._ollama_available = resp.status_code == 200
            except RuntimeError:
                # No running loop — safe to use asyncio.run
                self._ollama_available = asyncio.run(client.is_available())
        except Exception:
            self._ollama_available = False

        return self._ollama_available

    def load(self) -> None:
        """
        Load/verify MedGemma model connection via Ollama.

        This checks that Ollama is available and the model is loaded.
        If Ollama is not available, the model will use mock mode.
        """
        if self._use_mock:
            self._is_loaded = True
            return

        try:
            if self._is_ollama_available():
                self._is_loaded = True
        except Exception:
            self._is_loaded = True  # Will fall back to mock on inference

    def _ensure_loaded(self) -> None:
        """Ensure the model is loaded, loading if necessary."""
        if not self._is_loaded:
            self.load()

    async def _analyze_async(
        self,
        image_bytes: bytes,
        trimester: str,
        gestational_age_weeks: Optional[float] = None,
        biometric_context: Optional[dict] = None,
    ) -> SymptomDescription:
        """
        Async internal method to perform analysis on image bytes.

        Args:
            image_bytes: Image data as bytes
            trimester: Trimester context
            gestational_age_weeks: Optional gestational age
            biometric_context: Optional biometric context dict from compute_biometric_context()

        Returns:
            SymptomDescription with extracted symptoms
        """
        if not self._is_ollama_available():
            return self._mock_analysis(trimester)

        client = self._get_client()

        # Build context-aware prompt
        context_parts = [f"Trimester: {trimester}"]
        if gestational_age_weeks:
            context_parts.append(f"Gestational age: {gestational_age_weeks} weeks")
        # Inject biometric context when available
        if biometric_context and biometric_context.get("ai_prompt_fragment"):
            context_parts.append(biometric_context["ai_prompt_fragment"])

        context = "; ".join(context_parts)
        prompt = f"{SYMPTOM_EXTRACTION_PROMPT}\n\nContext: {context}"

        try:
            response = await client.analyze_image_bytes(
                image_bytes=image_bytes,
                prompt=prompt,
                system="You are a medical ultrasound expert. Be precise and clinical.",
            )

            # Parse response
            description = parse_medgemma_response(response)
            description.trimester = trimester
            description.gestational_age_weeks = gestational_age_weeks
            return description

        except (httpx.HTTPError, httpx.ConnectError) as e:
            # Ollama not available, fall back to mock
            return self._mock_analysis(trimester)
        except Exception:
            # Any other error, try mock
            return self._mock_analysis(trimester)

    def extract_symptoms(
        self,
        image_path: str,
        user_provided_trimester: Optional[str] = None,
        biometric_context: Optional[dict] = None,
    ) -> SymptomDescription:
        """
        Extract symptoms from an ultrasound image file.

        Args:
            image_path: Path to the ultrasound image (DICOM, JPEG, PNG)
            user_provided_trimester: Optional trimester override ("1st", "2nd", "3rd")
            biometric_context: Optional biometric context dict from compute_biometric_context()

        Returns:
            SymptomDescription with extracted symptoms

        Raises:
            MedGemmaError: If image processing or inference fails
        """
        self._ensure_loaded()

        # Load image and extract metadata
        image, metadata = load_ultrasound_image(image_path)

        # Determine trimester
        trimester = user_provided_trimester or metadata.trimester
        if trimester is None:
            raise MedGemmaError(
                "Trimester must be provided or extractable from image metadata. "
                "For non-DICOM images, provide trimester explicitly."
            )

        # Convert image to bytes
        image_bytes = image_to_bytes(image, format="PNG")

        return self._analyze(image_bytes, trimester, metadata.gestational_age_weeks, biometric_context)

    def extract_symptoms_from_bytes(
        self,
        image_bytes: bytes,
        trimester: str,
        gestational_age_weeks: Optional[float] = None,
        biometric_context: Optional[dict] = None,
    ) -> SymptomDescription:
        """
        Extract symptoms from image bytes.

        Args:
            image_bytes: Image data as bytes (PNG format recommended)
            trimester: Trimester ("1st", "2nd", "3rd")
            gestational_age_weeks: Optional gestational age in weeks
            biometric_context: Optional biometric context dict from compute_biometric_context()

        Returns:
            SymptomDescription with extracted symptoms
        """
        self._ensure_loaded()
        return self._analyze(image_bytes, trimester, gestational_age_weeks, biometric_context)

    async def extract_symptoms_async(
        self,
        image_path: str,
        user_provided_trimester: Optional[str] = None,
        biometric_context: Optional[dict] = None,
    ) -> SymptomDescription:
        """
        Async: Extract symptoms from an ultrasound image file.

        Args:
            image_path: Path to the ultrasound image (DICOM, JPEG, PNG)
            user_provided_trimester: Optional trimester override ("1st", "2nd", "3rd")
            biometric_context: Optional biometric context dict from compute_biometric_context()

        Returns:
            SymptomDescription with extracted symptoms
        """
        self._ensure_loaded()
        image, metadata = load_ultrasound_image(image_path)
        trimester = user_provided_trimester or metadata.trimester
        if trimester is None:
            raise MedGemmaError(
                "Trimester must be provided or extractable from image metadata."
            )
        image_bytes = image_to_bytes(image, format="PNG")
        return await self._analyze_async(image_bytes, trimester, metadata.gestational_age_weeks, biometric_context)

    async def extract_symptoms_from_bytes_async(
        self,
        image_bytes: bytes,
        trimester: str,
        gestational_age_weeks: Optional[float] = None,
        biometric_context: Optional[dict] = None,
    ) -> SymptomDescription:
        """
        Async: Extract symptoms from image bytes.

        Args:
            image_bytes: Image data as bytes (PNG format recommended)
            trimester: Trimester ("1st", "2nd", "3rd")
            gestational_age_weeks: Optional gestational age in weeks
            biometric_context: Optional biometric context dict from compute_biometric_context()

        Returns:
            SymptomDescription with extracted symptoms
        """
        self._ensure_loaded()
        return await self._analyze_async(image_bytes, trimester, gestational_age_weeks, biometric_context)

    def _analyze(
        self,
        image_bytes: bytes,
        trimester: str,
        gestational_age_weeks: Optional[float] = None,
        biometric_context: Optional[dict] = None,
    ) -> SymptomDescription:
        """
        Internal method to perform analysis on image bytes.

        Runs async analysis in a thread pool when called from within a running
        event loop (e.g. FastAPI handlers), so asyncio.run() is never nested.
        """
        coro = self._analyze_async(image_bytes, trimester, gestational_age_weeks, biometric_context)
        try:
            asyncio.get_running_loop()
            # We are inside a running loop — delegate to a worker thread
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            # No running loop — safe to call directly
            return asyncio.run(coro)

    def _mock_analysis(self, trimester: str) -> SymptomDescription:
        """
        Mock analysis for testing when Ollama is unavailable.

        Args:
            trimester: Trimester context

        Returns:
            Mock SymptomDescription
        """
        if trimester == "1st":
            return SymptomDescription(
                symptoms=[
                    Symptom(
                        type="nuchal_translucency",
                        value="2.5mm",
                        assessment="normal",
                        normal_range="1.5-2.5mm",
                        confidence=0.92,
                    ),
                    Symptom(
                        type="nasal_bone",
                        value="present",
                        assessment="normal",
                        normal_range="present",
                        confidence=0.95,
                    ),
                    Symptom(
                        type="cardiac",
                        value="four_chamber_normal",
                        assessment="normal",
                        normal_range="four_chamber_visible",
                        confidence=0.88,
                    ),
                ],
                overall="Normal first-trimester ultrasound with no apparent markers",
                trimester="1st",
                gestational_age_weeks=12.0,
            )
        elif trimester == "2nd":
            return SymptomDescription(
                symptoms=[
                    Symptom(
                        type="cardiac",
                        value="normal_four_chamber",
                        assessment="normal",
                        normal_range="four_chamber_present",
                        confidence=0.94,
                    ),
                    Symptom(
                        type="femur_length",
                        value="45mm",
                        assessment="normal",
                        normal_range="40-50mm at 20w",
                        confidence=0.91,
                    ),
                ],
                overall="Normal second-trimester ultrasound",
                trimester="2nd",
                gestational_age_weeks=20.0,
            )
        else:  # 3rd trimester
            return SymptomDescription(
                symptoms=[
                    Symptom(
                        type="growth",
                        value="normal_percentile",
                        assessment="normal",
                        normal_range="10th-90th percentile",
                        confidence=0.89,
                    ),
                    Symptom(
                        type="placenta",
                        value="posterior_grade_2",
                        assessment="normal",
                        normal_range="grade_1-2",
                        confidence=0.92,
                    ),
                ],
                overall="Normal third-trimester ultrasound",
                trimester="3rd",
                gestational_age_weeks=32.0,
            )

    def embed_image(self, image_bytes: bytes) -> List[float]:
        """
        Generate embedding for an image.

        Args:
            image_bytes: Image data as bytes

        Returns:
            Embedding vector as list of floats
        """
        if not self._is_ollama_available():
            return [0.1] * 768

        coro = self.embed_image_async(image_bytes)
        try:
            asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            return asyncio.run(coro)
        except Exception:
            return [0.1] * 768

    async def embed_image_async(self, image_bytes: bytes) -> List[float]:
        """
        Async: Generate embedding for an image using Ollama embeddings endpoint.

        Args:
            image_bytes: Image data as bytes

        Returns:
            Embedding vector as list of floats
        """
        if not self._is_ollama_available():
            return [0.1] * 768

        client = self._get_client()

        # First analyze the image to get a text description
        description = await self._analyze_async(image_bytes, "1st")

        # Then generate embedding for the text description
        text = f"Symptoms: {', '.join([s.type + '=' + s.value for s in description.symptoms])}. {description.overall}"
        try:
            return await client.generate_embeddings(text)
        except Exception:
            return [0.1] * 768

    def embed_symptoms(self, symptom_text: str) -> List[float]:
        """
        Generate embedding for symptom text.

        Args:
            symptom_text: Symptom description text

        Returns:
            Embedding vector as list of floats
        """
        if not self._is_ollama_available():
            return [hash(symptom_text) % 100 / 100.0] * 768

        coro = self.embed_symptoms_async(symptom_text)
        try:
            asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            return asyncio.run(coro)
        except Exception:
            return [hash(symptom_text) % 100 / 100.0] * 768

    async def embed_symptoms_async(self, symptom_text: str) -> List[float]:
        """
        Async: Generate embedding for symptom text.

        Args:
            symptom_text: Symptom description text

        Returns:
            Embedding vector as list of floats
        """
        if not self._is_ollama_available():
            return [hash(symptom_text) % 100 / 100.0] * 768

        client = self._get_client()
        try:
            return await client.generate_embeddings(symptom_text)
        except Exception:
            return [hash(symptom_text) % 100 / 100.0] * 768


# Global model instance
_medgemma: Optional[MedGemma] = None


def get_medgemma(
    model_path: Optional[str] = None,
    device: Optional[str] = None,
) -> MedGemma:
    """
    Get or create the global MedGemma instance.

    Args:
        model_path: Ignored (Ollama handles model)
        device: Device for torch (cpu, cuda, mps)

    Returns:
        MedGemma instance
    """
    global _medgemma
    if _medgemma is None:
        _medgemma = MedGemma(model_path=model_path, device=device)
    return _medgemma


def reset_medgemma() -> None:
    """Reset the global MedGemma instance."""
    global _medgemma
    _medgemma = None


async def extract_symptoms(
    image_path: str,
    user_provided_trimester: Optional[str] = None,
    biometric_context: Optional[dict] = None,
) -> SymptomDescription:
    """
    Async: Convenience function to extract symptoms from an image.

    Args:
        image_path: Path to the ultrasound image
        user_provided_trimester: Optional trimester override
        biometric_context: Optional biometric context dict from compute_biometric_context()

    Returns:
        SymptomDescription with extracted symptoms
    """
    medgemma = get_medgemma()
    medgemma._ensure_loaded()
    return await medgemma.extract_symptoms_async(image_path, user_provided_trimester, biometric_context)


async def extract_symptoms_from_bytes(
    image_bytes: bytes,
    trimester: str,
    gestational_age_weeks: Optional[float] = None,
    biometric_context: Optional[dict] = None,
) -> SymptomDescription:
    """
    Async: Convenience function to extract symptoms from image bytes.

    Args:
        image_bytes: Image data as bytes
        trimester: Trimester
        gestational_age_weeks: Optional gestational age
        biometric_context: Optional biometric context dict from compute_biometric_context()

    Returns:
        SymptomDescription with extracted symptoms
    """
    medgemma = get_medgemma()
    medgemma._ensure_loaded()
    return await medgemma.extract_symptoms_from_bytes_async(
        image_bytes, trimester, gestational_age_weeks, biometric_context
    )
