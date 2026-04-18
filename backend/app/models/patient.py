from pydantic import BaseModel
from typing import Optional


class PatientContextMoM(BaseModel):
    """
    MoM-normalized patient context for risk calculation.
    Using Multiple of Median removes gestational age dependency from biomarkers.
    """
    b_hcg_mom: Optional[float] = None
    papp_a_mom: Optional[float] = None
    mother_age: int
    gestational_age_weeks: float
    previous_affected_pregnancy: bool = False


class PatientContext(BaseModel):
    """
    First-trimester screening context.
    Based on French NT-prenatal screening protocol (11-14 weeks).
    """
    b_hcg: Optional[float] = None          # IU/L, serum biomarker
    papp_a: Optional[float] = None         # IU/L, serum biomarker
    mother_age: int                        # Age at due date
    gestational_age_weeks: float           # Weeks since LMP/conception
    previous_affected_pregnancy: bool = False  # Prior chromosomal anomaly

    def to_mom(self) -> PatientContextMoM:
        """
        Convert raw values to MoM (Multiple of Median).
        MoM normalizes for gestational age and gives population-relative values.
        """
        # Median values at 10 weeks (typical first-trimester screening timing)
        MEDIAN_B_HCG = 50000.0  # IU/L
        MEDIAN_PAPP_A = 1500.0  # IU/L
        return PatientContextMoM(
            b_hcg_mom=self.b_hcg / MEDIAN_B_HCG if self.b_hcg else None,
            papp_a_mom=self.papp_a / MEDIAN_PAPP_A if self.papp_a else None,
            mother_age=self.mother_age,
            gestational_age_weeks=self.gestational_age_weeks,
            previous_affected_pregnancy=self.previous_affected_pregnancy,
        )
