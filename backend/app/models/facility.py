from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
from app.db.base import Base

class Facility(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    facility_type = Column(String, index=True, nullable=False) # e.g. 'school', 'hospital'
    
    # Store standard lat/lng for easy frontend consumption
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    
    # PostGIS point geometry (SRID 4326 = WGS84 standard)
    geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
