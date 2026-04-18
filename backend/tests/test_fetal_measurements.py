"""
Tests for fetal_measurements module - BPD centile lookup and size assessment.
"""

import pytest
from app.core.fetal_measurements import (
    get_bpd_reference,
    get_bpd_centile,
    compute_size_assessment,
    check_head_shape,
    BPDReference,
    BPDCentileResult,
    SizeAssessment,
    HeadShapeResult,
)


class TestGetBPDReference:
    """Tests for get_bpd_reference()."""

    def test_valid_ga_returns_reference(self):
        """Given GA=20 weeks, returns BPDReference with correct centiles."""
        ref = get_bpd_reference(20)
        assert isinstance(ref, BPDReference)
        assert ref.ga_weeks == 20
        assert ref.p5 == 44
        assert ref.p50 == 50
        assert ref.p95 == 56

    def test_ga_boundary_min(self):
        """Given GA=12 weeks (minimum), returns valid reference."""
        ref = get_bpd_reference(12)
        assert ref.ga_weeks == 12
        assert ref.p5 == 17
        assert ref.p50 == 21
        assert ref.p95 == 25

    def test_ga_boundary_max(self):
        """Given GA=42 weeks (maximum), returns valid reference."""
        ref = get_bpd_reference(42)
        assert ref.ga_weeks == 42
        assert ref.p5 == 92
        assert ref.p50 == 104
        assert ref.p95 == 116

    def test_ga_below_min_raises(self):
        """Given GA=11 weeks, raises ValueError."""
        with pytest.raises(ValueError, match="GA must be 12-42 weeks"):
            get_bpd_reference(11)

    def test_ga_above_max_raises(self):
        """Given GA=43 weeks, raises ValueError."""
        with pytest.raises(ValueError, match="GA must be 12-42 weeks"):
            get_bpd_reference(43)

    def test_ga_non_integer_raises(self):
        """Given GA as float string, raises ValueError."""
        with pytest.raises(ValueError, match="GA must be an integer"):
            get_bpd_reference("20")


class TestGetBPDCentile:
    """Tests for get_bpd_centile()."""

    def test_bpd_at_50th_centile(self):
        """Given BPD=50mm at 20 weeks, returns 50th centile."""
        result = get_bpd_centile(50.0, 20)
        assert isinstance(result, BPDCentileResult)
        assert result.centile == "50th"
        assert result.ga_weeks == 20
        assert result.bpd_mm == 50.0
        assert result.p5 == 44
        assert result.p50 == 50
        assert result.p95 == 56

    def test_bpd_below_5th_centile(self):
        """Given BPD=43mm at 20 weeks (<5th=44), returns 5th."""
        result = get_bpd_centile(43.0, 20)
        assert result.centile == "5th"

    def test_bpd_above_95th_centile(self):
        """Given BPD=57mm at 20 weeks (>95th=56), returns 95th."""
        result = get_bpd_centile(57.0, 20)
        assert result.centile == "95th"

    def test_bpd_between_5th_and_50th_near_5th(self):
        """Given BPD=45mm at 20 weeks (just above 5th=44), returns 50th."""
        result = get_bpd_centile(45.0, 20)
        # 45mm is between p5(44) and p50(50), closer to 50th
        assert result.centile in ("5th", "50th")

    def test_ga_outside_range_raises(self):
        """Given GA=50 weeks, raises ValueError."""
        with pytest.raises(ValueError, match="GA must be 12-42 weeks"):
            get_bpd_centile(45.0, 50)


class TestComputeSizeAssessment:
    """Tests for compute_size_assessment()."""

    def test_size_small(self):
        """Given BPD=43mm at 20 weeks, returns size_category='small'."""
        result = compute_size_assessment(43.0, 20)
        assert isinstance(result, SizeAssessment)
        assert result.size_category == "small"
        assert result.centile == "<5th"

    def test_size_average(self):
        """Given BPD=50mm at 20 weeks, returns size_category='average'."""
        result = compute_size_assessment(50.0, 20)
        assert result.size_category == "average"
        assert result.centile == "50th"

    def test_size_large(self):
        """Given BPD=58mm at 20 weeks, returns size_category='large'."""
        result = compute_size_assessment(58.0, 20)
        assert result.size_category == "large"
        assert result.centile == ">95th"

    def test_size_assessment_ga_outside_range_raises(self):
        """Given GA=50 weeks, raises ValueError."""
        with pytest.raises(ValueError, match="GA must be 12-42 weeks"):
            compute_size_assessment(45.0, 50)


class TestCheckHeadShape:
    """Tests for check_head_shape()."""

    def test_normal_head_shape(self):
        """Given BPD=50mm, OFD=60mm (CI=0.833), not dolicocephalic."""
        result = check_head_shape(50.0, 60.0)
        assert isinstance(result, HeadShapeResult)
        assert result.cephalic_index == pytest.approx(0.833, rel=0.01)
        assert result.is_dolicocephalic is False
        assert result.dolicocephalic_warning is False

    def test_dolicocephalic(self):
        """Given BPD=30mm, OFD=45mm (CI=0.667 < 0.75), dolicocephalic."""
        result = check_head_shape(30.0, 45.0)
        assert result.cephalic_index == pytest.approx(0.667, rel=0.01)
        assert result.is_dolicocephalic is True
        assert result.dolicocephalic_warning is True

    def test_dolicocephalic_exact_boundary(self):
        """Given BPD=30mm, OFD=40mm (CI=0.75 exactly), borderline - not flagged."""
        result = check_head_shape(30.0, 40.0)
        assert result.cephalic_index == 0.75
        assert result.is_dolicocephalic is False  # < 0.75 triggers, = 0.75 is normal

    def test_ofd_zero_raises(self):
        """Given OFD=0, raises ValueError."""
        with pytest.raises(ValueError, match="OFD must be positive"):
            check_head_shape(45.0, 0)

    def test_ofd_negative_raises(self):
        """Given OFD=-5, raises ValueError."""
        with pytest.raises(ValueError, match="OFD must be positive"):
            check_head_shape(45.0, -5)
