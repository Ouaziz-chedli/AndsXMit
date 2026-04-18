from pydantic import BaseModel
from typing import Dict, Tuple


class TrimesterProfile(BaseModel):
    trimester: str
    symptom_weights: Dict[str, float]
    normal_ranges: Dict[str, Tuple[float, float]]


class Disease(BaseModel):
    disease_id: str
    name: str
    description: str
    trimester_profiles: Dict[str, TrimesterProfile]
    base_prevalence: float
