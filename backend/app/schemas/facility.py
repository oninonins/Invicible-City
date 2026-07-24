from pydantic import BaseModel
from typing import Optional

class FacilityBase(BaseModel):
    name: str
    facility_type: str
    lat: float
    lng: float

class FacilityCreate(FacilityBase):
    pass

class Facility(FacilityBase):
    id: int

    class Config:
        from_attributes = True
