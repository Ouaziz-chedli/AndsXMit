"""
MedGemma Module - Symptom extraction from ultrasound images.

This module provides an interface to MedGemma for extracting
structured symptom descriptions from ultrasound images.

IMPORTANT: MedGemma receives ONLY the image. All patient context
(age, history, biomarkers) is handled algorithmically in the
aggregation and priors modules.
"""

import io
from typing import List, Optional, Union
from dataclasses import dataclass
from .image_processor import load_ultrasound_image, image_to_bytes


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


class MedGemmaError(Exception):
    """Base exception for MedGemma-related errors."""
    pass


class MedGemma:
    """
    Wrapper for MedGemma model for symptom extraction.

    This class provides a clean interface to MedGemma, handling
    model loading and inference.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        Initialize MedGemma model.

        Args:
            model_path: Path to MedGemma model weights (if None, uses default)
            device: Device to run inference on ("cpu", "cuda", etc.)
        """
        self.model_path = model_path
        self.device = device
        self._model = None
        self._is_loaded = False

    def load(self) -> None:
        """
        Load the MedGemma model.

        This method should be called before any inference.
        """
        # TODO: Implement actual MedGemma model loading
        # For now, this is a placeholder
        self._is_loaded = True

    def _ensure_loaded(self) -> None:
        """Ensure the model is loaded, loading if necessary."""
        if not self._is_loaded:
            self.load()

    def extract_symptoms(
        self,
        image_path: str,
        user_provided_trimester: Optional[str] = None
    ) -> SymptomDescription:
        """
        Extract symptoms from an ultrasound image file.

        Args:
            image_path: Path to the ultrasound image (DICOM, JPEG, PNG)
            user_provided_trimester: Optional trimester override ("1st", "2nd", "3rd")

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

        # Perform inference
        return self._analyze(image_bytes, trimester, metadata.gestational_age_weeks)

    def extract_symptoms_from_bytes(
        self,
        image_bytes: bytes,
        trimester: str,
        gestational_age_weeks: Optional[float] = None
    ) -> SymptomDescription:
        """
        Extract symptoms from image bytes.

        Args:
            image_bytes: Image data as bytes (PNG format recommended)
            trimester: Trimester ("1st", "2nd", "3rd")
            gestational_age_weeks: Optional gestational age in weeks

        Returns:
            SymptomDescription with extracted symptoms
        """
        self._ensure_loaded()
        return self._analyze(image_bytes, trimester, gestational_age_weeks)

    def _analyze(
        self,
        image_bytes: bytes,
        trimester: str,
        gestational_age_weeks: Optional[float] = None
    ) -> SymptomDescription:
        """
        Internal method to perform analysis on image bytes.

        Args:
            image_bytes: Image data as bytes
            trimester: Trimester
            gestational_age_weeks: Optional gestational age

        Returns:
            SymptomDescription with extracted symptoms
        """
        # TODO: Implement actual MedGemma inference
        # For now, return a mock response for testing
        return self._mock_analysis(trimester)

    def _mock_analysis(self, trimester: str) -> SymptomDescription:
        """
        Mock analysis for testing purposes.

        Returns simulated symptom descriptions for development/testing.

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
                        confidence=0.92
                    ),
                    Symptom(
                        type="nasal_bone",
                        value="present",
                        assessment="normal",
                        normal_range="present",
                        confidence=0.95
                    ),
                    Symptom(
                        type="cardiac",
                        value="four_chamber_normal",
                        assessment="normal",
                        normal_range="four_chamber_visible",
                        confidence=0.88
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
                        confidence=0.94
                    ),
                    Symptom(
                        type="femur_length",
                        value="45mm",
                        assessment="normal",
                        normal_range="40-50mm at 20w",
                        confidence=0.91
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
                        confidence=0.89
                    ),
                    Symptom(
                        type="placenta",
                        value="posterior_grade_2",
                        assessment="normal",
                        normal_range="grade_1-2",
                        confidence=0.92
                    ),
                ],
                overall="Normal third-trimester ultrasound",
                trimester="3rd",
                gestational_age_weeks=32.0,
            )

    def embed_image(self, image_bytes: bytes) -> List[float]:
        """
        Generate embedding for an image.

        Used for vector similarity search.

        Args:
            image_bytes: Image data as bytes

        Returns:
            Embedding vector as list of floats
        """
        self._ensure_loaded()

        # TODO: Implement actual MedGemma embedding extraction
        # For now, return a mock embedding
        return [0.1] * 768  # Example embedding dimension

    def embed_symptoms(self, symptom_text: str) -> List[float]:
        """
        Generate embedding for symptom text.

        Used for vector similarity search.

        Args:
            symptom_text: Symptom description text

        Returns:
            Embedding vector as list of floats
        """
        self._ensure_loaded()

        # TODO: Implement actual MedGemma text embedding
        # For now, return a mock embedding based on text
        return [hash(symptom_text) % 100 / 100.0] * 768


# Global model instance
_medgemma: Optional[MedGemma] = None


def get_medgemma(
    model_path: Optional[str] = None,
    device: str = "cpu"
) -> MedGemma:
    """
    Get or create the global MedGemma instance.

    Args:
        model_path: Path to MedGemma model weights
        device: Device to run inference on

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
    user_provided_trimester: Optional[str] = None
) -> SymptomDescription:
    """
    Convenience function to extract symptoms from an image.

    Args:
        image_path: Path to the ultrasound image
        user_provided_trimester: Optional trimester override

    Returns:
        SymptomDescription with extracted symptoms
    """
    medgemma = get_medgemma()
    return medgemma.extract_symptoms(image_path, user_provided_trimester)


async def extract_symptoms_from_bytes(
    image_bytes: bytes,
    trimester: str,
    gestational_age_weeks: Optional[float] = None
) -> SymptomDescription:
    """
    Convenience function to extract symptoms from image bytes.

    Args:
        image_bytes: Image data as bytes
        trimester: Trimester
        gestational_age_weeks: Optional gestational age

    Returns:
        SymptomDescription with extracted symptoms
    """
    medgemma = get_medgemma()
    return medgemma.extract_symptoms_from_bytes(
        image_bytes,
        trimester,
        gestational_age_weeks
    )
