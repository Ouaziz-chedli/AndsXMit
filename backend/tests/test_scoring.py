"""
Unit tests for the scoring module.

Tests the calculation of raw diagnosis scores from similarity scores.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.scoring import calculate_raw_score, calculate_confidence_interval


class TestCalculateRawScore:
    """Tests for calculate_raw_score function."""

    def test_positive_score(self):
        """Test calculation when more similar to positive cases."""
        positive_sims = [0.85, 0.78, 0.82]
        negative_sims = [0.30, 0.25, 0.35]

        result = calculate_raw_score(positive_sims, negative_sims)

        # Mean positive: ~0.82, Mean negative: ~0.30
        # Score: 0.82 - 0.30 = 0.52
        assert result > 0
        assert 0.5 < result < 0.6

    def test_negative_score(self):
        """Test calculation when more similar to negative cases."""
        positive_sims = [0.30, 0.25, 0.35]
        negative_sims = [0.85, 0.78, 0.82]

        result = calculate_raw_score(positive_sims, negative_sims)

        # Mean positive: ~0.30, Mean negative: ~0.82
        # Score: 0.30 - 0.82 = -0.52
        assert result < 0
        assert -0.6 < result < -0.5

    def test_neutral_score(self):
        """Test calculation with equal similarities."""
        positive_sims = [0.5, 0.5, 0.5]
        negative_sims = [0.5, 0.5, 0.5]

        result = calculate_raw_score(positive_sims, negative_sims)

        assert result == pytest.approx(0.0)

    def test_no_positive_cases(self):
        """Test calculation with no positive cases."""
        positive_sims = []
        negative_sims = [0.5, 0.5, 0.5]

        result = calculate_raw_score(positive_sims, negative_sims)

        # Should be -0.5 (0.0 - 0.5)
        assert result == pytest.approx(-0.5)

    def test_no_negative_cases(self):
        """Test calculation with no negative cases."""
        positive_sims = [0.7, 0.7, 0.7]
        negative_sims = []

        result = calculate_raw_score(positive_sims, negative_sims)

        # Should be 0.7 (0.7 - 0.0)
        assert result == pytest.approx(0.7)

    def test_empty_both(self):
        """Test calculation with empty lists."""
        result = calculate_raw_score([], [])

        assert result == 0.0

    def test_single_values(self):
        """Test calculation with single similarity values."""
        positive_sims = [0.8]
        negative_sims = [0.2]

        result = calculate_raw_score(positive_sims, negative_sims)

        assert result == pytest.approx(0.6)


class TestCalculateConfidenceInterval:
    """Tests for calculate_confidence_interval function."""

    def test_with_sufficient_data(self):
        """Test confidence interval with sufficient data points."""
        positive_sims = [0.85, 0.78, 0.82, 0.80]
        negative_sims = [0.30, 0.25, 0.35, 0.28]

        lower, upper = calculate_confidence_interval(
            positive_sims,
            negative_sims,
            confidence=0.95
        )

        # Check that interval is valid
        assert lower < upper
        # Check that raw score is within interval
        raw_score = calculate_raw_score(positive_sims, negative_sims)
        assert lower <= raw_score <= upper

    def test_with_minimal_data(self):
        """Test confidence interval with minimal data points."""
        positive_sims = [0.8]
        negative_sims = [0.2]

        lower, upper = calculate_confidence_interval(
            positive_sims,
            negative_sims,
            confidence=0.95
        )

        # Should still return an interval
        assert lower < upper
        assert isinstance(lower, float)
        assert isinstance(upper, float)

    def test_with_no_data(self):
        """Test confidence interval with no data."""
        lower, upper = calculate_confidence_interval([], [], confidence=0.95)

        # Should return a small interval around 0
        assert lower < upper
        assert lower < 0 < upper
        # Default interval should be +/- 0.1
        assert lower == pytest.approx(-0.1)
        assert upper == pytest.approx(0.1)

    def test_high_variance_data(self):
        """Test confidence interval with high variance data."""
        positive_sims = [0.95, 0.70, 0.90, 0.75, 0.88]
        negative_sims = [0.50, 0.20, 0.40, 0.30, 0.45]

        lower, upper = calculate_confidence_interval(
            positive_sims,
            negative_sims,
            confidence=0.95
        )

        # High variance should produce wider interval
        interval_width = upper - lower
        assert interval_width > 0.1

    def test_low_variance_data(self):
        """Test confidence interval with low variance data."""
        positive_sims = [0.80, 0.81, 0.79, 0.80, 0.81]
        negative_sims = [0.30, 0.31, 0.29, 0.30, 0.31]

        lower, upper = calculate_confidence_interval(
            positive_sims,
            negative_sims,
            confidence=0.95
        )

        # Low variance should produce narrower interval
        interval_width = upper - lower
        # More data points reduce interval width
        assert interval_width < 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
