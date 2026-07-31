from sqlalchemy import text

from app.models.ufs import UfsIndicator, UfsScore
from app.services import ufs as ufs_service


def test_five_indicators(client):
    body = client.get("/api/v1/analytics/ufs?city_id=1").json()
    assert set(body["indicators"].keys()) == {
        "education", "healthcare", "transportation", "public_space", "accessibility",
    }


def test_score_range(client):
    body = client.get("/api/v1/analytics/ufs?city_id=1").json()
    assert 0 <= body["overall_score"] <= 100
    for v in body["indicators"].values():
        if v is not None:
            assert 0 <= v <= 100


def test_category_boundaries():
    assert ufs_service._category(100) == "Excellent"
    assert ufs_service._category(80) == "Excellent"
    assert ufs_service._category(79) == "Good"
    assert ufs_service._category(60) == "Good"
    assert ufs_service._category(59) == "Fair"
    assert ufs_service._category(40) == "Fair"
    assert ufs_service._category(39) == "Poor"
    assert ufs_service._category(20) == "Poor"
    assert ufs_service._category(19) == "Critical"
    assert ufs_service._category(0) == "Critical"


def test_benchmark_refresh_creates_five_indicators(db_session):
    ufs_service.refresh_benchmarks(db_session)
    rows = db_session.query(UfsIndicator).order_by(UfsIndicator.indicator).all()
    indicators = {r.indicator for r in rows}
    assert indicators == {
        "education", "healthcare", "transportation", "public_space", "accessibility",
    }
    for r in rows:
        assert r.weight == 0.2
        if r.indicator == "accessibility":
            assert r.reference_km == 1.0
        elif r.indicator == "transportation":
            assert r.benchmark_density is None  # seed has no BusStop
        else:
            assert r.benchmark_density is not None


def test_city_aggregation_is_mean_of_districts(client):
    body = client.get("/api/v1/analytics/ufs?city_id=1").json()
    district_scores = [d["overall_score"] for d in body["per_district"]]
    assert len(district_scores) == 3
    expected = round(sum(district_scores) / len(district_scores), 1)
    assert body["overall_score"] == expected


def test_zero_facility_district(client, db_session):
    db_session.execute(
        text(
            "INSERT INTO district (code, name, city_id, geom) VALUES "
            "('119999', 'Empty District', 1, "
            "'SRID=4326;MULTIPOLYGON(((140.0 -9.0, 140.1 -9.0, 140.1 -9.1, 140.0 -9.1, 140.0 -9.0)))')"
        )
    )
    db_session.commit()
    district_id = db_session.execute(
        text("SELECT id FROM district WHERE code = '119999'")
    ).scalar()
    body = client.get(f"/api/v1/analytics/ufs?district_id={district_id}").json()
    assert body["overall_score"] == 0
    assert body["total_facilities"] == 0
    assert body["status"] == "No Data"
    assert body["category"] == "Critical"


def test_invalid_city_404(client):
    resp = client.get("/api/v1/analytics/ufs?city_id=999999")
    assert resp.status_code == 404


def test_invalid_district_404(client):
    resp = client.get("/api/v1/analytics/ufs?district_id=999999")
    assert resp.status_code == 404


def test_missing_scope_422(client):
    resp = client.get("/api/v1/analytics/ufs")
    assert resp.status_code == 422


def test_cache_ufs_scores(client, db_session):
    client.get("/api/v1/analytics/ufs?city_id=1")
    row = (
        db_session.query(UfsScore)
        .filter(UfsScore.scope_type == "city", UfsScore.scope_id == 1)
        .first()
    )
    assert row is not None
    assert row.methodology == "v0-provision"
    assert row.overall_score == client.get("/api/v1/analytics/ufs?city_id=1").json()["overall_score"]


def test_breakdown_matches_database(client, db_session):
    body = client.get("/api/v1/analytics/ufs?city_id=1").json()
    db_counts = dict(
        db_session.execute(
            text(
                "SELECT facility_type, count(*) FROM facility "
                "WHERE city_id = 1 GROUP BY facility_type"
            )
        ).all()
    )
    for ftype, cnt in db_counts.items():
        assert body["breakdown"].get(ftype, 0) == cnt
    assert body["total_facilities"] == sum(db_counts.values())


def test_backward_compat_fields(client):
    body = client.get("/api/v1/analytics/ufs?city_id=1").json()
    for key in ["overall_score", "total_facilities", "breakdown", "status"]:
        assert key in body
    for key in [
        "category", "indicators", "methodology", "district_count", "per_district", "computed_at",
    ]:
        assert key in body
    assert body["methodology"] == "v0-provision"


def test_district_ufs_endpoint(client):
    body = client.get("/api/v1/analytics/ufs?district_id=1").json()
    assert body["scope_type"] == "district"
    assert body["scope_id"] == 1
    assert 0 <= body["overall_score"] <= 100
