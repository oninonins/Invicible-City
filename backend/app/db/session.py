from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Construct PostgreSQL connection string
if settings.DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_SERVER}:"
        f"{settings.POSTGRES_PORT}/"
        f"{settings.POSTGRES_DB}"
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
