import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.ai.openrouter import OpenRouterProvider
from app.services import ufs as ufs_service

logger = logging.getLogger(__name__)

METHODOLOGY = "rule-v1"
DEFICIT_THRESHOLD = 40.0
MAX_LLM_PRIORITY_ITEMS = 10

NO_DATA_SUMMARY = "Insufficient facility data to generate a reliable priority recommendation."

INDICATOR_ACTIONS = {
    "education": "Prioritize improving education facility access.",
    "healthcare": "Prioritize improving healthcare facility access.",
    "transportation": "Prioritize improving public transportation accessibility.",
    "public_space": "Prioritize improving access to public spaces.",
    "accessibility": "Prioritize improving connectivity and facility accessibility.",
}

INDICATOR_LABELS = {
    "education": "Pendidikan",
    "healthcare": "Kesehatan",
    "transportation": "Transportasi",
    "public_space": "Ruang Terbuka",
    "accessibility": "Aksesibilitas",
}


def _district_deficits(district: dict[str, Any]) -> list[dict[str, Any]]:
    indicators = district.get("indicators") or {}
    deficits = []
    for key, action in INDICATOR_ACTIONS.items():
        value = indicators.get(key)
        if value is not None and value < DEFICIT_THRESHOLD:
            deficits.append({"indicator": key, "score": value, "action": action})
    return deficits


def _weakest_score(indicators: dict[str, Any]) -> float:
    present = [v for v in indicators.values() if v is not None]
    return min(present) if present else 0.0


def rank_priority(city_ufs: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = []
    for district in city_ufs.get("per_district") or []:
        deficits = _district_deficits(district)
        ranked.append(
            {
                "district_id": district["district_id"],
                "name": district.get("name"),
                "overall_score": district["overall_score"],
                "category": district["category"],
                "deficit_count": len(deficits),
                "weakest_score": _weakest_score(district.get("indicators") or {}),
                "deficits": deficits,
                "recommended_actions": [d["action"] for d in deficits],
            }
        )
    ranked.sort(
        key=lambda r: (
            r["overall_score"],
            -r["deficit_count"],
            r["weakest_score"],
        )
    )
    for idx, item in enumerate(ranked, start=1):
        item["rank"] = idx
    return ranked


def _build_summary(city_ufs: dict[str, Any], ranked: list[dict[str, Any]]) -> str:
    total = city_ufs.get("district_count", len(ranked))
    critical = sum(1 for r in ranked if r["category"] in ("Poor", "Critical"))
    counter: Counter[str] = Counter()
    for item in ranked:
        for deficit in item["deficits"]:
            counter[deficit["indicator"]] += 1
    parts = [f"{critical} dari {total} kecamatan masuk kategori Poor/Critical."]
    if counter:
        top = ", ".join(
            f"{INDICATOR_LABELS.get(k, k)} ({v})"
            for k, v in counter.most_common(3)
        )
        parts.append(f"Defisit terbanyak: {top}.")
    return " ".join(parts)


def _build_prompt(city_ufs: dict[str, Any], ranked: list[dict[str, Any]], summary: str) -> str:
    items = "\n".join(
        f"- Rank {r['rank']}: {r['name']} (UFS {r['overall_score']}, {r['category']}), "
        f"defisit: {', '.join(d['indicator'] for d in r['deficits']) or 'tidak ada'}"
        for r in ranked[:MAX_LLM_PRIORITY_ITEMS]
    )
    return (
        "Kamu adalah analis perencanaan kota untuk platform Invisible City. "
        f"Kota: {city_ufs.get('name')}. UFS kota: {city_ufs.get('overall_score')} "
        f"({city_ufs.get('category')}). Ringkasan: {summary}\n"
        "Prioritas kecamatan (rule engine):\n"
        f"{items}\n"
        "Catatan metodologi: UFS v0 berbasis penyediaan (provision-based), BUKAN per-capita. "
        "Skor aksesibilitas adalah proxy jarak Euclidean 1km, tanpa data jaringan jalan/populasi. "
        "JANGAN mengklaim jumlah penduduk, waktu tempuh nyata, atau data yang tidak ada. "
        "Buat narasi rekomendasi kebijakan ringkas dalam Bahasa Indonesia (3-5 kalimat), "
        "sebutkan kecamatan prioritas dan aksi konkret."
    )


def generate_recommendations(
    db: Session, city_id: int, llm: bool = False, provider: Any = None
) -> dict[str, Any]:
    city_ufs = ufs_service.get_city_ufs(db, city_id)

    if city_ufs.get("status") == "No Data":
        return {
            "city_id": city_id,
            "city_name": city_ufs.get("name"),
            "methodology": METHODOLOGY,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": NO_DATA_SUMMARY,
            "status": "No Data",
            "recommendation_available": False,
            "priority": [],
            "narrative": None,
        }

    ranked = rank_priority(city_ufs)
    summary = _build_summary(city_ufs, ranked)

    narrative = None
    if llm:
        if provider is None:
            provider = OpenRouterProvider()
        prompt = _build_prompt(city_ufs, ranked, summary)
        narrative = provider.generate_narrative(prompt)

    return {
        "city_id": city_id,
        "city_name": city_ufs.get("name"),
        "methodology": METHODOLOGY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "status": "Data Available",
        "recommendation_available": True,
        "priority": ranked,
        "narrative": narrative,
    }
