from sqlalchemy import func, text

from app.models.facility import Facility


def test_facility_geometry_not_null(db_session):
    null_count = db_session.query(Facility).filter(Facility.geom.is_(None)).count()
    assert null_count == 0


def test_facility_coordinates_match_geometry(db_session):
    rows = db_session.query(
        Facility.id,
        func.ST_X(Facility.geom),
        func.ST_Y(Facility.geom),
        Facility.lng,
        Facility.lat,
    ).all()
    assert len(rows) == 5
    for _id, geom_x, geom_y, lng, lat in rows:
        assert geom_x == lng
        assert geom_y == lat


def test_no_duplicate_source_external_id(db_session):
    pairs = db_session.query(Facility.source, Facility.external_id).filter(
        Facility.external_id.isnot(None)
    ).all()
    assert len(pairs) == len(set(pairs))


def test_unique_source_external_id_index_exists(db_session):
    count = db_session.execute(
        text(
            "SELECT count(*) FROM pg_indexes "
            "WHERE tablename = 'facility' AND indexname = 'idx_facility_source_eid'"
        )
    ).scalar()
    assert count == 1


def test_facility_fk_integrity(db_session):
    bad_city = db_session.execute(
        text(
            "SELECT count(*) FROM facility f "
            "LEFT JOIN city c ON f.city_id = c.id "
            "WHERE f.city_id IS NOT NULL AND c.id IS NULL"
        )
    ).scalar()
    bad_district = db_session.execute(
        text(
            "SELECT count(*) FROM facility f "
            "LEFT JOIN district d ON f.district_id = d.id "
            "WHERE f.district_id IS NOT NULL AND d.id IS NULL"
        )
    ).scalar()
    assert bad_city == 0
    assert bad_district == 0
