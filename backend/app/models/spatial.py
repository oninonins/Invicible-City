from sqlalchemy import Column, Integer, String, ForeignKey
from geoalchemy2 import Geometry
from sqlalchemy.orm import relationship
from app.db.base import Base

class Province(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    geom = Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326), nullable=True)

class City(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    province_id = Column(Integer, ForeignKey("province.id"), nullable=True)
    geom = Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326), nullable=True)
    
    # province = relationship("Province")
    # districts = relationship("District", back_populates="city")

class District(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    city_id = Column(Integer, ForeignKey("city.id"), nullable=False)
    geom = Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326), nullable=True)

    # city = relationship("City", back_populates="districts")
