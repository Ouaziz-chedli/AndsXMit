"""
Unit tests for the image_processor module.

Tests ultrasound image loading, format handling, and metadata extraction.
"""

import pytest
import sys
from pathlib import Path
from PIL import Image
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.image_processor import (
    load_ultrasound_image,
    image_to_bytes,
    _compute_trimester,
    anonymize_dicom,
    get_image_format,
    validate_image,
    UltrasoundMetadata,
)


class TestComputeTrimester:
    """Tests for _compute_trimester function."""

    def test_first_trimester(self):
        """Test first trimester (0-13 weeks)."""
        assert _compute_trimester(11) == "1st"
        assert _compute_trimester(13) == "1st"
        assert _compute_trimester(0) == "1st"

    def test_second_trimester(self):
        """Test second trimester (14-26 weeks)."""
        assert _compute_trimester(14) == "2nd"
        assert _compute_trimester(20) == "2nd"
        assert _compute_trimester(26) == "2nd"

    def test_third_trimester(self):
        """Test third trimester (27+ weeks)."""
        assert _compute_trimester(27) == "3rd"
        assert _compute_trimester(35) == "3rd"
        assert _compute_trimester(40) == "3rd"

    def test_none_input(self):
        """Test that None returns None."""
        assert _compute_trimester(None) is None

    def test_boundary_conditions(self):
        """Test boundary conditions between trimesters."""
        # 1st to 2nd boundary
        assert _compute_trimester(13) == "1st"
        assert _compute_trimester(14) == "2nd"

        # 2nd to 3rd boundary
        assert _compute_trimester(26) == "2nd"
        assert _compute_trimester(27) == "3rd"


class TestGetImageFormat:
    """Tests for get_image_format function."""

    def test_dicom_format(self):
        """Test DICOM format detection."""
        assert get_image_format("image.dcm") == "dicom"
        assert get_image_format("image.dicom") == "dicom"
        assert get_image_format("path/to/file.DCM") == "dicom"

    def test_jpeg_format(self):
        """Test JPEG format detection."""
        assert get_image_format("image.jpg") == "jpeg"
        assert get_image_format("image.jpeg") == "jpeg"
        assert get_image_format("image.JPG") == "jpeg"

    def test_png_format(self):
        """Test PNG format detection."""
        assert get_image_format("image.png") == "png"
        assert get_image_format("image.PNG") == "png"

    def test_unknown_format(self):
        """Test unknown format detection."""
        assert get_image_format("image.tiff") == "unknown"
        assert get_image_format("image.bmp") == "unknown"
        assert get_image_format("image") == "unknown"


class TestValidateImage:
    """Tests for validate_image function."""

    def test_valid_image(self):
        """Test validation of valid image."""
        # Create a test image
        img = Image.new('RGB', (256, 256), color='white')
        assert validate_image(img) is True

    def test_min_size_image(self):
        """Test validation of minimum size image."""
        # Create a 64x64 image (minimum)
        img = Image.new('RGB', (64, 64), color='white')
        assert validate_image(img) is True

    def test_too_small_width(self):
        """Test rejection of image too small (width)."""
        img = Image.new('RGB', (32, 100), color='white')
        assert validate_image(img) is False

    def test_too_small_height(self):
        """Test rejection of image too small (height)."""
        img = Image.new('RGB', (100, 32), color='white')
        assert validate_image(img) is False

    def test_none_image(self):
        """Test rejection of None."""
        assert validate_image(None) is False

    def test_grayscale_mode(self):
        """Test that grayscale mode is valid."""
        img = Image.new('L', (128, 128), color=128)
        assert validate_image(img) is True

    def test_palette_mode(self):
        """Test that palette mode is not valid."""
        img = Image.new('P', (128, 128))
        assert validate_image(img) is False


