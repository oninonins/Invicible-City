from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api import deps
from app.models.facility import Facility

router = APIRouter()

@router.get("/ufs", response_model=Dict[str, Any])
def get_urban_fairness_score(
    city_id: Optional[int] = Query(None, description="Filter by city_id"),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Calculate the Urban Fairness Score (UFS) based on available public facilities.
    For the MVP, this is a simplified calculation:
    We expect an ideal city to have a baseline number of facilities (e.g., 20).
    The score is the percentage of that baseline met, capped at 100.
    """
    query = db.query(Facility)
    if city_id:
        query = query.filter(Facility.city_id == city_id)
        
    total_facilities = query.count()
    
    # Calculate score
    baseline = 20.0
    score = min((total_facilities / baseline) * 100, 100.0)
    
    # Get breakdown by type
    breakdown_query = db.query(Facility.facility_type, func.count(Facility.id))
    if city_id:
        breakdown_query = breakdown_query.filter(Facility.city_id == city_id)
        
    breakdown = breakdown_query.group_by(Facility.facility_type).all()
    type_counts = {item[0]: item[1] for item in breakdown}
    
    return {
        "overall_score": round(score, 1),
        "total_facilities": total_facilities,
        "breakdown": type_counts,
        "status": "Good" if score >= 70 else "Fair" if score >= 40 else "Poor"
    }
