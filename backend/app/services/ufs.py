import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.models.ufs import UfsIndicator, UfsScore

logger = logging.getLogger(__name__)

INDICATOR_KEYS = ["education", "healthcare", "transportation", "public_space", "accessibility"]
INDICATOR_TYPES = {
    "education": ["School"],
    "healthcare": ["Hospital", "Clinic"],
    "transportation": ["BusStop"],
    "public_space": ["Park"],
}
ACCESSIBILITY_TYPES = ["School", "Hospital", "Clinic", "BusStop", "Park"]
DEFAULT_WEIGHT = 0.2
REFERENCE_KM = 1.0
METHODOLOGY = "v0-provision"

CATEGORIES = [
    (80, "Excellent"),
    (60, "Good"),
    (40, "Fair"),
    (20, "Poor"),
    (0, "Critical"),
]


def _category(score: float) -> str:
    for threshold, label in CATEGORIES:
        if score >= threshold:
            return label
    return "Critical"


def _legacy_status(category: str) -> str:
    if category in ("Excellent", "Good"):
        return "Good"
    if category == "Fair":
        return "Fair"
    return "Poor"


def _median(values: list[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 0:
        return (ordered[mid - 1] + ordered[mid]) / 2
    return ordered[mid]


def refresh_benchmarks(db: Session) -> None:
    areas = dict(
        db.execute(
            text(
                """
                SELECT d.id, ST_Area(ST_Transform(d.geom, 32749)) / 1e6 AS area_km2
                FROM district d
                WHERE d.geom IS NOT NULL
                """
            )
        ).all()
    )

    counts = db.execute(
        text(
            """
            SELECT f.district_id, f.facility_type, count(*)::int AS cnt
            FROM facility f
            WHERE f.district_id IS NOT NULL
            GROUP BY f.district_id, f.facility_type
            """
        )
    ).all()

    densities: dict[str, list[float]] = {key: [] for key in INDICATOR_KEYS}
    for district_id, ftype, cnt in counts:
        area = areas.get(district_id)
        if not area:
            continue
        for key, types in INDICATOR_TYPES.items():
            if ftype in types:
                densities[key].append(cnt / area)

    now = datetime.now(timezone.utc)
    for key in INDICATOR_KEYS:
        if key == "accessibility":
            benchmark = None
            ref_km = REFERENCE_KM
            note = "1km reference distance, Euclidean proxy"
        else:
            benchmark = _median(densities[key])
            ref_km = None
            note = (
                f"median density over districts with >=1 {key} facility"
                if benchmark is not None
                else "no data"
            )

        row = db.query(UfsIndicator).filter(UfsIndicator.indicator == key).first()
        if row is None:
            row = UfsIndicator(indicator=key)
            db.add(row)
        row.weight = DEFAULT_WEIGHT
        row.benchmark_density = benchmark
        row.reference_km = ref_km
        row.benchmark_note = note
        row.updated_at = now
    db.commit()


def _load_indicators(db: Session) -> dict[str, UfsIndicator]:
    return {row.indicator: row for row in db.query(UfsIndicator).all()}


def _district_area_km2(db: Session, district_id: int) -> Optional[float]:
    return db.execute(
        text("SELECT ST_Area(ST_Transform(geom, 32749)) / 1e6 FROM district WHERE id = :id"),
        {"id": district_id},
    ).scalar()


def _density_score(
    db: Session, district_id: int, types: list[str], benchmark: Optional[float]
) -> Optional[float]:
    if benchmark is None:
        return None
    cnt = (
        db.query(func.count(Facility.id))
        .filter(Facility.district_id == district_id, Facility.facility_type.in_(types))
        .scalar()
    )
    area = _district_area_km2(db, district_id)
    if not area:
        return None
    actual = cnt / area
    return round(min(actual / benchmark * 100, 100), 1)


def _accessibility_scores(db: Session, district_id: int, reference_km: float) -> Optional[float]:
    scores = []
    for ftype in ACCESSIBILITY_TYPES:
        dist_m = db.execute(
            text(
                """
                SELECT ST_Distance(f.geom::geography, ST_PointOnSurface(d.geom)::geography)
                FROM facility f, district d
                WHERE f.facility_type = :ftype AND d.id = :did
                ORDER BY f.geom::geography <-> ST_PointOnSurface(d.geom)::geography
                LIMIT 1
                """
            ),
            {"ftype": ftype, "did": district_id},
        ).scalar()
        if dist_m is None:
            scores.append(0.0)
        else:
            dist_km = dist_m / 1000.0
            scores.append(round(max(0.0, 100.0 - dist_km / reference_km * 100.0), 1))
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def _rebalanced_overall(scores: dict[str, Optional[float]]) -> tuple[float, list[str]]:
    present = [k for k, v in scores.items() if v is not None]
    if not present:
        return 0.0, []
    total_weight = DEFAULT_WEIGHT * len(present)
    weighted = sum(DEFAULT_WEIGHT * scores[k] for k in present)
    return round(weighted / total_weight, 1), present


def _breakdown(db: Session, district_id: int) -> dict[str, int]:
    rows = db.execute(
        text(
            """
            SELECT facility_type, count(*)::int AS cnt
            FROM facility
            WHERE district_id = :did
            GROUP BY facility_type
            """
        ),
        {"did": district_id},
    ).all()
    return {ftype: cnt for ftype, cnt in rows}


def _upsert_score(db: Session, data: dict[str, Any]) -> UfsScore:
    row = (
        db.query(UfsScore)
        .filter(UfsScore.scope_type == data["scope_type"], UfsScore.scope_id == data["scope_id"])
        .first()
    )
    if row is None:
        row = UfsScore(scope_type=data["scope_type"], scope_id=data["scope_id"])
        db.add(row)
    row.overall_score = data["overall_score"]
    row.category = data["category"]
    row.indicators = data["indicators"]
    row.total_facilities = data["total_facilities"]
    row.breakdown = data["breakdown"]
    row.district_count = data["district_count"]
    row.methodology = METHODOLOGY
    row.computed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def compute_district_ufs(db: Session, district_id: int) -> dict[str, Any]:
    indicators = _load_indicators(db)
    scores: dict[str, Optional[float]] = {}
    for key in INDICATOR_KEYS:
        row = indicators.get(key)
        if key == "accessibility":
            ref_km = row.reference_km if row and row.reference_km else REFERENCE_KM
            scores[key] = _accessibility_scores(db, district_id, ref_km)
        else:
            benchmark = row.benchmark_density if row else None
            scores[key] = _density_score(db, district_id, INDICATOR_TYPES[key], benchmark)

    overall, _present = _rebalanced_overall(scores)
    breakdown = _breakdown(db, district_id)
    total = sum(breakdown.values())
    data = {
        "scope_type": "district",
        "scope_id": district_id,
        "overall_score": overall,
        "category": _category(overall),
        "indicators": scores,
        "total_facilities": total,
        "breakdown": breakdown,
        "district_count": 1,
        "methodology": METHODOLOGY,
    }
    row = _upsert_score(db, data)
    return _build_response(db, row)


def compute_city_ufs(db: Session, city_id: int) -> dict[str, Any]:
    districts = db.execute(
        text("SELECT id FROM district WHERE city_id = :cid ORDER BY id"), {"cid": city_id}
    ).scalars().all()

    if not districts:
        empty = {k: None for k in INDICATOR_KEYS}
        data = {
            "scope_type": "city",
            "scope_id": city_id,
            "overall_score": 0.0,
            "category": "Critical",
            "indicators": empty,
            "total_facilities": 0,
            "breakdown": {},
            "district_count": 0,
            "methodology": METHODOLOGY,
        }
        row = _upsert_score(db, data)
        return _build_response(db, row)

    per_district = []
    for did in districts:
        per_district.append(compute_district_ufs(db, did))

    overall = round(sum(d["overall_score"] for d in per_district) / len(per_district), 1)
    indicators: dict[str, Optional[float]] = {}
    for key in INDICATOR_KEYS:
        vals = [d["indicators"][key] for d in per_district if d["indicators"].get(key) is not None]
        indicators[key] = round(sum(vals) / len(vals), 1) if vals else None

    breakdown: dict[str, int] = {}
    for d in per_district:
        for ftype, cnt in d["breakdown"].items():
            breakdown[ftype] = breakdown.get(ftype, 0) + cnt

    data = {
        "scope_type": "city",
        "scope_id": city_id,
        "overall_score": overall,
        "category": _category(overall),
        "indicators": indicators,
        "total_facilities": sum(breakdown.values()),
        "breakdown": breakdown,
        "district_count": len(per_district),
        "methodology": METHODOLOGY,
    }
    row = _upsert_score(db, data)
    return _build_response(db, row)


def _build_response(db: Session, row: UfsScore) -> dict[str, Any]:
    indicators = row.indicators or {k: None for k in INDICATOR_KEYS}
    breakdown = row.breakdown or {}
    score = row.overall_score or 0.0

    per_district: list[dict[str, Any]] = []
    if row.scope_type == "city":
        district_rows = db.execute(
            text(
                """
                SELECT d.id AS district_id, d.name, s.overall_score, s.category,
                       s.indicators, s.total_facilities, s.breakdown
                FROM ufs_scores s
                JOIN district d ON d.id = s.scope_id
                WHERE s.scope_type = 'district' AND d.city_id = :cid
                ORDER BY d.id
                """
            ),
            {"cid": row.scope_id},
        ).all()
        per_district = [
            {
                "district_id": r.district_id,
                "name": r.name,
                "overall_score": r.overall_score,
                "category": r.category,
                "indicators": r.indicators,
                "total_facilities": r.total_facilities,
                "breakdown": r.breakdown,
            }
            for r in district_rows
        ]
    else:
        name = db.execute(
            text("SELECT name FROM district WHERE id = :id"), {"id": row.scope_id}
        ).scalar()
        per_district = [
            {
                "district_id": row.scope_id,
                "name": name,
                "overall_score": row.overall_score,
                "category": row.category,
                "indicators": indicators,
                "total_facilities": row.total_facilities,
                "breakdown": breakdown,
            }
        ]

    status = "No Data" if row.total_facilities == 0 else _legacy_status(row.category)
    name = db.execute(
        text(
            "SELECT name FROM {} WHERE id = :id".format(
                "city" if row.scope_type == "city" else "district"
            )
        ),
        {"id": row.scope_id},
    ).scalar()
    return {
        "scope_type": row.scope_type,
        "scope_id": row.scope_id,
        "name": name,
        "overall_score": round(score, 1),
        "total_facilities": row.total_facilities,
        "breakdown": breakdown,
        "status": status,
        "category": row.category,
        "indicators": indicators,
        "methodology": row.methodology or METHODOLOGY,
        "district_count": row.district_count,
        "per_district": per_district,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
    }


def get_district_ufs(db: Session, district_id: int) -> dict[str, Any]:
    row = (
        db.query(UfsScore)
        .filter(UfsScore.scope_type == "district", UfsScore.scope_id == district_id)
        .first()
    )
    if row:
        return _build_response(db, row)
    return compute_district_ufs(db, district_id)


def get_city_ufs(db: Session, city_id: int) -> dict[str, Any]:
    row = (
        db.query(UfsScore)
        .filter(UfsScore.scope_type == "city", UfsScore.scope_id == city_id)
        .first()
    )
    if row:
        return _build_response(db, row)
    return compute_city_ufs(db, city_id)
