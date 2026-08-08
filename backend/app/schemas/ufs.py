from typing import Optional

from pydantic import BaseModel


class UfsPerDistrict(BaseModel):
    district_id: int
    name: Optional[str] = None
    overall_score: float
    category: str
    indicators: dict[str, Optional[float]] = {}
    total_facilities: int
    breakdown: dict[str, int] = {}


class UfsResponse(BaseModel):
    scope_type: str
    scope_id: int
    name: Optional[str] = None
    overall_score: float
    total_facilities: int
    breakdown: dict[str, int] = {}
    status: str
    category: str
    indicators: dict[str, Optional[float]] = {}
    methodology: str
    district_count: int
    per_district: list[UfsPerDistrict] = []
    computed_at: Optional[str] = None
