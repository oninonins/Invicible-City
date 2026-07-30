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
    data_source = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    metadata_info = Column(JSON, nullable=True)

class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"
    id = Column(Integer, primary_key=True, index=True)
    layer_name = Column(String, nullable=False, index=True)
    download_date = Column(DateTime(timezone=True), server_default=func.now())
    record_count = Column(Integer, nullable=False)
    source = Column(String, nullable=False)
    version = Column(String, nullable=True)
    status = Column(String, nullable=False, default="downloaded")
