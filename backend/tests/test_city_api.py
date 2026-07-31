def test_cities_count(client):
    resp = client.get("/api/v1/cities/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_cities_contains_id_and_name(client):
    cities = client.get("/api/v1/cities/").json()
    for city in cities:
        assert "id" in city
        assert "name" in city
    names = {city["name"] for city in cities}
    assert names == {"City A", "City B"}


def test_cities_do_not_return_geometry(client):
    cities = client.get("/api/v1/cities/").json()
    for city in cities:
        assert "geom" not in city
        assert "geometry" not in city


def test_cities_deterministic_order(client):
    ids = [city["id"] for city in client.get("/api/v1/cities/").json()]
    assert ids == sorted(ids)
    assert ids == [1, 2]


def test_city_boundary_valid(client):
    resp = client.get("/api/v1/cities/1/boundary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1
    assert body["features"][0]["geometry"]["type"] == "MultiPolygon"
    assert body["features"][0]["properties"]["city_id"] == 1


def test_city_boundary_invalid_returns_404(client):
    resp = client.get("/api/v1/cities/999999/boundary")
    assert resp.status_code == 404


def test_city_districts_valid(client):
    resp = client.get("/api/v1/cities/1/districts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 3


def test_city_districts_invalid_returns_404(client):
    resp = client.get("/api/v1/cities/999999/districts")
    assert resp.status_code == 404


def test_city_districts_empty_returns_200(client):
    resp = client.get("/api/v1/cities/2/districts")
    assert resp.status_code == 200
    assert resp.json()["features"] == []
