from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.models.facility import Facility
from app.schemas.facility import Facility as FacilitySchema, FacilityCreate

router = APIRouter()

@router.post("/", response_model=FacilitySchema)
def create_facility(
    *,
    db: Session = Depends(deps.get_db),
    facility_in: FacilityCreate,
) -> Any:
    """
    Create new facility.
    """
    # Simple WKT conversion for PostGIS POINT geometry
    geom = f"SRID=4326;POINT({facility_in.lng} {facility_in.lat})"
    facility = Facility(
        name=facility_in.name,
        facility_type=facility_in.facility_type,
        lat=facility_in.lat,
        lng=facility_in.lng,
        geom=geom,
        city_id=facility_in.city_id
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility

@router.get("/", response_model=List[FacilitySchema])
def read_facilities(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    facility_type: Optional[str] = None,
    city_id: Optional[int] = Query(None, description="Filter by city_id")
) -> Any:
    """
    Retrieve facilities.
    """
    query = db.query(Facility)
    if facility_type:
        query = query.filter(Facility.facility_type == facility_type)
    if city_id:
        query = query.filter(Facility.city_id == city_id)
    facilities = query.offset(skip).limit(limit).all()
    return facilities
