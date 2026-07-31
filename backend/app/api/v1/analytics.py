from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.models.spatial import City, District
from app.models.ufs import UfsIndicator
from app.services import ufs as ufs_service

router = APIRouter()

@router.get("/ufs", response_model=Dict[str, Any])
def get_urban_fairness_score(
    city_id: Optional[int] = Query(None, description="Filter by city_id"),
    district_id: Optional[int] = Query(None, description="Filter by district_id"),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Calculate the Urban Fairness Score (UFS v0 — provision-based).

    Methodology (see docs/UFS_METHODOLOGY.md):
    - 5 indicators, 20% weight each: education, healthcare, transportation,
      public space, accessibility.
    - Benchmarks = national median density over districts with >=1 facility.
    - Accessibility = kNN distance (meter geography) from district centroid to
      nearest facility of each type, 1km reference, Euclidean proxy.
    - City score = mean of district scores.
    """
    if db.query(UfsIndicator).count() == 0:
        ufs_service.refresh_benchmarks(db)

    if district_id is not None:
        if db.query(District.id).filter(District.id == district_id).first() is None:
            raise HTTPException(status_code=404, detail="District not found")
        return ufs_service.get_district_ufs(db, district_id)

    if city_id is not None:
        if db.query(City.id).filter(City.id == city_id).first() is None:
            raise HTTPException(status_code=404, detail="City not found")
        return ufs_service.get_city_ufs(db, city_id)

    raise HTTPException(status_code=422, detail="city_id or district_id is required")
