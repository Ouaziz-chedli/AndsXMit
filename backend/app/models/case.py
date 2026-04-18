from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
from .patient import PatientContext


class ImageData(BaseModel):
    url: str
    format: Literal["dicom", "jpeg", "png"]


class DiseaseCase(BaseModel):
    case_id: str
    disease_id: str
    trimester: Literal["1st", "2nd", "3rd"]
    label: Literal["positive", "negative"]

    images: List[ImageData] = []
    symptom_text: str

    image_embedding: List[float] = []
    text_embedding: List[float] = []

    gestational_age_weeks: float
    b_hcg_mom: Optional[float] = None
    papp_a_mom: Optional[float] = None

    equipment_manufacturer: Optional[str] = None
    acquisition_params: Optional[dict] = None

    patient_context: Optional[PatientContext] = None

    source_institution: str = ""
    diagnosing_physician: str = ""
    confirmation_method: str = ""
    anonymized: bool = True

    created_at: datetime = datetime.now()
    validated: bool = False
