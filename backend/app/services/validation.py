"""
Validation Service - Validate case submissions.

This service provides validation for community case submissions,
ensuring data quality and consistency before storage.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum

from .case_upload import UploadedCaseData


class Severity(Enum):
    """Severity level of validation issues."""
    ERROR = "error"      # Prevents storage
    WARNING = "warning"  # Allows storage with warning
    INFO = "info"        # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: Severity
    field: str
    message: str


@dataclass
class ValidationResult:
    """Result of case validation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_issue(self, severity: Severity, field: str, message: str) -> None:
        """Add a validation issue."""
        self.issues.append(ValidationIssue(severity, field, message))
        if severity == Severity.ERROR:
            self.is_valid = False

    def get_errors(self) -> List[ValidationIssue]:
        """Get all error issues."""
        return [i for i in self.issues if i.severity == Severity.ERROR]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning issues."""
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def get_info(self) -> List[ValidationIssue]:
        """Get all informational issues."""
        return [i for i in self.issues if i.severity == Severity.INFO]


class ValidationService:
    """Service for validating case submissions."""

    # Valid trimesters
    VALID_TRIMESTERS = {"1st", "2nd", "3rd"}

    # Valid labels
    VALID_LABELS = {"positive", "negative"}

    # Disease IDs (for MVP)
    VALID_DISEASES = {
        "down_syndrome",
        "edwards_syndrome",
        "patau_syndrome",
        "cardiac_defect",
        "neural_tube_defect",
        "skeletal_dysplasia",
    }

    # Biomarker ranges (IU/L)
    B_HCG_RANGE = (0.0, 500000.0)
    PAPP_A_RANGE = (0.0, 10000.0)

    # Gestational age ranges (weeks)
    GESTATIONAL_AGE_RANGES = {
        "1st": (10.0, 14.0),
        "2nd": (14.0, 27.0),
        "3rd": (27.0, 42.0),
    }

    # Mother age range (years)
    MOTHER_AGE_RANGE = (12, 60)

    @classmethod
    def validate_case_submission(
        cls,
        case_data: UploadedCaseData,
    ) -> ValidationResult:
        """
        Validate a complete case submission.

        Args:
            case_data: Data for the case being uploaded

        Returns:
            ValidationResult with all issues found
        """
        result = ValidationResult(is_valid=True)

        # Validate required fields
        cls._validate_required_fields(case_data, result)

        # Validate field values
        cls._validate_disease_id(case_data.disease_id, result)
        cls._validate_trimester(case_data.trimester, result)
        cls._validate_label(case_data.label, result)
        cls._validate_gestational_age(case_data, result)
        cls._validate_biomarkers(case_data, result)
        cls._validate_mother_age(case_data, result)
        cls._validate_images(case_data, result)
        cls._validate_symptoms(case_data, result)

        # Validate consistency
        cls._validate_consistency(case_data, result)

        return result

    @classmethod
    def _validate_required_fields(
        cls,
        case_data: UploadedCaseData,
        result: ValidationResult,
    ) -> None:
        """Validate that all required fields are present."""
        required_fields = {
            "disease_id": case_data.disease_id,
            "trimester": case_data.trimester,
            "label": case_data.label,
            "images": case_data.images,
        }

        for field_name, field_value in required_fields.items():
            if not field_value:
                result.add_issue(
                    Severity.ERROR,
                    field_name,
                    f"Field '{field_name}' is required"
                )

    @classmethod
    def _validate_disease_id(
        cls,
        disease_id: str,
        result: ValidationResult,
    ) -> None:
        """Validate disease ID."""
        if disease_id not in cls.VALID_DISEASES:
            result.add_issue(
                Severity.ERROR,
                "disease_id",
                f"Unknown disease ID: {disease_id}"
            )

    @classmethod
    def _validate_trimester(
        cls,
        trimester: str,
        result: ValidationResult,
    ) -> None:
        """Validate trimester value."""
        if trimester not in cls.VALID_TRIMESTERS:
            result.add_issue(
                Severity.ERROR,
                "trimester",
                f"Invalid trimester: {trimester}. Must be one of: {cls.VALID_TRIMESTERS}"
            )

    @classmethod
    def _validate_label(
        cls,
        label: str,
        result: ValidationResult,
    ) -> None:
        """Validate label (positive/negative)."""
        if label not in cls.VALID_LABELS:
            result.add_issue(
                Severity.ERROR,
                "label",
                f"Invalid label: {label}. Must be 'positive' or 'negative'"
            )

    @classmethod
    def _validate_gestational_age(
        cls,
        case_data: UploadedCaseData,
        result: ValidationResult,
    ) -> None:
        """Validate gestational age."""
        gestational_age = case_data.gestational_age_weeks

        if gestational_age is None:
            # Warning if not provided
            result.add_issue(
                Severity.WARNING,
                "gestational_age_weeks",
                "Gestational age not provided"
            )
            return

        # Check range
        if gestational_age < 0 or gestational_age > 50:
            result.add_issue(
                Severity.ERROR,
                "gestational_age_weeks",
                f"Gestational age out of valid range: {gestational_age}"
            )

        # Check consistency with trimester
        trimester = case_data.trimester
        if trimester in cls.GESTATIONAL_AGE_RANGES:
            min_age, max_age = cls.GESTATIONAL_AGE_RANGES[trimester]
            if gestational_age < min_age or gestational_age > max_age:
                result.add_issue(
                    Severity.WARNING,
                    "gestational_age_weeks",
                    f"Gestational age {gestational_age} weeks inconsistent "
                    f"with {trimester} trimester (expected {min_age}-{max_age} weeks)"
                )

    @classmethod
    def _validate_biomarkers(
        cls,
        case_data: UploadedCaseData,
        result: ValidationResult,
    ) -> None:
        """Validate biomarker values."""
        # Validate b-hCG
        if case_data.b_hcg is not None:
            if not cls.B_HCG_RANGE[0] <= case_data.b_hcg <= cls.B_HCG_RANGE[1]:
                result.add_issue(
                    Severity.WARNING,
                    "b_hcg",
                    f"b-hCG value {case_data.b_hcg} outside typical range"
                )

        # Validate PAPP-A
        if case_data.papp_a is not None:
            if not cls.PAPP_A_RANGE[0] <= case_data.papp_a <= cls.PAPP_A_RANGE[1]:
                result.add_issue(
                    Severity.WARNING,
                    "papp_a",
                    f"PAPP-A value {case_data.papp_a} outside typical range"
                )

    @classmethod
    def _validate_mother_age(
        cls,
        case_data: UploadedCaseData,
        result: ValidationResult,
    ) -> None:
        """Validate mother age."""
        mother_age = case_data.mother_age

        if mother_age is None:
            # Optional field
            return

        if not cls.MOTHER_AGE_RANGE[0] <= mother_age <= cls.MOTHER_AGE_RANGE[1]:
            result.add_issue(
                Severity.WARNING,
                "mother_age",
                f"Mother age {mother_age} outside typical range"
            )

    @classmethod
    def _validate_images(
        cls,
        case_data: UploadedCaseData,
        result: ValidationResult,
    ) -> None:
        """Validate image list."""
        images = case_data.images

        if not images:
            result.add_issue(
                Severity.ERROR,
                "images",
                "At least one image is required"
            )
            return

        if len(images) > 10:
            result.add_issue(
                Severity.WARNING,
                "images",
                f"Large number of images: {len(images)}. Consider reducing."
            )

        # Check if image files exist
        import os
        missing_files = [img for img in images if not os.path.exists(img)]
        if missing_files:
            result.add_issue(
                Severity.ERROR,
                "images",
                f"Image files not found: {missing_files}"
            )

    @classmethod
    def _validate_symptoms(
        cls,
        case_data: UploadedCaseData,
        result: ValidationResult,
    ) -> None:
        """Validate symptom text if provided."""
        symptom_text = case_data.symptom_text

        if symptom_text is None:
            # Optional field
            return

        if len(symptom_text) < 5:
            result.add_issue(
                Severity.WARNING,
                "symptom_text",
                "Symptom description too short"
            )

        if len(symptom_text) > 1000:
            result.add_issue(
                Severity.WARNING,
                "symptom_text",
                "Symptom description very long"
            )

    @classmethod
    def _validate_consistency(
        cls,
        case_data: UploadedCaseData,
        result: ValidationResult,
    ) -> None:
        """Validate overall consistency of the case."""
        # Check positive label with biomarkers
        if case_data.label == "positive":
            # For positive cases, biomarkers should be provided
            if case_data.b_hcg is None and case_data.papp_a is None:
                result.add_issue(
                    Severity.INFO,
                    "consistency",
                    "Positive case without biomarkers. Consider adding for better priors."
                )

        # Check Down syndrome pattern
        if case_data.disease_id == "down_syndrome" and case_data.label == "positive":
            if case_data.b_hcg and case_data.papp_a:
                # Calculate approximate MoM
                b_hcg_mom = case_data.b_hcg / 50000.0
                papp_a_mom = case_data.papp_a / 1500.0

                # Classic pattern: high b-hCG, low PAPP-A
                if b_hcg_mom < 1.0 and papp_a_mom > 1.0:
                    result.add_issue(
                        Severity.INFO,
                        "consistency",
                        "Biomarkers do not show typical Down syndrome pattern"
                    )

    @classmethod
    def format_validation_result(
        cls,
        result: ValidationResult,
    ) -> Dict:
        """
        Format validation result as dictionary.

        Args:
            result: ValidationResult to format

        Returns:
            Dictionary with formatted result
        """
        return {
            "is_valid": result.is_valid,
            "error_count": len(result.get_errors()),
            "warning_count": len(result.get_warnings()),
            "info_count": len(result.get_info()),
            "errors": [
                {
                    "field": issue.field,
                    "message": issue.message,
                }
                for issue in result.get_errors()
            ],
            "warnings": [
                {
                    "field": issue.field,
                    "message": issue.message,
                }
                for issue in result.get_warnings()
            ],
            "info": [
                {
                    "field": issue.field,
                    "message": issue.message,
                }
                for issue in result.get_info()
            ],
        }


# Convenience function
def validate_case_submission(
    case_data: UploadedCaseData,
) -> ValidationResult:
    """
    Validate a case submission.

    Args:
        case_data: Data for the case being uploaded

    Returns:
        ValidationResult
    """
    return ValidationService.validate_case_submission(case_data)


if __name__ == "__main__":
    # Example usage
    from .case_upload import UploadedCaseData

    valid_case = UploadedCaseData(
        disease_id="down_syndrome",
        trimester="1st",
        label="positive",
        images=["/path/to/image.png"],
        gestational_age_weeks=12.0,
        b_hcg=100000.0,
        papp_a=750.0,
        mother_age=35,
    )

    result = validate_case_submission(valid_case)

    print(f"Valid: {result.is_valid}")
    print(f"Errors: {len(result.get_errors())}")
    print(f"Warnings: {len(result.get_warnings())}")

    for issue in result.issues:
        print(f"  {issue.severity.value.upper()} [{issue.field}]: {issue.message}")
