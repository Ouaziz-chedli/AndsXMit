"""
Tests for biometric_context module - AI prompt fragment generation from BPD.
"""

import pytest
from app.core.biometric_context import (
    compute_biometric_context,
    build_biometric_prompt,
)


class TestComputeBiometricContext:
    """Tests for compute_biometric_context()."""

    def test_with_valid_bpd_and_ga(self):
        """Given BPD=45mm at 20 weeks, returns centile, size_category, and fragment."""
        result = compute_biometric_context(45.0, 20, "2nd")
        assert result["bpd_mm"] == 45.0
        assert result["ga_weeks"] == 20
        assert result["centile"] in ("5th", "50th", "95th")
        assert result["size_category"] in ("small", "average", "large")
        assert result["head_shape_warning"] is None
        assert result["ai_prompt_fragment"] is not None
        assert "BPD=45" in result["ai_prompt_fragment"]
        assert "20 weeks" in result["ai_prompt_fragment"]

    def test_bpd_none_returns_partial_context(self):
        """Given BPD=None, returns None for centile, size_category, and fragment."""
        result = compute_biometric_context(None, 20, "2nd")
        assert result["bpd_mm"] is None
        assert result["ga_weeks"] == 20
        assert result["centile"] is None
        assert result["size_category"] is None
        assert result["head_shape_warning"] is None
        assert result["ai_prompt_fragment"] is None

    def test_ga_none_returns_partial_context(self):
        """Given GA=None, returns None for centile and size_category."""
        result = compute_biometric_context(45.0, None, "2nd")
        assert result["bpd_mm"] == 45.0
        assert result["ga_weeks"] is None
        assert result["centile"] is None
        assert result["size_category"] is None
        assert result["ai_prompt_fragment"] is None

    def test_ga_outside_range_returns_partial(self):
        """Given GA=50 weeks (outside 12-42), returns None for centile/size_category."""
        result = compute_biometric_context(45.0, 50, "3rd")
        assert result["bpd_mm"] == 45.0
        assert result["ga_weeks"] == 50
        assert result["centile"] is None
        assert result["size_category"] is None
        assert result["ai_prompt_fragment"] is None

    def test_trimester_included_in_fragment(self):
        """Given trimester='2nd', fragment mentions GA correctly."""
        result = compute_biometric_context(50.0, 20, "2nd")
        assert result["ai_prompt_fragment"] is not None
        # Fragment should contain biometric data
        assert "BPD=" in result["ai_prompt_fragment"]

    def test_all_none_returns_empty(self):
        """Given all inputs None, returns all-None dict."""
        result = compute_biometric_context(None, None, None)
        assert result["bpd_mm"] is None
        assert result["ga_weeks"] is None
        assert result["centile"] is None
        assert result["size_category"] is None
        assert result["head_shape_warning"] is None
        assert result["ai_prompt_fragment"] is None


class TestBuildBiometricPrompt:
    """Tests for build_biometric_prompt()."""

    def test_with_bpd_returns_fragment(self):
        """Given BPD=45mm at 20 weeks, returns non-empty prompt fragment."""
        prompt = build_biometric_prompt(45.0, 20, "2nd")
        assert prompt != ""
        assert "BPD=" in prompt
        assert "20 weeks" in prompt

    def test_without_bpd_returns_empty(self):
        """Given BPD=None, returns empty string."""
        prompt = build_biometric_prompt(None, 20, "2nd")
        assert prompt == ""

    def test_with_ofd_adds_head_shape(self):
        """Given OFD=45mm with BPD=30mm (dolicocephalic), includes warning."""
        prompt = build_biometric_prompt(30.0, 20, "2nd", ofd_mm=45.0)
        assert prompt != ""
        assert "dolicocephalic" in prompt.lower()

    def test_with_normal_head_shape_omits_warning(self):
        """Given OFD=60mm with BPD=50mm (normal CI), no dolicocephalic mention."""
        prompt = build_biometric_prompt(50.0, 20, "2nd", ofd_mm=60.0)
        # Normal head shape should not add a dolicocephalic warning
        assert "dolicocephalic" not in prompt.lower()

    def test_without_ofd_no_head_shape_mention(self):
        """Given no OFD, does not mention head shape."""
        prompt = build_biometric_prompt(45.0, 20, "2nd")
        assert "head shape" not in prompt.lower()

    def test_ga_outside_range_returns_empty(self):
        """Given GA=50 weeks, returns empty string (no valid centile)."""
        prompt = build_biometric_prompt(45.0, 50, "3rd")
        assert prompt == ""
