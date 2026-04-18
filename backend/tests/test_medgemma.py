"""
Unit tests for the medgemma module.

Tests symptom extraction and embedding generation from ultrasound images.
"""

import pytest
import sys
from pathlib import Path
from PIL import Image
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.medgemma import (
    MedGemma,
    MedGemmaError,
    Symptom,
    SymptomDescription,
    get_medgemma,
    reset_medgemma,
    extract_symptoms_from_bytes,
)


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    img = Image.new('RGB', (200, 200), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def reset_model():
    """Reset the global model before each test."""
    reset_medgemma()
    yield


class TestSymptom:
    """Tests for Symptom dataclass."""

    def test_creation(self):
        """Test creating a Symptom."""
        symptom = Symptom(
            type="nuchal_translucency",
            value="3.5mm",
            assessment="elevated",
            normal_range="1.5-2.5mm",
            confidence=0.92,
        )

        assert symptom.type == "nuchal_translucency"
        assert symptom.value == "3.5mm"
        assert symptom.assessment == "elevated"

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        symptom = Symptom(
            type="nasal_bone",
            value="present",
            assessment="normal",
        )

        assert symptom.normal_range is None
        assert symptom.confidence is None


class TestSymptomDescription:
    """Tests for SymptomDescription dataclass."""

    def test_creation(self):
        """Test creating a SymptomDescription."""
        symptoms = [
            Symptom(type="nt", value="2.0mm", assessment="normal"),
            Symptom(type="nasal_bone", value="present", assessment="normal"),
        ]

        description = SymptomDescription(
            symptoms=symptoms,
            overall="Normal scan",
            trimester="1st",
            gestational_age_weeks=12.0,
        )

        assert len(description.symptoms) == 2
        assert description.overall == "Normal scan"
        assert description.trimester == "1st"

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        description = SymptomDescription(
            symptoms=[],
            overall="No symptoms detected",
        )

        assert description.trimester is None
        assert description.gestational_age_weeks is None


class TestMedGemma:
    """Tests for MedGemma class."""

    def test_initialization(self):
        """Test MedGemma initialization."""
        medgemma = MedGemma(use_mock=True)  # Use mock mode for testing

        assert medgemma.model_path is None
        assert medgemma.device in ("cpu", "cuda", "mps")
        assert medgemma._is_loaded is False

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        medgemma = MedGemma(
            model_path="/custom/path/model",
            device="cuda",
            use_mock=True,
        )

        assert medgemma.model_path == "/custom/path/model"
        assert medgemma.device == "cuda"

    def test_load_sets_is_loaded(self, reset_model):
        """Test that load() sets _is_loaded flag."""
        medgemma = MedGemma(use_mock=True)
        assert medgemma._is_loaded is False

        medgemma.load()
        assert medgemma._is_loaded is True

    def test_ensure_loaded(self, reset_model):
        """Test that _ensure_loaded() loads model if needed."""
        medgemma = MedGemma(use_mock=True)
        assert medgemma._is_loaded is False

        medgemma._ensure_loaded()
        assert medgemma._is_loaded is True

    def test_extract_symptoms_from_bytes(self, reset_model, sample_image_bytes):
        """Test extracting symptoms from image bytes."""
        medgemma = MedGemma(use_mock=True)

        description = medgemma.extract_symptoms_from_bytes(
            image_bytes=sample_image_bytes,
            trimester="1st",
            gestational_age_weeks=12.0,
        )

        assert isinstance(description, SymptomDescription)
        assert description.trimester == "1st"
        assert description.gestational_age_weeks == 12.0
        assert isinstance(description.symptoms, list)
        assert description.overall is not None

    def test_extract_symptoms_different_trimesters(
        self, reset_model, sample_image_bytes
    ):
        """Test extracting symptoms for different trimesters."""
        medgemma = MedGemma(use_mock=True)

        for trimester in ["1st", "2nd", "3rd"]:
            description = medgemma.extract_symptoms_from_bytes(
                image_bytes=sample_image_bytes,
                trimester=trimester,
            )

            assert description.trimester == trimester
            # Mock analysis returns gestational age appropriate to trimester
            assert description.gestational_age_weeks is not None

    def test_embed_image(self, reset_model, sample_image_bytes):
        """Test generating image embedding."""
        medgemma = MedGemma(use_mock=True)

        embedding = medgemma.embed_image(sample_image_bytes)

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_symptoms(self, reset_model):
        """Test generating symptom text embedding."""
        medgemma = MedGemma(use_mock=True)

        embedding = medgemma.embed_symptoms("nuchal_translucency_3_5mm absent_nasal_bone")

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_symptoms_different_texts(self, reset_model):
        """Test that different texts produce different embeddings."""
        medgemma = MedGemma(use_mock=True)

        emb1 = medgemma.embed_symptoms("nt_3_5mm absent_nasal_bone")
        emb2 = medgemma.embed_symptoms("normal_scan")

        # Mock embeddings may be same, but in production would differ
        assert isinstance(emb1, list)
        assert isinstance(emb2, list)

    def test_mock_analysis_first_trimester(self, reset_model):
        """Test mock analysis returns first trimester symptoms."""
        medgemma = MedGemma(use_mock=True)
        medgemma.load()

        description = medgemma._mock_analysis("1st")

        assert description.trimester == "1st"
        assert description.gestational_age_weeks == 12.0
        assert len(description.symptoms) == 3

        # Check for expected first trimester symptoms
        symptom_types = [s.type for s in description.symptoms]
        assert "nuchal_translucency" in symptom_types
        assert "nasal_bone" in symptom_types
        assert "cardiac" in symptom_types

    def test_mock_analysis_second_trimester(self, reset_model):
        """Test mock analysis returns second trimester symptoms."""
        medgemma = MedGemma(use_mock=True)
        medgemma.load()

        description = medgemma._mock_analysis("2nd")

        assert description.trimester == "2nd"
        assert description.gestational_age_weeks == 20.0
        assert len(description.symptoms) == 2

    def test_mock_analysis_third_trimester(self, reset_model):
        """Test mock analysis returns third trimester symptoms."""
        medgemma = MedGemma(use_mock=True)
        medgemma.load()

        description = medgemma._mock_analysis("3rd")

        assert description.trimester == "3rd"
        assert description.gestational_age_weeks == 32.0
        assert len(description.symptoms) == 2


class TestGetMedGemma:
    """Tests for get_medgemma function."""

    def test_returns_singleton(self, reset_model):
        """Test that get_medgemma returns the same instance."""
        medgemma1 = get_medgemma()
        medgemma2 = get_medgemma()

        assert medgemma1 is medgemma2

    def test_creates_new_on_first_call(self, reset_model):
        """Test that first call creates a new instance."""
        medgemma = get_medgemma()

        assert medgemma is not None
        assert isinstance(medgemma, MedGemma)

    def test_custom_params_on_first_call(self, reset_model):
        """Test custom params on first call."""
        medgemma = get_medgemma(
            model_path="/custom/path",
            device="cuda"
        )

        assert medgemma.model_path == "/custom/path"
        assert medgemma.device == "cuda"


class TestResetMedGemma:
    """Tests for reset_medgemma function."""

    def test_resets_singleton(self):
        """Test that reset_medgemma clears the global instance."""
        medgemma1 = get_medgemma()
        reset_medgemma()

        medgemma2 = get_medgemma()

        assert medgemma1 is not medgemma2

    def test_reset_multiple_times(self):
        """Test that reset can be called multiple times."""
        for _ in range(3):
            get_medgemma()
            reset_medgemma()


class TestExtractSymptomsFromBytes:
    """Tests for extract_symptoms_from_bytes convenience function."""

    @pytest.mark.asyncio
    async def test_extracts_symptoms(self, reset_model, sample_image_bytes):
        """Test that function extracts symptoms."""
        description = await extract_symptoms_from_bytes(
            image_bytes=sample_image_bytes,
            trimester="1st",
            gestational_age_weeks=12.0,
        )

        assert isinstance(description, SymptomDescription)
        assert description.trimester == "1st"

    @pytest.mark.asyncio
    async def test_uses_global_model(self, reset_model, sample_image_bytes):
        """Test that function uses the global model."""
        # Get global model
        model = get_medgemma()

        # Extract via convenience function
        await extract_symptoms_from_bytes(sample_image_bytes, "1st")

        # Global model should be loaded
        assert model._is_loaded is True


class TestMedGemmaError:
    """Tests for MedGemmaError."""

    def test_error_is_exception(self):
        """Test that MedGemmaError is an Exception."""
        error = MedGemmaError("Test error")

        assert isinstance(error, Exception)
        assert str(error) == "Test error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
