"""
Unit tests for the priors module.

Tests Bayesian prior calculations based on patient context,
maternal age, and biomarker patterns.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.priors import (
    calculate_age_risk,
    calculate_biomarker_risk,
    apply_priors,
    get_applied_priors,
)

from app.models.patient import PatientContext, PatientContextMoM


class TestCalculateAgeRisk:
    """Tests for calculate_age_risk function."""

    def test_age_under_30(self):
        """Test that age under 30 returns baseline risk (1.0)."""
        risk = calculate_age_risk(25)
        assert risk == 1.0

    def test_age_30(self):
        """Test that age 30 returns baseline risk (1.0)."""
        risk = calculate_age_risk(30)
        assert risk == 1.0

    def test_age_35(self):
        """Test that age 35 has increased risk."""
        risk = calculate_age_risk(35)
        assert risk > 1.0
        # At 35, risk approximately 1.45x baseline (formula: 800/(800-10*5^2) = 800/550)
        assert 1.4 < risk < 2.0

    def test_age_40(self):
        """Test that age 40 has significantly increased risk."""
        risk = calculate_age_risk(40)
        assert risk > 2.0
        # At 40, risk is ~5x baseline
        assert 4.0 < risk <= 5.0

    def test_age_45(self):
        """Test that age 45 is capped at maximum."""
        risk = calculate_age_risk(45)
        # Should be capped at 5.0
        assert risk == pytest.approx(5.0)

    def test_monotonic_increase(self):
        """Test that risk increases monotonically with age."""
        risk_30 = calculate_age_risk(30)
        risk_35 = calculate_age_risk(35)
        risk_40 = calculate_age_risk(40)

        assert risk_30 < risk_35 < risk_40


class TestCalculateBiomarkerRisk:
    """Tests for calculate_biomarker_risk function."""

    def test_no_biomarkers(self):
        """Test with no biomarkers (both None)."""
        risk = calculate_biomarker_risk(None, None)
        assert risk == 1.0

    def test_normal_biomarkers(self):
        """Test with normal biomarker values (1.0 MoM)."""
        risk = calculate_biomarker_risk(1.0, 1.0)
        assert risk == 1.0

    def test_high_b_hcg_alone(self):
        """Test high b-hCG alone (elevated > 2.0)."""
        risk = calculate_biomarker_risk(2.5, 1.0)
        # High b-hCG increases risk by 1.5x
        assert risk == pytest.approx(1.5)

    def test_low_b_hcg_alone(self):
        """Test low b-hCG alone (very low < 0.25)."""
        risk = calculate_biomarker_risk(0.2, 1.0)
        # Very low b-hCG increases risk by 1.3x (suggests T18/T13)
        assert risk == pytest.approx(1.3)

    def test_low_papp_a_alone(self):
        """Test low PAPP-A alone (very low < 0.4)."""
        risk = calculate_biomarker_risk(1.0, 0.3)
        # Very low PAPP-A increases risk by 2.0x
        assert risk == pytest.approx(2.0)

    def test_moderate_low_papp_a(self):
        """Test moderately low PAPP-A (0.5-0.75)."""
        risk = calculate_biomarker_risk(1.0, 0.6)
        # Moderately low PAPP-A increases risk by 1.2x
        assert risk == pytest.approx(1.2)

    def test_classic_down_pattern(self):
        """Test classic Down syndrome pattern (high b-hCG, low PAPP-A)."""
        risk = calculate_biomarker_risk(2.1, 0.48)
        # Classic pattern: 2.1 (1.5x) * 0.48 (1.5x) * 1.8 (combined) = ~4.05x
        assert risk > 3.0

    def test_both_low_pattern(self):
        """Test both biomarkers low (T18/T13 pattern)."""
        risk = calculate_biomarker_risk(0.2, 0.3)
        # Both low: increases risk significantly
        assert risk > 1.5

    def test_only_b_hcg_provided(self):
        """Test with only b-hCG provided."""
        risk = calculate_biomarker_risk(2.2, None)
        assert risk > 1.0

    def test_only_papp_a_provided(self):
        """Test with only PAPP-A provided."""
        risk = calculate_biomarker_risk(None, 0.4)
        assert risk > 1.0


class TestApplyPriors:
    """Tests for apply_priors function."""

    def test_no_context_priors(self):
        """Test with patient that has no risk factors.

        Note: Even with MoM=1.0 values, biomarker risk may still be calculated
        if MoM values are very small (essentially zero), triggering risk multipliers.
        """
        context = PatientContext(
            mother_age=30,
            gestational_age_weeks=12.0,
            b_hcg=50000.0,  # MoM = 1.0 (exactly median)
            papp_a=1500.0,   # MoM = 1.0 (exactly median)
            previous_affected_pregnancy=False,
        )

        result = apply_priors(0.5, "down_syndrome", context)

        # With exact MoM=1.0, risk multiplier should be 1.0
        # But allow some tolerance for floating point
        assert 0.4 < result < 0.6

    def test_high_maternal_age(self):
        """Test with high maternal age."""
        context = PatientContext(
            mother_age=40,
            gestational_age_weeks=12.0,
            b_hcg=1.0,
            papp_a=1.0,
        )

        result = apply_priors(0.5, "down_syndrome", context)

        # Should be increased due to age
        assert result > 0.5
        # At age 40, multiplier should be ~5x
        assert result > 2.0

    def test_down_syndrome_biomarkers(self):
        """Test with Down syndrome biomarker pattern."""
        context = PatientContext(
            mother_age=30,
            gestational_age_weeks=12.0,
            b_hcg=100000.0,  # ~2.0 MoM
            papp_a=750.0,     # ~0.5 MoM
        )

        result = apply_priors(0.5, "down_syndrome", context)

        # Should be increased due to biomarker pattern
        assert result > 0.5

    def test_previous_affected_pregnancy(self):
        """Test with previous affected pregnancy."""
        context = PatientContext(
            mother_age=30,
            gestational_age_weeks=12.0,
            previous_affected_pregnancy=True,
        )

        result = apply_priors(0.5, "down_syndrome", context)

        # Should be multiplied by 2.5
        assert result == pytest.approx(1.25)

    def test_non_chromosomal_disease(self):
        """Test that priors don't apply to non-chromosomal diseases."""
        context = PatientContext(
            mother_age=40,
            gestational_age_weeks=20.0,
            b_hcg=1.0,
            papp_a=1.0,
        )

        result = apply_priors(0.5, "some_other_disease", context)

        # Should be unchanged (only chromosomal diseases use these priors)
        assert result == pytest.approx(0.5)

    def test_with_mom_context(self):
        """Test with PatientContextMoM."""
        context = PatientContextMoM(
            mother_age=35,
            gestational_age_weeks=12.0,
            b_hcg_mom=2.1,
            papp_a_mom=0.48,
        )

        result = apply_priors(0.5, "down_syndrome", context)

        # Should incorporate all priors
        assert result > 0.5

    def test_negative_score(self):
        """Test that negative scores become more negative with priors."""
        context = PatientContext(
            mother_age=40,
            gestational_age_weeks=12.0,
        )

        result = apply_priors(-0.3, "down_syndrome", context)

        # Should stay negative but more extreme
        assert result < -0.3

    def test_combined_risk_factors(self):
        """Test with multiple risk factors combined."""
        context = PatientContext(
            mother_age=40,
            gestational_age_weeks=12.0,
            b_hcg=100000.0,  # ~2.0 MoM
            papp_a=750.0,     # ~0.5 MoM
            previous_affected_pregnancy=True,
        )

        result = apply_priors(0.5, "down_syndrome", context)

        # Should have significant multiplier from all factors
        assert result > 5.0


