"""
Fetal Measurements Module - BPD centile lookup and size assessment.

Reference: Altman & Chitty 1997 - British Medical Journal
BPD centiles (5th, 50th, 95th) for gestational ages 12-42 weeks.
Uses "outer-to-outer" calliper positioning on parietal bones (BMUS standard).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# BPD reference data: GA (weeks) -> (5th, 50th, 95th) in mm
# Source: Altman & Chitty 1997, BMJ
_BPD_REFERENCE: dict[int, tuple[int, int, int]] = {
    12: (17, 21, 25),
    13: (20, 24, 28),
    14: (24, 28, 32),
    15: (27, 31, 36),
    16: (31, 35, 40),
    17: (34, 39, 44),
    18: (38, 43, 48),
    19: (41, 46, 52),
    20: (44, 50, 56),
    21: (47, 54, 60),
    22: (50, 57, 64),
    23: (53, 60, 68),
    24: (56, 64, 72),
    25: (59, 67, 75),
    26: (62, 70, 79),
    27: (65, 73, 82),
    28: (67, 76, 85),
    29: (70, 79, 88),
    30: (72, 82, 92),
    31: (75, 84, 95),
    32: (77, 87, 97),
    33: (79, 90, 100),
    34: (81, 92, 103),
    35: (82, 93, 104),
    36: (84, 95, 107),
    37: (85, 97, 109),
    38: (86, 98, 110),
    39: (87, 99, 112),
    40: (89, 101, 113),
    41: (90, 102, 115),
    42: (92, 104, 116),
}

_MIN_GA = 12
_MAX_GA = 42


@dataclass
class BPDReference:
    """BPD reference values for a gestational age."""
    ga_weeks: int
    p5: int
    p50: int
    p95: int


@dataclass
class BPDCentileResult:
    """Result of BPD centile lookup."""
    bpd_mm: float
    ga_weeks: int
    centile: Literal["5th", "50th", "95th"]
    p5: int
    p50: int
    p95: int


@dataclass
class SizeAssessment:
    """Fetal size assessment based on BPD."""
    bpd_mm: float
    ga_weeks: int
    size_category: Literal["small", "average", "large"]
    centile: str


@dataclass
class HeadShapeResult:
    """Head shape assessment from BPD and OFD."""
    bpd_mm: float
    ofd_mm: float
    cephalic_index: float
    is_dolicocephalic: bool
    dolicocephalic_warning: bool


def _interpolate_centile(bpd_mm: float, ga_weeks: int) -> Literal["5th", "50th", "95th"]:
    """
    Determine which centile band a BPD measurement falls into via linear interpolation.
    Uses position relative to centile reference values for band assignment.
    """
    p5, p50, p95 = _BPD_REFERENCE[ga_weeks]
    if bpd_mm <= p5:
        return "5th"
    elif bpd_mm >= p95:
        return "95th"

    # Map measurement to nearest centile band
    if bpd_mm < p50:
        return "5th" if bpd_mm < (p5 + p50) / 2 else "50th"
    else:
        return "50th" if bpd_mm < (p50 + p95) / 2 else "95th"


def get_bpd_reference(ga_weeks: int) -> BPDReference:
    """
    Get BPD reference values (5th, 50th, 95th centiles) for a gestational age.

    Args:
        ga_weeks: Gestational age in weeks (12-42)

    Returns:
        BPDReference with centile values in mm

    Raises:
        ValueError: If GA is outside the valid range (12-42 weeks)
    """
    if not isinstance(ga_weeks, int):
        raise ValueError(f"GA must be an integer, got {type(ga_weeks).__name__}")

    if ga_weeks < _MIN_GA or ga_weeks > _MAX_GA:
        raise ValueError(f"GA must be {_MIN_GA}-{_MAX_GA} weeks, got {ga_weeks}")

    p5, p50, p95 = _BPD_REFERENCE[ga_weeks]
    return BPDReference(ga_weeks=ga_weeks, p5=p5, p50=p50, p95=p95)


def get_bpd_centile(bpd_mm: float, ga_weeks: int) -> BPDCentileResult:
    """
    Determine which centile band a BPD measurement falls into.

    Args:
        bpd_mm: BPD measurement in millimeters
        ga_weeks: Gestational age in weeks (12-42)

    Returns:
        BPDCentileResult with centile classification

    Raises:
        ValueError: If GA is outside the valid range (12-42 weeks)
    """
    ref = get_bpd_reference(ga_weeks)
    centile = _interpolate_centile(bpd_mm, ga_weeks)
    return BPDCentileResult(
        bpd_mm=bpd_mm,
        ga_weeks=ga_weeks,
        centile=centile,
        p5=ref.p5,
        p50=ref.p50,
        p95=ref.p95,
    )


def compute_size_assessment(bpd_mm: float, ga_weeks: int) -> SizeAssessment:
    """
    Assess fetal size category based on BPD measurement.

    Args:
        bpd_mm: BPD measurement in millimeters
        ga_weeks: Gestational age in weeks (12-42)

    Returns:
        SizeAssessment with category: "small" (<5th), "average" (5th-95th), "large" (>95th)

    Raises:
        ValueError: If GA is outside the valid range (12-42 weeks)
    """
    ref = get_bpd_reference(ga_weeks)

    if bpd_mm < ref.p5:
        category: Literal["small", "average", "large"] = "small"
        centile = "<5th"
    elif bpd_mm > ref.p95:
        category = "large"
        centile = ">95th"
    else:
        category = "average"
        centile = _interpolate_centile(bpd_mm, ga_weeks)

    return SizeAssessment(
        bpd_mm=bpd_mm,
        ga_weeks=ga_weeks,
        size_category=category,
        centile=centile,
    )


def check_head_shape(bpd_mm: float, ofd_mm: float) -> HeadShapeResult:
    """
    Check head shape for dolicocephaly using BPD/OFD ratio.
    
    Dolicocephaly is flagged when BPD/OFD < 0.75 (informational warning).
    The cephalic index = BPD/OFD; normal range is 0.75-0.85.

    Args:
        bpd_mm: BPD measurement in millimeters
        ofd_mm: OFD (Occipitofrontal Diameter) measurement in millimeters

    Returns:
        HeadShapeResult with cephalic index and warnings
    """
    if ofd_mm <= 0:
        raise ValueError(f"OFD must be positive, got {ofd_mm}")

    cephalic_index = bpd_mm / ofd_mm
    is_dolicocephalic = cephalic_index < 0.75

    return HeadShapeResult(
        bpd_mm=bpd_mm,
        ofd_mm=ofd_mm,
        cephalic_index=round(cephalic_index, 3),
        is_dolicocephalic=is_dolicocephalic,
        dolicocephalic_warning=is_dolicocephalic,
    )
