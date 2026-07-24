from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api import deps
from app.models.facility import Facility

router = APIRouter()

@router.get("/ufs", response_model=Dict[str, Any])
def get_urban_fairness_score(db: Session = Depends(deps.get_db)) -> Any:
    """
    Calculate the Urban Fairness Score (UFS) based on available public facilities.
    For the MVP, this is a simplified calculation:
    We expect an ideal city to have a baseline number of facilities (e.g., 20).
    The score is the percentage of that baseline met, capped at 100.
    """
    total_facilities = db.query(Facility).count()
    
    # Calculate score
    baseline = 20.0
    score = min((total_facilities / baseline) * 100, 100.0)
    
    # Get breakdown by type
    breakdown = db.query(Facility.facility_type, func.count(Facility.id)).group_by(Facility.facility_type).all()
    type_counts = {item[0]: item[1] for item in breakdown}
    
    return {
        "overall_score": round(score, 1),
        "total_facilities": total_facilities,
        "breakdown": type_counts,
        "status": "Good" if score >= 70 else "Fair" if score >= 40 else "Poor"
    }
