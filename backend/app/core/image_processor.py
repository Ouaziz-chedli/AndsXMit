"""
Image Processor Module - Handle ultrasound image formats.

Supports DICOM, JPEG, and PNG formats commonly used in medical imaging.
Extracts metadata from DICOM files for clinical context.
"""

import io
import numpy as np
from PIL import Image
from pydicom import dcmread
from pydicom.dataset import Dataset
from dataclasses import dataclass
from typing import Literal, Optional, Tuple


@dataclass
class UltrasoundMetadata:
    """Metadata extracted from ultrasound images."""
    gestational_age_weeks: Optional[int] = None
    trimester: Optional[Literal["1st", "2nd", "3rd"]] = None
    acquisition_date: Optional[str] = None
    patient_age: Optional[int] = None
    study_description: Optional[str] = None
    manufacturer: Optional[str] = None
    modality: Optional[str] = None


def load_ultrasound_image(filepath: str) -> Tuple[Image.Image, UltrasoundMetadata]:
    """
    Load an ultrasound image and extract metadata.

    Args:
        filepath: Path to the image file

    Returns:
        Tuple of (PIL Image, UltrasoundMetadata)

    Raises:
        ValueError: If the file format is not supported
        FileNotFoundError: If the file doesn't exist
    """
    ext = filepath.lower().split('.')[-1]

    if ext in ('dcm', 'dicom'):
        return _load_dicom(filepath)
    elif ext in ('jpg', 'jpeg', 'png'):
        return _load_conventional(filepath)
    else:
        raise ValueError(f"Unsupported image format: {ext}. "
                      f"Supported formats: DICOM, JPEG, PNG")


