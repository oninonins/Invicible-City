from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.models.facility import Facility
from app.models.spatial import City, District
from app.schemas.facility import Facility as FacilitySchema, FacilityCreate

router = APIRouter()

@router.post("/", response_model=FacilitySchema)
def create_facility(
    *,
    db: Session = Depends(deps.get_db),
    facility_in: FacilityCreate,
) -> Any:
    if facility_in.city_id is not None:
        if db.query(City.id).filter(City.id == facility_in.city_id).first() is None:
            raise HTTPException(status_code=404, detail="city_id not found")
    if facility_in.district_id is not None:
        if db.query(District.id).filter(District.id == facility_in.district_id).first() is None:
            raise HTTPException(status_code=404, detail="district_id not found")

    geom = f"SRID=4326;POINT({facility_in.lng} {facility_in.lat})"
    facility = Facility(
        name=facility_in.name,
        facility_type=facility_in.facility_type,
        lat=facility_in.lat,
        lng=facility_in.lng,
        geom=geom,
        source=facility_in.source,
        external_id=facility_in.external_id,
        raw_tags=facility_in.raw_tags,
        city_id=facility_in.city_id,
        district_id=facility_in.district_id,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility

@router.get("/", response_model=List[FacilitySchema])
def read_facilities(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    facility_type: Optional[str] = None,
    city_id: Optional[int] = Query(None, description="Filter by city_id"),
    district_id: Optional[int] = Query(None, description="Filter by district_id"),
) -> Any:
    query = db.query(Facility)
    if facility_type:
        query = query.filter(Facility.facility_type == facility_type)
    if city_id:
        query = query.filter(Facility.city_id == city_id)
    if district_id:
        query = query.filter(Facility.district_id == district_id)
    facilities = query.order_by(Facility.id).offset(skip).limit(limit).all()
    return facilities
