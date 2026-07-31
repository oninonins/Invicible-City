from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class UfsIndicator(Base):
    __tablename__ = "ufs_indicators"

    id = Column(Integer, primary_key=True, index=True)
    indicator = Column(String, unique=True, index=True, nullable=False)
    weight = Column(Float, nullable=False, default=0.2)
    benchmark_density = Column(Float, nullable=True)
    reference_km = Column(Float, nullable=True)
    benchmark_note = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UfsScore(Base):
    __tablename__ = "ufs_scores"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", name="uq_ufs_scope"),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String, nullable=False)
    scope_id = Column(Integer, nullable=False)
    overall_score = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    indicators = Column(JSONB, nullable=True)
    total_facilities = Column(Integer, nullable=False, default=0)
    breakdown = Column(JSONB, nullable=True)
    district_count = Column(Integer, nullable=False, default=0)
    methodology = Column(String, nullable=False, default="v0-provision")
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
