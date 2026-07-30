from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class FacilityBase(BaseModel):
    name: str
    facility_type: str
    lat: float
    lng: float
    source: str = "OSM"
    external_id: Optional[str] = None
    raw_tags: Optional[dict[str, Any]] = None
    city_id: Optional[int] = None
    district_id: Optional[int] = None

class FacilityCreate(FacilityBase):
    pass

class Facility(FacilityBase):
    id: int
    source_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
