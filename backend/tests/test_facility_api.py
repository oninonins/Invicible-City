import pytest

VALID = {
    "name": "New School",
    "facility_type": "School",
    "lat": -6.2,
    "lng": 106.8,
    "source": "OSM",
    "external_id": "new1",
    "city_id": 1,
    "district_id": 1,
}


def _post(client, payload):
    return client.post("/api/v1/facilities/", json=payload)


def test_list_valid_pagination(client):
    resp = client.get("/api/v1/facilities/?limit=5")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


def test_list_limit_max_500(client):
    resp = client.get("/api/v1/facilities/?limit=500")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


@pytest.mark.parametrize("params", ["limit=-5", "skip=-5", "limit=0", "limit=501"])
def test_invalid_pagination_returns_422(client, params):
    resp = client.get(f"/api/v1/facilities/?{params}")
    assert resp.status_code == 422


def test_deterministic_ordering(client):
    ids = [f["id"] for f in client.get("/api/v1/facilities/?limit=100").json()]
    assert ids == sorted(ids)
    assert ids == [1, 2, 3, 4, 5]


def test_city_filter(client):
    resp = client.get("/api/v1/facilities/?city_id=1")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 4
    assert all(f["city_id"] == 1 for f in body)


def test_district_filter(client):
    resp = client.get("/api/v1/facilities/?district_id=1")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert all(f["district_id"] == 1 for f in body)


def test_facility_type_filter(client):
    resp = client.get("/api/v1/facilities/?facility_type=School")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert all(f["facility_type"] == "School" for f in body)


def test_post_valid_facility(client):
    resp = _post(client, VALID)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New School"
    assert body["facility_type"] == "School"
    assert body["lat"] == -6.2
    assert body["lng"] == 106.8
    assert body["city_id"] == 1
    assert body["district_id"] == 1


def test_post_empty_name_rejected(client):
    assert _post(client, dict(VALID, name="")).status_code == 422


def test_post_missing_name_rejected(client):
    payload = {k: v for k, v in VALID.items() if k != "name"}
    assert _post(client, payload).status_code == 422


def test_post_empty_facility_type_rejected(client):
    assert _post(client, dict(VALID, facility_type="")).status_code == 422


@pytest.mark.parametrize("lat", [91, -91, 999])
def test_post_invalid_lat_rejected(client, lat):
    assert _post(client, dict(VALID, lat=lat)).status_code == 422


@pytest.mark.parametrize("lng", [181, -181, 999])
def test_post_invalid_lng_rejected(client, lng):
    assert _post(client, dict(VALID, lng=lng)).status_code == 422


def test_post_invalid_city_fk_rejected(client):
    assert _post(client, dict(VALID, city_id=999999)).status_code == 404


def test_post_invalid_district_fk_rejected(client):
    assert _post(client, dict(VALID, district_id=999999)).status_code == 404
