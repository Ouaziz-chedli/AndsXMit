"""
Biometric Context Module - Builds structured AI prompt fragment from BPD measurements.

Injects fetal biometric context into MedGemma prompts to improve disease detection
accuracy by providing scale context (small/average/large for gestational age).
"""

from __future__ import annotations

from typing import Optional, Literal

from .fetal_measurements import (
    get_bpd_centile,
    compute_size_assessment,
    check_head_shape,
)


def compute_biometric_context(
    bpd_mm: Optional[float],
    ga_weeks: Optional[int],
    trimester: Optional[Literal["1st", "2nd", "3rd"]],
) -> dict:
    """
    Build structured biometric context dict from BPD measurement.

    Args:
        bpd_mm: BPD measurement in millimeters (optional)
        ga_weeks: Gestational age in weeks (optional)
        trimester: Current trimester (optional)

    Returns:
        Structured dict with keys:
        - bpd_mm: Original BPD value or None
        - ga_weeks: Gestational age or None
        - centile: Centile string (e.g., "50th") or None
        - size_category: "small", "average", "large", or None
        - head_shape_warning: Boolean or None
        - ai_prompt_fragment: Formatted string for AI prompt or None
    """
    if bpd_mm is None or ga_weeks is None:
        return {
            "bpd_mm": bpd_mm,
            "ga_weeks": ga_weeks,
            "centile": None,
            "size_category": None,
            "head_shape_warning": None,
            "ai_prompt_fragment": None,
        }

    try:
        centile_result = get_bpd_centile(bpd_mm, ga_weeks)
        size_result = compute_size_assessment(bpd_mm, ga_weeks)
        head_shape_warning = None  # Head shape checked separately via build_biometric_prompt when OFD available
    except ValueError:
        # GA outside valid range — return partial context
        return {
            "bpd_mm": bpd_mm,
            "ga_weeks": ga_weeks,
            "centile": None,
            "size_category": None,
            "head_shape_warning": None,
            "ai_prompt_fragment": None,
        }

    # Build AI prompt fragment
    # Format: "Fetal biometry: BPD={bpd_mm}mm at {ga_weeks} weeks ({centile} centile, {size_category}). Head shape: {normal/dolicocephalic}."
    ai_fragment = (
        f"Fetal biometry: BPD={bpd_mm:.1f}mm at {ga_weeks} weeks "
        f"({centile_result.centile} centile, {size_result.size_category} for GA)."
    )

    return {
        "bpd_mm": bpd_mm,
        "ga_weeks": ga_weeks,
        "centile": centile_result.centile,
        "size_category": size_result.size_category,
        "head_shape_warning": head_shape_warning,
        "ai_prompt_fragment": ai_fragment,
    }


def build_biometric_prompt(
    bpd_mm: Optional[float],
    ga_weeks: Optional[int],
    trimester: Optional[Literal["1st", "2nd", "3rd"]],
    ofd_mm: Optional[float] = None,
) -> str:
    """
    Build enhanced AI prompt fragment including head shape assessment.

    Args:
        bpd_mm: BPD measurement in millimeters (optional)
        ga_weeks: Gestational age in weeks (optional)
        trimester: Current trimester (optional)
        ofd_mm: OFD measurement in millimeters (optional, for head shape)

    Returns:
        Formatted string for appending to MedGemma prompt, or empty string if no BPD
    """
    context = compute_biometric_context(bpd_mm, ga_weeks, trimester)
    if context["ai_prompt_fragment"] is None:
        return ""

    prompt_parts = [context["ai_prompt_fragment"]]

    # Add head shape if OFD is provided
    if ofd_mm is not None and bpd_mm is not None:
        try:
            head_result = check_head_shape(bpd_mm, ofd_mm)
            if head_result.dolicocephalic_warning:
                prompt_parts.append(
                    f" Head shape: dolicocephalic (CI={head_result.cephalic_index:.2f})."
                )
            # else: normal head shape, omit from prompt to keep it concise
        except ValueError:
            pass

    return " ".join(prompt_parts)
