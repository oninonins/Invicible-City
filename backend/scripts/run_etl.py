import sys
import os
import argparse
import logging
from datetime import datetime

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.etl import ETLJob
from app.etl.osm import extract_city_boundary, extract_facilities, transform_facilities, load_city_and_facilities

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_pipeline(city_name: str):
    db = SessionLocal()
    
    # 1. Register ETL Job
    job = ETLJob(
        city_name=city_name,
        data_source="OSM (Overpass)",
        status="RUNNING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"Started ETL Job ID {job.id} for {city_name}")
    
    try:
        # EXTRACT
        city_gdf = extract_city_boundary(city_name)
        if city_gdf.empty:
            raise ValueError(f"Could not find boundary for {city_name}")
            
        fac_gdf = extract_facilities(city_name)
        
        # TRANSFORM
        fac_gdf_clean = transform_facilities(fac_gdf)
        
        # LOAD
        result = load_city_and_facilities(db, city_name, city_gdf, fac_gdf_clean)
        
        # FINAL METADATA
        job.status = "SUCCESS"
        job.completed_at = datetime.utcnow()
        job.metadata_info = result
        db.commit()
        
        logger.info(f"ETL Job {job.id} completed successfully! Imported {result['facilities_inserted']} facilities.")
        
    except Exception as e:
        logger.error(f"ETL Job {job.id} failed: {str(e)}")
        job.status = "FAILED"
        job.completed_at = datetime.utcnow()
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Geospatial ETL Pipeline')
    parser.add_argument('city', type=str, help='Name of the city to import (e.g., "Malang, Indonesia")')
    args = parser.parse_args()
    
    run_pipeline(args.city)
