from typing import Optional

from pydantic import BaseModel


class Deficit(BaseModel):
    indicator: str
    score: float
    action: str


class RecommendationItem(BaseModel):
    rank: int
    district_id: int
    name: Optional[str] = None
    overall_score: float
    category: str
    deficit_count: int
    weakest_score: Optional[float] = None
    deficits: list[Deficit] = []
    recommended_actions: list[str] = []


class RecommendationResponse(BaseModel):
    city_id: int
    city_name: Optional[str] = None
    methodology: str
    generated_at: Optional[str] = None
    summary: str
    status: Optional[str] = None
    recommendation_available: bool = True
    priority: list[RecommendationItem] = []
    narrative: Optional[str] = None
