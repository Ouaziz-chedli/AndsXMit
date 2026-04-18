"""
Aggregation Module - Apply trimester-specific weights to diagnosis scores.

Different diseases manifest at different pregnancy stages, so symptom
relevance varies by trimester.
"""

from typing import Dict


# Trimester-specific weights for each disease
# Higher weight = disease more detectable in that trimester
TRIMESTER_WEIGHTS: Dict[str, Dict[str, float]] = {
    "1st": {
        "down_syndrome": 0.85,      # NT, nasal bone most visible
        "edwards_syndrome": 0.80,   # Early markers
        "patau_syndrome": 0.75,     # Early markers
        "cardiac_defect": 0.50,     # Early screening possible
        "neural_tube_defect": 0.60, # Some early markers
        "skeletal_dysplasia": 0.55, # Long bones visible early
    },
    "2nd": {
        "down_syndrome": 0.75,      # Markers still relevant
        "edwards_syndrome": 0.85,   # Growth patterns clear
        "patau_syndrome": 0.80,     # Heart defects visible
        "cardiac_defect": 0.90,     # Cardiac anatomy best visualized
        "neural_tube_defect": 0.85, # Spine clearly visible
        "skeletal_dysplasia": 0.90, # Long bones best measured
    },
    "3rd": {
        "down_syndrome": 0.40,      # Late-stage diagnosis less common
        "edwards_syndrome": 0.50,   # Growth restriction visible
        "patau_syndrome": 0.45,     # Late markers
        "cardiac_defect": 0.60,      # Functional assessment possible
        "neural_tube_defect": 0.70, # Spine closure assessment
        "skeletal_dysplasia": 0.65, # Final growth assessment
    },
}


def aggregate_scores(
    raw_score: float,
    disease: str,
    trimester: str,
) -> float:
    """
    Apply trimester-specific weight to the raw diagnosis score.

    Args:
        raw_score: The raw score from calculate_raw_score()
        disease: Disease identifier (e.g., "down_syndrome")
        trimester: "1st", "2nd", or "3rd"

    Returns:
        Weighted score (may be negative if raw_score is negative)

    Raises:
        KeyError: If disease or trimester not found in weights

    Examples:
        >>> aggregate_scores(0.52, "down_syndrome", "1st")
        0.442

        >>> aggregate_scores(0.60, "cardiac_defect", "2nd")
        0.54
    """
    if trimester not in TRIMESTER_WEIGHTS:
        raise ValueError(f"Unknown trimester: {trimester}. Must be '1st', '2nd', or '3rd'")

    if disease not in TRIMESTER_WEIGHTS[trimester]:
        # Default weight for unknown diseases
        weight = 0.5
    else:
        weight = TRIMESTER_WEIGHTS[trimester][disease]

    return raw_score * weight


def get_available_diseases() -> list[str]:
    """Return list of all supported disease identifiers."""
    diseases = set()
    for trimester_data in TRIMESTER_WEIGHTS.values():
        diseases.update(trimester_data.keys())
    return sorted(list(diseases))


def get_disease_weight(disease: str, trimester: str) -> float:
    """Get the trimester weight for a specific disease."""
    if trimester not in TRIMESTER_WEIGHTS:
        raise ValueError(f"Unknown trimester: {trimester}")

    return TRIMESTER_WEIGHTS[trimester].get(disease, 0.5)


def update_trimester_weight(disease: str, trimester: str, weight: float) -> None:
    """
    Update a trimester weight for a disease.

    Args:
        disease: Disease identifier
        trimester: "1st", "2nd", or "3rd"
        weight: New weight value (typically 0.0 to 1.0)

    Raises:
        ValueError: If trimester is invalid
    """
    if trimester not in TRIMESTER_WEIGHTS:
        raise ValueError(f"Unknown trimester: {trimester}")

    if not 0.0 <= weight <= 1.0:
        raise ValueError(f"Weight must be between 0.0 and 1.0, got {weight}")

    TRIMESTER_WEIGHTS[trimester][disease] = weight
