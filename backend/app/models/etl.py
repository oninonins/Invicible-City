from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class ETLJob(Base):
    """
    Tracks ETL executions to ensure idempotency and store metadata.
    """
    __tablename__ = "etl_job"
    id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String, index=True, nullable=False)
    data_source = Column(String, nullable=False) # e.g. "OSM", "BPS"
    status = Column(String, nullable=False) # "PENDING", "SUCCESS", "FAILED"
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    metadata_info = Column(JSON, nullable=True) # E.g. {"nodes_imported": 100}
