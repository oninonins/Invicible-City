from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Index
from geoalchemy2 import Geometry
from app.db.base import Base

class Facility(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    facility_type = Column(String, index=True, nullable=False)

    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)

    geom = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)

    source = Column(String, nullable=False, default="OSM")
    external_id = Column(String, nullable=True)
    raw_tags = Column(JSON, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)

    city_id = Column(Integer, ForeignKey("city.id"), nullable=True)
    district_id = Column(Integer, ForeignKey("district.id"), nullable=True)

    __table_args__ = (
        Index("idx_facility_source_eid", "source", "external_id", unique=True, postgresql_where=None),
        Index("idx_facility_type_city", "facility_type", "city_id"),
        Index("idx_facility_district", "district_id"),
    )

