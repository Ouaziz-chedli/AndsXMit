"""
Unit tests for the aggregation module.

Tests trimester-specific weight application and weight management.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.aggregation import (
    aggregate_scores,
    get_available_diseases,
    get_disease_weight,
    update_trimester_weight,
    TRIMESTER_WEIGHTS,
)


class TestAggregateScores:
    """Tests for aggregate_scores function."""

    def test_down_syndrome_first_trimester(self):
        """Test Down Syndrome score in first trimester."""
        raw_score = 0.52
        disease = "down_syndrome"
        trimester = "1st"

        result = aggregate_scores(raw_score, disease, trimester)

        # Weight for down_syndrome in 1st trimester is 0.85
        # 0.52 * 0.85 = 0.442
        expected = 0.52 * 0.85
        assert result == pytest.approx(expected)

    def test_down_syndrome_second_trimester(self):
        """Test Down Syndrome score in second trimester."""
        raw_score = 0.52
        disease = "down_syndrome"
        trimester = "2nd"

        result = aggregate_scores(raw_score, disease, trimester)

        # Weight for down_syndrome in 2nd trimester is 0.75
        expected = 0.52 * 0.75
        assert result == pytest.approx(expected)

    def test_down_syndrome_third_trimester(self):
        """Test Down Syndrome score in third trimester."""
        raw_score = 0.52
        disease = "down_syndrome"
        trimester = "3rd"

        result = aggregate_scores(raw_score, disease, trimester)

        # Weight for down_syndrome in 3rd trimester is 0.40
        expected = 0.52 * 0.40
        assert result == pytest.approx(expected)

    def test_cardiac_defect_second_trimester(self):
        """Test cardiac defect score in second trimester (optimal)."""
        raw_score = 0.60
        disease = "cardiac_defect"
        trimester = "2nd"

        result = aggregate_scores(raw_score, disease, trimester)

        # Weight for cardiac_defect in 2nd trimester is 0.90
        expected = 0.60 * 0.90
        assert result == pytest.approx(expected)

    def test_negative_raw_score(self):
        """Test that negative raw scores remain negative after weighting."""
        raw_score = -0.3
        disease = "down_syndrome"
        trimester = "1st"

        result = aggregate_scores(raw_score, disease, trimester)

        # Should stay negative
        assert result < 0

    def test_zero_raw_score(self):
        """Test that zero raw score remains zero."""
        raw_score = 0.0
        disease = "cardiac_defect"
        trimester = "2nd"

        result = aggregate_scores(raw_score, disease, trimester)

        assert result == pytest.approx(0.0)

    def test_invalid_trimester(self):
        """Test that invalid trimester raises error."""
        raw_score = 0.5
        disease = "down_syndrome"
        trimester = "4th"  # Invalid

        with pytest.raises(ValueError, match="Unknown trimester"):
            aggregate_scores(raw_score, disease, trimester)

    def test_unknown_disease_default_weight(self):
        """Test that unknown disease gets default weight."""
        raw_score = 0.5
        disease = "unknown_disease"
        trimester = "1st"

        result = aggregate_scores(raw_score, disease, trimester)

        # Default weight is 0.5
        expected = 0.5 * 0.5
        assert result == pytest.approx(expected)

    def test_extreme_weights(self):
        """Test with extreme weight values."""
        raw_score = 1.0

        # Test with maximum weight scenario (cardiac_defect in 2nd = 0.9)
        result_max = aggregate_scores(raw_score, "cardiac_defect", "2nd")
        assert result_max == pytest.approx(0.9)

        # Test with minimum weight scenario (down_syndrome in 3rd = 0.4)
        result_min = aggregate_scores(raw_score, "down_syndrome", "3rd")
        assert result_min == pytest.approx(0.4)


class TestGetAvailableDiseases:
    """Tests for get_available_diseases function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        diseases = get_available_diseases()
        assert isinstance(diseases, list)

    def test_contains_expected_diseases(self):
        """Test that expected diseases are in the list."""
        diseases = get_available_diseases()

        expected_diseases = [
            "down_syndrome",
            "edwards_syndrome",
            "patau_syndrome",
            "cardiac_defect",
        ]

        for disease in expected_diseases:
            assert disease in diseases

    def test_sorted(self):
        """Test that diseases are alphabetically sorted."""
        diseases = get_available_diseases()
        assert diseases == sorted(diseases)

    def test_not_empty(self):
        """Test that list is not empty."""
        diseases = get_available_diseases()
        assert len(diseases) > 0


