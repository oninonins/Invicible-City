from typing import Any, List, Dict
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from sqlalchemy import func
from app.models.spatial import City, District

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
def get_cities(db: Session = Depends(deps.get_db)) -> Any:
    """
    Get all cities for geographic context selection.
    """
    cities = db.query(City).all()
    # If no cities exist yet (ETL pending), return a dummy list for MVP
    if not cities:
        return [
            {"id": 3573, "name": "Malang"},
            {"id": 3171, "name": "Jakarta Pusat"},
            {"id": 3273, "name": "Bandung"}
        ]
        
    return [{"id": c.id, "name": c.name} for c in cities]

@router.get("/{city_id}/boundary", response_model=Dict[str, Any])
def get_city_boundary(city_id: int, db: Session = Depends(deps.get_db)) -> Any:
    """
    Get the GeoJSON boundary of a specific city.
    """
    geojson_str = db.query(func.ST_AsGeoJSON(City.geom)).filter(City.id == city_id).scalar()
    if not geojson_str:
        raise HTTPException(status_code=404, detail="City boundary not found")
        
    geometry = json.loads(geojson_str)
    
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"city_id": city_id},
                "geometry": geometry
            }
        ]
    }

@router.get("/{city_id}/districts", response_model=Dict[str, Any])
def get_city_districts(city_id: int, db: Session = Depends(deps.get_db)) -> Any:
    """
    Get all districts within a city as a GeoJSON FeatureCollection.
    """
    results = db.query(
        District.id,
        District.name,
        func.ST_AsGeoJSON(District.geom).label('geom_geojson')
    ).filter(District.city_id == city_id).all()
    
    features = []
    for row in results:
        if row.geom_geojson:
            features.append({
                "type": "Feature",
                "properties": {
                    "id": row.id,
                    "name": row.name
                },
                "geometry": json.loads(row.geom_geojson)
            })
            
    return {
        "type": "FeatureCollection",
        "features": features
    }