def _load_dicom(filepath: str) -> Tuple[Image.Image, UltrasoundMetadata]:
    """
    Load a DICOM file and extract metadata.

    Args:
        filepath: Path to the DICOM file

    Returns:
        Tuple of (PIL Image, UltrasoundMetadata)
    """
    ds = dcmread(filepath)

    # Extract gestational age
    gestational_age = _extract_gestational_age(ds)
    trimester = _compute_trimester(gestational_age)

    # Extract patient age
    patient_age = None
    if hasattr(ds, 'PatientAge'):
        age_str = ds.PatientAge
        # Format is usually "0XXY" or "0XXM" or "0XXD" for Years, Months, Days
        if len(age_str) > 1 and age_str[-1].isdigit():
            patient_age = int(age_str[:-1])
        else:
            unit = age_str[-1]
            value = int(age_str[:-1])
            if unit == 'Y':
                patient_age = value
            elif unit == 'M':
                patient_age = value // 12
            elif unit == 'D':
                patient_age = value // 365

    # Extract acquisition date
    acquisition_date = None
    if hasattr(ds, 'StudyDate'):
        acquisition_date = str(ds.StudyDate)

    # Extract study description
    study_description = None
    if hasattr(ds, 'StudyDescription'):
        study_description = ds.StudyDescription

    # Extract manufacturer
    manufacturer = None
    if hasattr(ds, 'Manufacturer'):
        manufacturer = ds.Manufacturer

    # Extract modality
    modality = None
    if hasattr(ds, 'Modality'):
        modality = ds.Modality

    metadata = UltrasoundMetadata(
        gestational_age_weeks=gestational_age,
        trimester=trimester,
        acquisition_date=acquisition_date,
        patient_age=patient_age,
        study_description=study_description,
        manufacturer=manufacturer,
        modality=modality,
    )

    # Convert pixel array to image
    pixel_array = ds.pixel_array

    # Normalize pixel values to 0-255
    if pixel_array.dtype != np.uint8:
        pixel_array = ((pixel_array - pixel_array.min()) /
                       (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)

    image = Image.fromarray(pixel_array)

    # Ensure RGB format
    if image.mode != 'RGB':
        image = image.convert('RGB')

    return image, metadata


def _load_conventional(filepath: str) -> Tuple[Image.Image, UltrasoundMetadata]:
    """
    Load a conventional image file (JPEG, PNG).

    Args:
        filepath: Path to the image file

    Returns:
        Tuple of (PIL Image, UltrasoundMetadata)
    """
    image = Image.open(filepath)

    # Ensure RGB format
    if image.mode != 'RGB':
        image = image.convert('RGB')

    metadata = UltrasoundMetadata(
        gestational_age_weeks=None,
        trimester=None,
        acquisition_date=None,
        patient_age=None,
        study_description=None,
        manufacturer=None,
        modality=None,
    )

    return image, metadata


def _extract_gestational_age(ds: Dataset) -> Optional[int]:
    """
    Extract gestational age from DICOM dataset.

    Looks for common DICOM tags for gestational age.

    Args:
        ds: DICOM dataset

    Returns:
        Gestational age in weeks, or None if not found
    """
    gestational_age_tags = [
        'GestationalAge',
        'GestationalAgeSample',
        'ClinicalTrialTimePoint',
    ]

    for tag in gestational_age_tags:
        if hasattr(ds, tag):
            try:
                value = getattr(ds, tag)
                # Handle different formats (string, float, int)
                if isinstance(value, str):
                    # Try to parse numeric value
                    value = float(''.join(c for c in value if c.isdigit() or c == '.'))
                return int(float(value))
            except (ValueError, TypeError, AttributeError):
                continue

    return None


def _compute_trimester(
    gestational_age_weeks: Optional[int]
) -> Optional[Literal["1st", "2nd", "3rd"]]:
    """
    Compute trimester from gestational age.

    Args:
        gestational_age_weeks: Gestational age in weeks

    Returns:
        Trimester ("1st", "2nd", or "3rd"), or None if age is None
    """
    if gestational_age_weeks is None:
        return None

    if gestational_age_weeks <= 13:
        return "1st"
    elif gestational_age_weeks <= 26:
        return "2nd"
    else:
        return "3rd"


def image_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    """
    Convert PIL Image to bytes.

    Args:
        image: PIL Image object
        format: Output format (PNG, JPEG, etc.)

    Returns:
        Image data as bytes
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return buffer.read()


def anonymize_dicom(ds: Dataset) -> Dataset:
    """
    Remove personally identifiable information (PII) from DICOM dataset.

    Args:
        ds: DICOM dataset

    Returns:
        Anonymized DICOM dataset
    """
    # Common PII fields in DICOM
    pii_fields = [
        'PatientName',
        'PatientID',
        'PatientBirthDate',
        'PatientSex',
        'PatientAddress',
        'PatientTelephoneNumbers',
        'OtherPatientIDs',
        'OtherPatientNames',
        'PatientMotherBirthName',
        'StudyDate',
        'StudyTime',
        'SeriesDate',
        'SeriesTime',
        'AcquisitionDate',
        'AcquisitionTime',
        'InstitutionName',
        'InstitutionAddress',
        'ReferringPhysicianName',
        'ReadingPhysicianName',
        'PerformingPhysicianName',
        'OperatorsName',
        'AccessionNumber',
    ]

    for field in pii_fields:
        if hasattr(ds, field):
            setattr(ds, field, None)

    # Ensure proper DICOM format
    ds.is_little_endian = True
    ds.is_implicit_VR = True

    return ds


def get_image_format(filepath: str) -> Literal["dicom", "jpeg", "png", "unknown"]:
    """
    Determine the image format from file extension.

    Args:
        filepath: Path to the image file

    Returns:
        Image format string
    """
    ext = filepath.lower().split('.')[-1]

    if ext in ('dcm', 'dicom'):
        return "dicom"
    elif ext in ('jpg', 'jpeg'):
        return "jpeg"
    elif ext in ('png'):
        return "png"
    else:
        return "unknown"


def validate_image(image: Image.Image) -> bool:
    """
    Validate that an image is suitable for processing.

    Args:
        image: PIL Image object

    Returns:
        True if image is valid, False otherwise
    """
    # Check if image is not None
    if image is None:
        return False

    # Check image dimensions (minimum size)
    width, height = image.size
    if width < 64 or height < 64:
        return False

    # Check if image has data
    if image.mode == 'L' or image.mode == 'RGB':
        return True

    return False