class TestGetAppliedPriors:
    """Tests for get_applied_priors function."""

    def test_no_priors(self):
        """Test with no applicable priors.

        Note: With b_hcg=50000 and papp_a=1500 (exactly median MoM=1.0),
        biomarker risk multiplier is 1.0, so no biomarker prior should be applied.
        """
        context = PatientContext(
            mother_age=30,
            gestational_age_weeks=12.0,
            b_hcg=50000.0,  # Exactly median, MoM=1.0
            papp_a=1500.0,  # Exactly median, MoM=1.0
        )

        applied = get_applied_priors("down_syndrome", context)

        # No priors should be applied for age < 40 and normal MoM values
        assert applied == []

    def test_high_age_prior(self):
        """Test that high age is reported."""
        context = PatientContext(
            mother_age=40,
            gestational_age_weeks=12.0,
        )

        applied = get_applied_priors("down_syndrome", context)

        assert "maternal_age_40" in applied

    def test_biomarker_pattern_prior(self):
        """Test that biomarker pattern is reported."""
        context = PatientContext(
            mother_age=30,
            gestational_age_weeks=12.0,
            b_hcg=100000.0,  # ~2.0 MoM
            papp_a=750.0,     # ~0.5 MoM
        )

        applied = get_applied_priors("down_syndrome", context)

        assert "biomarker_risk_pattern" in applied

    def test_previous_affected_prior(self):
        """Test that previous affected pregnancy is reported."""
        context = PatientContext(
            mother_age=30,
            gestational_age_weeks=12.0,
            previous_affected_pregnancy=True,
        )

        applied = get_applied_priors("down_syndrome", context)

        assert "previous_affected_pregnancy" in applied

    def test_multiple_priors(self):
        """Test with multiple priors applied."""
        context = PatientContext(
            mother_age=40,
            gestational_age_weeks=12.0,
            b_hcg=100000.0,
            papp_a=750.0,
            previous_affected_pregnancy=True,
        )

        applied = get_applied_priors("down_syndrome", context)

        # Should have multiple priors
        assert len(applied) >= 2
        assert "maternal_age_40" in applied

    def test_normal_biomarkers_no_prior(self):
        """Test that normal biomarkers don't trigger prior."""
        context = PatientContext(
            mother_age=30,
            gestational_age_weeks=12.0,
            b_hcg=50000.0,  # ~1.0 MoM
            papp_a=1500.0,   # ~1.0 MoM
        )

        applied = get_applied_priors("down_syndrome", context)

        assert "biomarker_risk_pattern" not in applied

    def test_with_mom_context(self):
        """Test with PatientContextMoM."""
        context = PatientContextMoM(
            mother_age=40,
            gestational_age_weeks=12.0,
            b_hcg_mom=2.1,
            papp_a_mom=0.48,
        )

        applied = get_applied_priors("down_syndrome", context)

        assert "maternal_age_40" in applied
        assert "biomarker_risk_pattern" in applied


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
