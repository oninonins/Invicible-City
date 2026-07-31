from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class FacilityBase(BaseModel):
    name: str = Field(min_length=1)
    facility_type: str = Field(min_length=1)
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
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