class TestGetDiseaseWeight:
    """Tests for get_disease_weight function."""

    def test_valid_combination(self):
        """Test getting weight for valid disease and trimester."""
        weight = get_disease_weight("down_syndrome", "1st")
        assert weight == pytest.approx(0.85)

    def test_different_trimesters(self):
        """Test that different trimesters give different weights."""
        weight_1st = get_disease_weight("down_syndrome", "1st")
        weight_2nd = get_disease_weight("down_syndrome", "2nd")
        weight_3rd = get_disease_weight("down_syndrome", "3rd")

        # Weights should decrease for Down syndrome
        assert weight_1st > weight_2nd > weight_3rd

    def test_unknown_disease_default(self):
        """Test that unknown disease returns default weight."""
        weight = get_disease_weight("unknown_disease", "1st")
        assert weight == 0.5

    def test_invalid_trimester(self):
        """Test that invalid trimester raises error."""
        with pytest.raises(ValueError, match="Unknown trimester"):
            get_disease_weight("down_syndrome", "4th")


class TestUpdateTrimesterWeight:
    """Tests for update_trimester_weight function."""

    def test_update_existing_weight(self):
        """Test updating an existing weight."""
        # Get original weight
        original = get_disease_weight("down_syndrome", "1st")

        # Update weight
        update_trimester_weight("down_syndrome", "1st", 0.99)

        # Verify update
        new_weight = get_disease_weight("down_syndrome", "1st")
        assert new_weight == pytest.approx(0.99)

        # Restore original weight
        update_trimester_weight("down_syndrome", "1st", original)

    def test_add_new_disease_weight(self):
        """Test adding weight for a new disease."""
        new_disease = "test_disease"
        trimester = "1st"
        new_weight = 0.7

        # Add new weight
        update_trimester_weight(new_disease, trimester, new_weight)

        # Verify it was added
        retrieved = get_disease_weight(new_disease, trimester)
        assert retrieved == pytest.approx(new_weight)

    def test_invalid_weight_too_high(self):
        """Test that weight > 1.0 raises error."""
        with pytest.raises(ValueError, match="Weight must be between"):
            update_trimester_weight("down_syndrome", "1st", 1.5)

    def test_invalid_weight_negative(self):
        """Test that negative weight raises error."""
        with pytest.raises(ValueError, match="Weight must be between"):
            update_trimester_weight("down_syndrome", "1st", -0.1)

    def test_boundary_values(self):
        """Test that boundary values 0.0 and 1.0 are accepted."""
        # 0.0 should be valid
        update_trimester_weight("test_disease", "1st", 0.0)

        # 1.0 should be valid
        update_trimester_weight("test_disease", "1st", 1.0)

    def test_invalid_trimester(self):
        """Test that invalid trimester raises error."""
        with pytest.raises(ValueError, match="Unknown trimester"):
            update_trimester_weight("down_syndrome", "4th", 0.5)


class TestTrimesterWeightsConstant:
    """Tests for the TRIMESTER_WEIGHTS constant."""

    def test_structure(self):
        """Test that TRIMESTER_WEIGHTS has correct structure."""
        assert "1st" in TRIMESTER_WEIGHTS
        assert "2nd" in TRIMESTER_WEIGHTS
        assert "3rd" in TRIMESTER_WEIGHTS

        for trimester, diseases in TRIMESTER_WEIGHTS.items():
            assert isinstance(diseases, dict)
            assert len(diseases) > 0

    def test_weights_in_valid_range(self):
        """Test that all weights are between 0 and 1."""
        for trimester, diseases in TRIMESTER_WEIGHTS.items():
            for disease, weight in diseases.items():
                assert 0.0 <= weight <= 1.0, \
                    f"Invalid weight for {disease} in {trimester}: {weight}"

    def test_consistent_diseases_across_trimesters(self):
        """Test that same diseases exist across trimesters (mostly)."""
        diseases_1st = set(TRIMESTER_WEIGHTS["1st"].keys())
        diseases_2nd = set(TRIMESTER_WEIGHTS["2nd"].keys())
        diseases_3rd = set(TRIMESTER_WEIGHTS["3rd"].keys())

        # All diseases should appear in at least 2 trimesters
        all_diseases = diseases_1st | diseases_2nd | diseases_3rd

        for disease in all_diseases:
            trimester_count = sum([
                disease in diseases_1st,
                disease in diseases_2nd,
                disease in diseases_3rd
            ])
            assert trimester_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
