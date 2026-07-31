from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.api import deps
from app.core.config import settings
from app.db.base import Base
from app.main import app
from app.models.facility import Facility
from app.models.spatial import City, District, Province
from app.models.ufs import UfsIndicator, UfsScore  # noqa: F401  (register in Base.metadata)

TEST_DB_NAME = "sdgs_test"


def _db_url(database: str) -> str:
    return (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{database}"
    )


def _multipolygon(coords: str) -> str:
    return f"SRID=4326;MULTIPOLYGON((({coords})))"


@pytest.fixture(scope="session")
def test_engine():
    admin_engine = create_engine(_db_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    engine = create_engine(_db_url(TEST_DB_NAME))
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def api_session(test_engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def client(api_session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield api_session

    app.dependency_overrides[deps.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(deps.get_db, None)


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def seeded(db_session) -> None:
    db_session.execute(
        text("TRUNCATE facility, district, city, province, ufs_scores, ufs_indicators RESTART IDENTITY CASCADE")
    )
    db_session.commit()

    province = Province(code="11", name="Test Province")
    db_session.add(province)
    db_session.flush()

    city_a = City(
        code="1101",
        name="City A",
        province_id=province.id,
        geom=_multipolygon("106.7 -6.1, 106.9 -6.1, 106.9 -6.3, 106.7 -6.3, 106.7 -6.1"),
    )
    city_b = City(code="1102", name="City B", province_id=province.id)
    db_session.add_all([city_a, city_b])
    db_session.flush()

    districts = [
        District(
            code="110101",
            name="District 1",
            city_id=city_a.id,
            geom=_multipolygon(
                "106.75 -6.15, 106.85 -6.15, 106.85 -6.25, 106.75 -6.25, 106.75 -6.15"
            ),
        ),
        District(
            code="110102",
            name="District 2",
            city_id=city_a.id,
            geom=_multipolygon(
                "106.75 -6.25, 106.85 -6.25, 106.85 -6.35, 106.75 -6.35, 106.75 -6.25"
            ),
        ),
        District(
            code="110103",
            name="District 3",
            city_id=city_a.id,
            geom=_multipolygon(
                "106.85 -6.15, 106.9 -6.15, 106.9 -6.2, 106.85 -6.2, 106.85 -6.15"
            ),
        ),
    ]
    db_session.add_all(districts)
    db_session.flush()

    facilities = [
        Facility(
            name="School A",
            facility_type="School",
            lat=-6.2,
            lng=106.8,
            geom="SRID=4326;POINT(106.8 -6.2)",
            source="OSM",
            external_id="e1",
            city_id=city_a.id,
            district_id=districts[0].id,
        ),
        Facility(
            name="School B",
            facility_type="School",
            lat=-6.3,
            lng=106.9,
            geom="SRID=4326;POINT(106.9 -6.3)",
            source="OSM",
            external_id="e2",
            city_id=city_a.id,
            district_id=districts[0].id,
        ),
        Facility(
            name="Hospital A",
            facility_type="Hospital",
            lat=-6.4,
            lng=107.0,
            geom="SRID=4326;POINT(107.0 -6.4)",
            source="OSM",
            external_id="e3",
            city_id=city_a.id,
            district_id=districts[1].id,
        ),
        Facility(
            name="Park A",
            facility_type="Park",
            lat=-6.5,
            lng=107.1,
            geom="SRID=4326;POINT(107.1 -6.5)",
            source="OSM",
            external_id=None,
            city_id=city_a.id,
            district_id=districts[2].id,
        ),
        Facility(
            name="Clinic A",
            facility_type="Clinic",
            lat=-6.6,
            lng=107.2,
            geom="SRID=4326;POINT(107.2 -6.6)",
            source="OSM",
            external_id=None,
            city_id=None,
            district_id=None,
        ),
    ]
    db_session.add_all(facilities)
    db_session.commit()
