from app.ai.openrouter import OpenRouterProvider
from app.services import recommendation as rec


def test_rule_engine_default_no_llm(client):
    body = client.get("/api/v1/analytics/recommendations?city_id=1").json()
    assert body["methodology"] == "rule-v1"
    assert body["city_id"] == 1
    assert body["city_name"] == "City A"
    assert body["narrative"] is None
    assert body["recommendation_available"] is True
    assert len(body["priority"]) == 3
    for item in body["priority"]:
        assert item["rank"] >= 1
        assert 0 <= len(item["deficits"]) <= 5
        assert item["deficit_count"] == len(item["deficits"])


def test_measured_low_score_keeps_recommendation(client):
    body = client.get("/api/v1/analytics/recommendations?city_id=1").json()
    assert body["recommendation_available"] is True
    assert len(body["priority"]) > 0

    any_action = any(
        item["recommended_actions"]
        for item in body["priority"]
    )
    assert any_action, "measured low-score districts must still produce actions"


def test_no_data_city_no_prescriptive_actions(client):
    body = client.get("/api/v1/analytics/recommendations?city_id=2").json()
    assert body["status"] == "No Data"
    assert body["recommendation_available"] is False
    assert body["priority"] == []
    assert body["narrative"] is None
    assert body["summary"] == rec.NO_DATA_SUMMARY
    for item in body["priority"]:
        assert item["deficits"] == []
        assert item["recommended_actions"] == []


def test_action_wording_non_prescriptive():
    expected = {
        "education": "Prioritize improving education facility access.",
        "healthcare": "Prioritize improving healthcare facility access.",
        "transportation": "Prioritize improving public transportation accessibility.",
        "public_space": "Prioritize improving access to public spaces.",
        "accessibility": "Prioritize improving connectivity and facility accessibility.",
    }
    assert rec.INDICATOR_ACTIONS == expected

    forbidden = ("tambah", "bangun", "bangunan")
    for action in rec.INDICATOR_ACTIONS.values():
        assert action.lower().startswith("prioritize ")
        for word in forbidden:
            assert word not in action.lower()


def test_priority_sorted_by_overall_ascending(client):
    body = client.get("/api/v1/analytics/recommendations?city_id=1").json()
    scores = [item["overall_score"] for item in body["priority"]]
    assert scores == sorted(scores)


def test_rank_priority_lexicographic():
    city_ufs = {
        "district_count": 4,
        "per_district": [
            {
                "district_id": 3,
                "name": "C",
                "overall_score": 30.0,
                "category": "Poor",
                "indicators": {k: 10.0 for k in rec.INDICATOR_ACTIONS},
            },
            {
                "district_id": 1,
                "name": "A",
                "overall_score": 20.0,
                "category": "Poor",
                "indicators": {
                    "education": 3.0,
                    "healthcare": 3.0,
                    "transportation": 60.0,
                    "public_space": 60.0,
                    "accessibility": 60.0,
                },
            },
            {
                "district_id": 2,
                "name": "B",
                "overall_score": 20.0,
                "category": "Poor",
                "indicators": {
                    "education": 8.0,
                    "healthcare": 50.0,
                    "transportation": 50.0,
                    "public_space": 50.0,
                    "accessibility": 8.0,
                },
            },
            {
                "district_id": 4,
                "name": "D",
                "overall_score": 20.0,
                "category": "Poor",
                "indicators": {
                    "education": 90.0,
                    "healthcare": 90.0,
                    "transportation": 10.0,
                    "public_space": 90.0,
                    "accessibility": 90.0,
                },
            },
        ],
    }
    ranked = rec.rank_priority(city_ufs)
    ids = [item["district_id"] for item in ranked]
    assert ids == [1, 2, 4, 3]
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2


def test_deficit_threshold_boundary():
    district = {
        "indicators": {
            "education": 40.0,
            "healthcare": 40.0,
            "transportation": 40.0,
            "public_space": 40.0,
            "accessibility": 40.0,
        }
    }
    assert rec._district_deficits(district) == []
    district["indicators"]["education"] = 39.9
    deficits = rec._district_deficits(district)
    assert [d["indicator"] for d in deficits] == ["education"]


def test_action_mapping():
    district = {
        "indicators": {
            "education": 10.0,
            "healthcare": 50.0,
            "transportation": 55.0,
            "public_space": 60.0,
            "accessibility": 0.0,
        }
    }
    deficits = rec._district_deficits(district)
    indicators = {d["indicator"] for d in deficits}
    assert indicators == {"education", "accessibility"}
    actions = {d["action"] for d in deficits}
    assert rec.INDICATOR_ACTIONS["education"] in actions
    assert rec.INDICATOR_ACTIONS["accessibility"] in actions


def test_invalid_city_404(client):
    resp = client.get("/api/v1/analytics/recommendations?city_id=999999")
    assert resp.status_code == 404


def test_missing_city_422(client):
    resp = client.get("/api/v1/analytics/recommendations")
    assert resp.status_code == 422


def test_llm_fallback_null_without_provider(client, monkeypatch):
    def fake_generate(self, prompt, **kwargs):
        return None

    monkeypatch.setattr(OpenRouterProvider, "generate_narrative", fake_generate)
    body = client.get("/api/v1/analytics/recommendations?city_id=1&llm=true").json()
    assert body["narrative"] is None


def test_llm_narrative_present(client, monkeypatch):
    def fake_generate(self, prompt, **kwargs):
        return "Narasi rekomendasi test"

    monkeypatch.setattr(OpenRouterProvider, "generate_narrative", fake_generate)
    body = client.get("/api/v1/analytics/recommendations?city_id=1&llm=true").json()
    assert body["narrative"] == "Narasi rekomendasi test"
