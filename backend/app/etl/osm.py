import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, MultiPolygon
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from app.models.spatial import City
from app.models.facility import Facility
import logging

logger = logging.getLogger(__name__)

def ensure_multipolygon(geom):
    if geom.geom_type == 'Polygon':
        return MultiPolygon([geom])
    elif geom.geom_type == 'MultiPolygon':
        return geom
    return None

def extract_city_boundary(city_name: str) -> gpd.GeoDataFrame:
    """Extracts city boundary from OSM."""
    logger.info(f"Extracting boundary for {city_name} from OSM...")
    gdf = ox.geocode_to_gdf(city_name)
    return gdf

def extract_facilities(city_name: str) -> gpd.GeoDataFrame:
    """Extracts public facilities for a city from OSM."""
    logger.info(f"Extracting facilities for {city_name} from OSM...")
    tags = {
        'amenity': ['school', 'hospital', 'clinic', 'bus_station'],
        'public_transport': ['station', 'stop_position']
    }
    # Use features_from_place for osmnx >= 2.0 (we use 2.0.7)
    gdf = ox.features_from_place(city_name, tags=tags)
    return gdf

def transform_facilities(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Transforms facilities to ensure they are point geometries."""
    logger.info("Transforming facilities...")
    gdf = gdf.copy()
    
    # If geometry is a polygon (e.g. a hospital building), take its centroid
    non_points = gdf.geom_type != 'Point'
    if non_points.any():
        # warning: centroid of geographic coordinates is just a mathematical center
        gdf.loc[non_points, 'geometry'] = gdf[non_points].geometry.centroid
        
    # Standardize types for MVP mapping
    def map_type(row):
        amenity = row.get('amenity', '')
        if amenity in ['school']: return 'School'
        if amenity in ['hospital', 'clinic']: return 'Healthcare'
        return 'Transport'
        
    gdf['mapped_type'] = gdf.apply(map_type, axis=1)
    
    return gdf

def load_city_and_facilities(db: Session, city_name: str, city_gdf: gpd.GeoDataFrame, fac_gdf: gpd.GeoDataFrame):
    """Loads transformed data into PostGIS."""
    logger.info("Loading data into PostGIS...")
    
    # 1. Check if city already exists (Idempotency)
    city_record = db.query(City).filter(City.name == city_name).first()
    if not city_record:
        geom = city_gdf.iloc[0].geometry
        mp_geom = ensure_multipolygon(geom)
        
        city_record = City(
            name=city_name,
            geom=from_shape(mp_geom, srid=4326)
        )
        db.add(city_record)
        db.commit()
        db.refresh(city_record)
        logger.info(f"Inserted new City: {city_name} with ID {city_record.id}")
    else:
        logger.info(f"City {city_name} already exists (ID: {city_record.id}). Updating facilities.")

    # 2. Delete existing facilities for this city to prevent duplicates during re-run (Idempotency)
    deleted_count = db.query(Facility).filter(Facility.city_id == city_record.id).delete()
    db.commit()
    logger.info(f"Deleted {deleted_count} existing facilities for {city_name}.")
    
    # 3. Insert new facilities
    facilities_to_insert = []
    for idx, row in fac_gdf.iterrows():
        name = row.get('name')
        if not name or str(name) == 'nan':
            continue # Skip unnamed facilities for MVP quality
            
        geom = row.geometry
        
        facility = Facility(
            name=str(name),
            facility_type=row['mapped_type'],
            lat=geom.y,
            lng=geom.x,
            geom=from_shape(geom, srid=4326),
            city_id=city_record.id
        )
        facilities_to_insert.append(facility)
        
    db.bulk_save_objects(facilities_to_insert)
    db.commit()
    logger.info(f"Inserted {len(facilities_to_insert)} facilities for {city_name}.")
    
    return {
        "city_id": city_record.id,
        "facilities_inserted": len(facilities_to_insert)
    }
