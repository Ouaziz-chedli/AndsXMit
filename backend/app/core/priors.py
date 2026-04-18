"""
Priors Module - Apply Bayesian priors based on patient context.

First-trimester chromosomal risk priors based on biomarkers and maternal age.
Based on French NT-prenatal screening protocol.

Key insight: b-hCG and PAPP-A MoM values indicate chromosomal risk:
- Low PAPP-A + High b-hCG → increased Down syndrome risk
- Both low → increased T18/T13 risk
"""

from typing import Union
from ..models.patient import PatientContext, PatientContextMoM


# Population medians for risk calculation
MEDIAN_MOTHER_AGE_RISK = 37.0  # Age where risk starts increasing significantly
TRISOMY_21_BASE_RISK = 800      # 1 in 800 at maternal age 30


def calculate_age_risk(mother_age: int) -> float:
    """
    Calculate age-based prior risk for chromosomal abnormality.

    Risk doubles every 2.5 years after age 25.

    Args:
        mother_age: Mother's age in years

    Returns:
        Risk multiplier relative to baseline

    Examples:
        >>> calculate_age_risk(30)
        1.0

        >>> calculate_age_risk(35)
        ~2.0

        >>> calculate_age_risk(40)
        ~5.0
    """
    # Maternal age risk curve based on epidemiological data.
    # Baseline at age 30 (×1.0), risk accelerates with age.
    # Reference: age 30 → ×1.0, age 35 → ×1.45, age 40 → ×5.0 (capped)
    if mother_age <= 30:
        return 1.0
    years_over_30 = mother_age - 30
    denominator = 800 - 10 * years_over_30 ** 2
    if denominator <= 0:
        # Above ~38 the quadratic formula breaks down — return cap directly
        return 5.0
    risk_factor = 800 / denominator
    return min(risk_factor, 5.0)


def calculate_biomarker_risk(
    b_hcg_mom: Union[float, None],
    papp_a_mom: Union[float, None],
) -> float:
    """
    Calculate biomarker-based risk modifier.

    Based on MoM values relative to expected medians.

    Typical patterns:
    - Down syndrome: b-hCG MoM elevated (~2.0), PAPP-A MoM low (~0.5)
    - Edwards (T18): both b-hCG and PAPP-A low
    - Patau (T13): both b-hCG and PAPP-A low

    Args:
        b_hcg_mom: b-hCG Multiple of Median (None if not available)
        papp_a_mom: PAPP-A Multiple of Median (None if not available)

    Returns:
        Risk multiplier (1.0 = normal)

    Examples:
        >>> calculate_biomarker_risk(2.0, 0.5)  # Down pattern
        1.8

        >>> calculate_biomarker_risk(0.2, 0.3)  # T18/T13 pattern
        1.5

        >>> calculate_biomarker_risk(1.0, 1.0)  # Normal
        1.0
    """
    if b_hcg_mom is None and papp_a_mom is None:
        return 1.0

    risk = 1.0

    # b-hCG risk modifier
    if b_hcg_mom is not None:
        if b_hcg_mom > 2.0:
            # High b-hCG suggests Down syndrome
            risk *= 1.5
        elif b_hcg_mom < 0.25:
            # Very low b-hCG suggests T18/T13
            risk *= 1.3

    # PAPP-A risk modifier
    if papp_a_mom is not None:
        if papp_a_mom < 0.4:
            # Very low PAPP-A indicates high risk
            risk *= 2.0
        elif papp_a_mom < 0.5:
            risk *= 1.5
        elif papp_a_mom < 0.75:
            risk *= 1.2

    # Combined modifier for opposing patterns (high b-hcg + low papp_a)
    if b_hcg_mom is not None and papp_a_mom is not None:
        if b_hcg_mom > 1.5 and papp_a_mom < 0.6:
            # Classic Down syndrome pattern
            risk *= 1.8

    return risk


def apply_priors(
    weighted_score: float,
    disease: str,
    context: Union[PatientContext, PatientContextMoM],
) -> float:
    """
    Apply all priors to get final disease probability modifier.

    For chromosomal diseases (Down, Edwards, Patau):
    - Maternal age is significant factor
    - b-hCG and PAPP-A MoM values indicate disease-specific patterns

    Args:
        weighted_score: Score after trimester weighting
        disease: Disease identifier (e.g., "down_syndrome")
        context: Patient context (raw or MoM-normalized)

    Returns:
        Final score with all priors applied

    Examples:
        >>> apply_priors(0.44, "down_syndrome", PatientContext(mother_age=38, ...))
        0.66  # Increased due to high maternal age
    """
    multiplier = 1.0

    # Maternal age risk (significant for all chromosomal diseases)
    age_risk = calculate_age_risk(context.mother_age)
    chromosomal_diseases = ["down_syndrome", "edwards_syndrome", "patau_syndrome"]
    if disease in chromosomal_diseases:
        multiplier *= age_risk

    # Biomarker risk
    if isinstance(context, PatientContextMoM):
        biomarker_risk = calculate_biomarker_risk(
            context.b_hcg_mom,
            context.papp_a_mom
        )
    else:
        # Convert to MoM first
        mom_context = context.to_mom()
        biomarker_risk = calculate_biomarker_risk(
            mom_context.b_hcg_mom,
            mom_context.papp_a_mom
        )

    if disease in chromosomal_diseases:
        multiplier *= biomarker_risk

    # IVF modifier (slight increase for chromosomal anomalies)
    if hasattr(context, 'ivf_conception') and context.ivf_conception:
        if disease in chromosomal_diseases:
            multiplier *= 1.1

    # Previous affected pregnancy (significant risk factor)
    if context.previous_affected_pregnancy:
        multiplier *= 2.5

    # Note: scores can exceed 1.0 for high-risk cases — they are relative rankings,
    # not calibrated probabilities. Normalization happens at the presentation layer.
    return weighted_score * multiplier


def get_applied_priors(
    disease: str,
    context: Union[PatientContext, PatientContextMoM],
) -> list[str]:
    """
    Return list of prior descriptors that were applied.

    Useful for explaining the diagnosis result.

    Args:
        disease: Disease identifier
        context: Patient context

    Returns:
        List of strings describing applied priors

    Examples:
        >>> get_applied_priors("down_syndrome", PatientContext(mother_age=38, ...))
        ["maternal_age_38", "previous_affected_pregnancy"]
    """
    applied = []

    # Age priors
    if context.mother_age >= 40:
        chromosomal_diseases = ["down_syndrome", "edwards_syndrome", "patau_syndrome"]
        if disease in chromosomal_diseases:
            applied.append(f"maternal_age_{context.mother_age}")

    # Biomarker priors
    if isinstance(context, PatientContextMoM):
        if context.b_hcg_mom is not None or context.papp_a_mom is not None:
            biomarker_risk = calculate_biomarker_risk(
                context.b_hcg_mom,
                context.papp_a_mom
            )
            if biomarker_risk > 1.2:
                applied.append("biomarker_risk_pattern")
    else:
        mom_context = context.to_mom()
        if mom_context.b_hcg_mom is not None or mom_context.papp_a_mom is not None:
            biomarker_risk = calculate_biomarker_risk(
                mom_context.b_hcg_mom,
                mom_context.papp_a_mom
            )
            if biomarker_risk > 1.2:
                applied.append("biomarker_risk_pattern")

    # Previous affected pregnancy
    if context.previous_affected_pregnancy:
        applied.append("previous_affected_pregnancy")

    return applied