class TestImageToBytes:
    """Tests for image_to_bytes function."""

    def test_rgb_to_png(self):
        """Test converting RGB image to PNG bytes."""
        img = Image.new('RGB', (100, 100), color='red')
        bytes_data = image_to_bytes(img, format="PNG")

        assert isinstance(bytes_data, bytes)
        assert len(bytes_data) > 0

        # Verify it can be loaded back
        loaded = Image.open(io.BytesIO(bytes_data))
        assert loaded.size == (100, 100)

    def test_jpeg_format(self):
        """Test JPEG format output."""
        img = Image.new('RGB', (100, 100), color='blue')
        bytes_data = image_to_bytes(img, format="JPEG")

        assert isinstance(bytes_data, bytes)
        assert len(bytes_data) > 0

    def test_default_format(self):
        """Test default PNG format."""
        img = Image.new('RGB', (50, 50))
        bytes_data = image_to_bytes(img)

        # Should default to PNG
        assert isinstance(bytes_data, bytes)


class TestAnonymizeDicom:
    """Tests for anonymize_dicom function."""

    def test_remove_patient_name(self):
        """Test removal of patient name."""
        # Create mock DICOM dataset
        class MockDataset:
            def __init__(self):
                self.PatientName = "John Doe"
                self.PatientID = "12345"
                self.PatientBirthDate = "19900101"
                self.StudyDescription = "US Abdomen"
                self.Manufacturer = "GE Healthcare"

        ds = MockDataset()
        anonymized = anonymize_dicom(ds)

        assert anonymized.PatientName is None
        assert anonymized.PatientID is None
        assert anonymized.PatientBirthDate is None

        # Non-PII fields should remain
        assert anonymized.StudyDescription == "US Abdomen"
        assert anonymized.Manufacturer == "GE Healthcare"

    def test_set_endian_flags(self):
        """Test that endian flags are set."""
        class MockDataset:
            pass

        ds = MockDataset()
        anonymized = anonymize_dicom(ds)

        assert anonymized.is_little_endian is True
        assert anonymized.is_implicit_VR is True


class TestUltrasoundMetadata:
    """Tests for UltrasoundMetadata dataclass."""

    def test_creation(self):
        """Test creation of metadata object."""
        metadata = UltrasoundMetadata(
            gestational_age_weeks=12,
            trimester="1st",
            acquisition_date="20230101",
            patient_age=30,
            study_description="NT scan",
            manufacturer="GE",
            modality="US",
        )

        assert metadata.gestational_age_weeks == 12
        assert metadata.trimester == "1st"
        assert metadata.acquisition_date == "20230101"

    def test_all_optional_fields(self):
        """Test creation with all optional fields."""
        metadata = UltrasoundMetadata()

        assert metadata.gestational_age_weeks is None
        assert metadata.trimester is None
        assert metadata.acquisition_date is None


class TestLoadUltrasoundImage:
    """Integration tests for load_ultrasound_image."""

    @pytest.fixture
    def temp_image_file(self, tmp_path):
        """Create a temporary test image file."""
        img = Image.new('RGB', (200, 200), color='white')
        file_path = tmp_path / "test_image.png"
        img.save(file_path)
        return str(file_path)

    def test_load_png(self, temp_image_file):
        """Test loading PNG file."""
        image, metadata = load_ultrasound_image(temp_image_file)

        assert isinstance(image, Image.Image)
        assert image.mode == 'RGB'
        assert isinstance(metadata, UltrasoundMetadata)

    def test_non_dicom_metadata(self, tmp_path):
        """Test that non-DICOM files have minimal metadata."""
        img = Image.new('RGB', (100, 100), color='white')
        file_path = tmp_path / "test.jpg"
        img.save(file_path)

        image, metadata = load_ultrasound_image(str(file_path))

        assert metadata.gestational_age_weeks is None
        assert metadata.trimester is None
        assert metadata.acquisition_date is None

    def test_rgb_conversion(self, tmp_path):
        """Test that image is converted to RGB."""
        # Create grayscale image
        img = Image.new('L', (100, 100), color=128)
        file_path = tmp_path / "test.png"
        img.save(file_path)

        image, _ = load_ultrasound_image(str(file_path))

        assert image.mode == 'RGB'

    def test_invalid_format(self, tmp_path):
        """Test that invalid format raises error."""
        file_path = tmp_path / "test.tiff"
        file_path.write_text("fake data")

        with pytest.raises(ValueError, match="Unsupported image format"):
            load_ultrasound_image(str(file_path))

    def test_file_not_found(self):
        """Test that missing file raises error."""
        with pytest.raises(FileNotFoundError):
            load_ultrasound_image("/nonexistent/path/image.png")


# Import io for image loading test
import io


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
