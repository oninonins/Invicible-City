import json
import logging
import os
import time
from threading import Lock
from typing import Optional

import geopandas as gpd
import psycopg2
from geoalchemy2.shape import from_shape
from psycopg2.extras import execute_values
from shapely import wkb
from shapely.geometry import MultiPolygon, Polygon
from shapely.validation import make_valid
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.etl.providers import DatasetProvider, LocalFileProvider
from app.models.etl import DatasetMetadata
from app.models.spatial import Province, City, District, Village

logger = logging.getLogger(__name__)

_provider_lock = Lock()
_default_provider = None

_ALIAS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "mappings",
    "city_aliases.json",
)
_city_aliases = None


def _load_city_aliases() -> dict[str, str]:
    global _city_aliases
    if _city_aliases is None:
        if os.path.exists(_ALIAS_FILE):
            with open(_ALIAS_FILE, encoding="utf-8") as f:
                _city_aliases = json.load(f)
            logger.info(f"Loaded {len(_city_aliases)} city aliases from {_ALIAS_FILE}")
        else:
            _city_aliases = {}
            logger.warning(f"City alias file not found: {_ALIAS_FILE}")
    return _city_aliases


LAYERS = [
    {
        "id": 0,
        "name": "provinsi",
        "filename": "provinsi.geojson",
        "model": Province,
        "code_field": None,
        "name_field": "namobj",
        "parent_field": None,
        "has_geometry": False,
    },
    {
        "id": 2,
        "name": "kabupaten_kota",
        "filename": "kabupaten_kota.geojson",
        "model": City,
        "code_field": "wadmkk",
        "name_field": "namobj",
        "parent_field": "wadmpr",
        "parent_model": Province,
        "has_geometry": True,
    },
    {
        "id": 3,
        "name": "kecamatan",
        "filename": "district/Kecamatan.shp",
        "model": District,
        "code_field": "code",
        "name_field": "name",
        "parent_field": "parent_name",
        "parent_model": City,
        "has_geometry": True,
    },
    {
        "id": 4,
        "name": "desa",
        "filename": "desa.geojson",
        "model": Village,
        "code_field": "kdpumdes",
        "name_field": "namobj",
        "parent_field": "kdpumkec",
        "parent_model": District,
        "has_geometry": True,
        "extra_fields": {
            "tipadm": "village_type",
            "kdbbps": "bps_code",
        },
    },
]


def set_default_provider(provider: DatasetProvider):
    global _default_provider
    with _provider_lock:
        _default_provider = provider


def get_default_provider() -> DatasetProvider:
    global _default_provider
    with _provider_lock:
        if _default_provider is None:
            _default_provider = LocalFileProvider()
        return _default_provider


def ensure_multipolygon(geom):
    if geom is None:
        return None
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    return None


def validate_geometry(geom):
    if geom is None:
        return None
    if not geom.is_valid:
        try:
            geom = make_valid(geom)
        except Exception:
            return None
    return ensure_multipolygon(geom)


def extract_field(row: dict, field: str) -> Optional[str]:
    val = row.get(field)
    if val is None or val == "" or val == "None":
        return None
    return str(val).strip()


def _attr(row) -> dict:
    return getattr(row, "attributes", row.to_dict())


def load_provinces(db: Session, gdf: gpd.GeoDataFrame, layer_cfg: dict) -> int:
    count = 0
    name_field = layer_cfg["name_field"]

    for _, row in gdf.iterrows():
        name = extract_field(row, name_field)
        if not name:
            continue

        existing = db.query(Province).filter(Province.name == name).first()
        if existing:
            existing.name = name
        else:
            db.add(Province(name=name))

        count += 1

    db.commit()
    logger.info(f"Upserted {count} provinces")
    return count


def load_cities(db: Session, gdf: gpd.GeoDataFrame, layer_cfg: dict) -> int:
    code_field = layer_cfg["code_field"]
    name_field = layer_cfg["name_field"]
    parent_field = layer_cfg["parent_field"]

    # === Phase 1: Extract + Validate + Convert geometry to WKB ===
    t0 = time.time()
    prepared = []
    parent_names = set()
    for _, row in gdf.iterrows():
        code = extract_field(row, code_field) if code_field else None
        name = extract_field(row, name_field)
        parent_name = extract_field(row, parent_field) if parent_field else None
        if not name or not code:
            continue
        geom = validate_geometry(row.geometry)
        geom_wkb = wkb.dumps(geom) if geom is not None else None
        prepared.append((code, name, parent_name, geom_wkb))
        if parent_name:
            parent_names.add(parent_name)
    t1 = time.time()
    logger.info(
        f"[timing] cities extract+validate+convert: "
        f"{len(prepared)} rows in {t1-t0:.2f}s"
    )

    if not prepared:
        return 0

    # === Phase 2: Resolve parent FKs in bulk ===
    if parent_names:
        existing = db.query(Province).filter(
            Province.name.in_(parent_names)
        ).all()
        parent_map = {p.name: p.id for p in existing}
        missing = parent_names - set(parent_map.keys())
        for name in missing:
            p = Province(name=name)
            db.add(p)
            db.flush()
            parent_map[name] = p.id
    else:
        parent_map = {}
    t2 = time.time()
    logger.info(
        f"[timing] cities parent FK resolution: "
        f"{t2-t1:.2f}s ({len(parent_map)} parents)"
    )

    # === Phase 3: Batch UPSERT via execute_values ===
    dedup = {}
    for code, name, parent_name, geom_wkb in prepared:
        province_id = parent_map.get(parent_name) if parent_name else None
        dedup[code] = (code, name, province_id, geom_wkb)
    value_tuples = list(dedup.values())
    if len(value_tuples) < len(prepared):
        logger.warning(
            f"Cities: deduplicated {len(prepared) - len(value_tuples)} "
            f"rows by code"
        )

    raw_conn = db.connection().connection
    insert_sql = """
        INSERT INTO city (code, name, province_id, geom)
        VALUES %s
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            province_id = EXCLUDED.province_id,
            geom = COALESCE(ST_GeomFromWKB(EXCLUDED.geom, 4326), city.geom)
    """

    t3 = time.time()
    with raw_conn.cursor() as cur:
        execute_values(cur, insert_sql, value_tuples, page_size=200)
    t4 = time.time()
    logger.info(
        f"[timing] cities batch insert: {t4-t3:.2f}s "
        f"({len(value_tuples)} rows, page_size=200)"
    )

    db.commit()
    t5 = time.time()
    logger.info(f"[timing] cities commit: {t5-t4:.2f}s")

    count = len(prepared)
    logger.info(f"Upserted {count} cities")
    return count


def load_districts(db: Session, gdf: gpd.GeoDataFrame, layer_cfg: dict) -> int:
    code_field = layer_cfg["code_field"]
    name_field = layer_cfg["name_field"]
    parent_field = layer_cfg["parent_field"]

    # === Phase 1: Extract + Validate + Convert ===
    aliases = _load_city_aliases()
    t0 = time.time()
    prepared = []
    parent_codes = set()
    for _, row in gdf.iterrows():
        code = extract_field(row, code_field) if code_field else None
        name = extract_field(row, name_field)
        parent_code = extract_field(row, parent_field) if parent_field else None
        if not name or not code:
            continue
        if parent_code:
            resolved = aliases.get(parent_code, parent_code)
            if resolved != parent_code:
                logger.debug(
                    f"Resolved city alias: '{parent_code}' -> '{resolved}'"
                )
            parent_code = resolved
        geom = validate_geometry(row.geometry)
        geom_wkb = wkb.dumps(geom) if geom is not None else None
        prepared.append((code, name, parent_code, geom_wkb))
        if parent_code:
            parent_codes.add(parent_code)
    t1 = time.time()
    logger.info(
        f"[timing] districts extract+validate+convert: "
        f"{len(prepared)} rows in {t1-t0:.2f}s"
    )

    if not prepared:
        return 0

    # === Phase 2: Resolve parent FKs ===
    if parent_codes:
        existing = db.query(City).filter(
            City.code.in_(parent_codes)
        ).all()
        parent_map = {c.code: c.id for c in existing}
        missing = parent_codes - set(parent_map.keys())
        if missing:
            new_unresolved = {m for m in missing if m not in aliases.values()}
            if new_unresolved:
                logger.warning(
                    f"Districts: {len(new_unresolved)} unresolved city names "
                    f"(not in DB nor alias map): {sorted(new_unresolved)[:5]}..."
                )
            alias_resolved = {m for m in missing if m in aliases.values()}
            if alias_resolved:
                logger.info(
                    f"Districts: {len(alias_resolved)} alias-resolved names "
                    f"still unmatched — alias may need updating: "
                    f"{sorted(alias_resolved)[:3]}..."
                )
    else:
        parent_map = {}
    t2 = time.time()
    logger.info(
        f"[timing] districts parent FK resolution: "
        f"{t2-t1:.2f}s ({len(parent_map)} parents)"
    )

    # === Phase 3: Skip orphans ===
    orphan_count = 0
    orphan_samples = []
    filtered = []
    for code, name, parent_code, geom_wkb in prepared:
        if not parent_code:
            orphan_count += 1
            if len(orphan_samples) < 5:
                orphan_samples.append(f"code={code} (no parent ref)")
            continue
        city_id = parent_map.get(parent_code)
        if city_id is None:
            orphan_count += 1
            if len(orphan_samples) < 5:
                orphan_samples.append(f"code={code} parent={parent_code}")
            continue
        filtered.append((code, name, city_id, geom_wkb))

    if orphan_count:
        logger.warning(
            f"Districts: skipped {orphan_count} orphan records "
            f"(no matching city). Samples: {orphan_samples}"
        )

    # === Phase 4: Batch UPSERT ===
    dedup = {}
    for code, name, city_id, geom_wkb in filtered:
        dedup[code] = (code, name, city_id, geom_wkb)
    value_tuples = list(dedup.values())
    if len(value_tuples) < len(filtered):
        logger.warning(
            f"Districts: deduplicated {len(filtered) - len(value_tuples)} "
            f"rows by code"
        )

    raw_conn = db.connection().connection
    insert_sql = """
        INSERT INTO district (code, name, city_id, geom)
        VALUES %s
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            city_id = EXCLUDED.city_id,
            geom = COALESCE(ST_GeomFromWKB(EXCLUDED.geom, 4326), district.geom)
    """

    t3 = time.time()
    with raw_conn.cursor() as cur:
        execute_values(cur, insert_sql, value_tuples, page_size=200)
    t4 = time.time()
    logger.info(
        f"[timing] districts batch insert: {t4-t3:.2f}s "
        f"({len(value_tuples)} rows, page_size=200)"
    )

    db.commit()
    t5 = time.time()
    logger.info(f"[timing] districts commit: {t5-t4:.2f}s")

    inserted = len(value_tuples)
    logger.info(
        f"Upserted {inserted} districts "
        f"(skipped {orphan_count} orphans, "
        f"deduped {len(filtered) - inserted})"
    )
    return inserted


def _get_value(row, field):
    if field is None:
        return None
    v = getattr(row, field, None)
    if v is None or v == "" or v == "None":
        return None
    return str(v).strip()


def load_villages(db: Session, gdf: gpd.GeoDataFrame, layer_cfg: dict) -> int:
    code_field = layer_cfg["code_field"]
    name_field = layer_cfg["name_field"]
    parent_field = layer_cfg["parent_field"]
    extra_fields = layer_cfg.get("extra_fields", {})
    has_village_type = "tipadm" in extra_fields
    has_bps_code = "kdbbps" in extra_fields
    geom_col = gdf.geometry.name

    # === Phase 1: Transform + WKB Serialization ===
    t0 = time.time()
    prepared = []
    parent_codes = set()
    for row in gdf.itertuples(index=False):
        code = _get_value(row, code_field)
        name = _get_value(row, name_field)
        parent_code = _get_value(row, parent_field)
        if not name or not code:
            continue

        geom = getattr(row, geom_col, None)
        if geom is None:
            continue
        geom_wkb = wkb.dumps(geom, output_dimension=2)

        vt = _get_value(row, "tipadm") if has_village_type else None
        bc = _get_value(row, "kdbbps") if has_bps_code else None

        prepared.append((code, name, parent_code, geom_wkb, vt, bc))
        if parent_code:
            parent_codes.add(parent_code)
    t1 = time.time()
    logger.info(
        f"[timing] villages transform+serialize: "
        f"{len(prepared)} rows in {t1-t0:.2f}s"
    )

    if not prepared:
        return 0

    # === Phase 2: Resolve parent FKs ===
    if parent_codes:
        existing = db.query(District).filter(
            District.code.in_(parent_codes)
        ).all()
        parent_map = {d.code: d.id for d in existing}
        missing = parent_codes - set(parent_map.keys())
        if missing:
            logger.warning(
                f"Villages: {len(missing)} parent districts not found: "
                f"{sorted(missing)[:5]}..."
            )
    else:
        parent_map = {}
    t2 = time.time()
    logger.info(
        f"[timing] villages parent FK resolution: "
        f"{t2-t1:.2f}s ({len(parent_map)} parents)"
    )

    # === Phase 3: Skip orphans ===
    orphan_count = 0
    orphan_no_ref = 0
    orphan_unmatched = 0
    orphan_samples = []
    filtered = []
    for code, name, parent_code, geom_wkb, vt, bc in prepared:
        if not parent_code:
            orphan_count += 1
            orphan_no_ref += 1
            if len(orphan_samples) < 5:
                orphan_samples.append(f"code={code} (no parent ref)")
            continue
        district_id = parent_map.get(parent_code)
        if district_id is None:
            orphan_count += 1
            orphan_unmatched += 1
            if len(orphan_samples) < 5:
                orphan_samples.append(f"code={code} parent={parent_code}")
            continue
        filtered.append((code, name, district_id, geom_wkb, vt, bc))

    if orphan_count:
        logger.warning(
            f"Villages: skipped {orphan_count} orphans "
            f"({orphan_no_ref} no parent ref, {orphan_unmatched} unmatched parent). "
            f"Samples: {orphan_samples}"
        )

    # === Phase 4: Dedup ===
    dedup = {}
    for code, name, district_id, geom_wkb, vt, bc in filtered:
        dedup[code] = (code, name, district_id, geom_wkb, vt, bc)
    value_tuples = list(dedup.values())
    if len(value_tuples) < len(filtered):
        logger.warning(
            f"Villages: deduplicated {len(filtered) - len(value_tuples)} "
            f"rows by code"
        )

    insert_sql = """
        INSERT INTO village (code, name, district_id, geom, village_type, bps_code)
        VALUES %s
        ON CONFLICT (code) DO NOTHING
    """

    # === Phase 5a: Benchmark page_size ===
    bench_results = {}
    for ps in [200, 500, 1000]:
        bconn = psycopg2.connect(
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB,
        )
        t_start = time.time()
        with bconn.cursor() as cur:
            execute_values(cur, insert_sql, value_tuples, page_size=ps)
        elapsed = time.time() - t_start
        bench_results[ps] = elapsed
        logger.info(
            f"[timing] villages benchmark page_size={ps}: {elapsed:.2f}s"
        )
        bconn.rollback()
        bconn.close()

    best_ps = min(bench_results, key=bench_results.get)
    logger.info(
        f"[timing] villages selected page_size={best_ps} "
        f"({bench_results[best_ps]:.2f}s)"
    )

    # === Phase 5b: Final batch insert ===
    raw_conn = db.connection().connection
    t3 = time.time()
    with raw_conn.cursor() as cur:
        execute_values(cur, insert_sql, value_tuples, page_size=best_ps)
    t4 = time.time()
    logger.info(
        f"[timing] villages batch insert: {t4-t3:.2f}s "
        f"({len(value_tuples)} rows, page_size={best_ps})"
    )

    db.commit()
    t5 = time.time()
    logger.info(f"[timing] villages commit: {t5-t4:.2f}s")

    inserted = len(value_tuples)
    logger.info(
        f"Imported {inserted} villages "
        f"(skipped {orphan_count} orphans, "
        f"deduped {len(filtered) - inserted})"
    )
    return inserted


LOADERS = {
    "provinsi": load_provinces,
    "kabupaten_kota": load_cities,
    "kecamatan": load_districts,
    "desa": load_villages,
}


def load_layer(
    db: Session,
    layer_cfg: dict,
    provider: Optional[DatasetProvider] = None,
) -> int:
    provider = provider or get_default_provider()
    gdf = provider.read_layer(layer_cfg)
    loader = LOADERS.get(layer_cfg["name"])
    if not loader:
        raise ValueError(f"No loader found for layer: {layer_cfg['name']}")
    return loader(db, gdf, layer_cfg)


def load_all_layers(
    db: Session,
    provider: Optional[DatasetProvider] = None,
    layers_to_load: Optional[list[str]] = None,
) -> list[dict]:
    provider = provider or get_default_provider()
    results = []
    target_layers = [
        l
        for l in LAYERS
        if layers_to_load is None or l["name"] in layers_to_load
    ]

    for layer_cfg in target_layers:
        try:
            count = load_layer(db, layer_cfg, provider)
            results.append(
                {
                    "layer_name": layer_cfg["name"],
                    "record_count": count,
                    "status": "success",
                }
            )
            logger.info(f"Loaded {layer_cfg['name']}: {count} records")
        except Exception as e:
            logger.error(f"Failed to load layer {layer_cfg['name']}: {e}")
            results.append(
                {
                    "layer_name": layer_cfg["name"],
                    "record_count": 0,
                    "status": "failed",
                    "error": str(e),
                }
            )

    return results


def create_gist_indexes(db: Session):
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_province_geom ON province USING GIST (geom)",
        "CREATE INDEX IF NOT EXISTS idx_city_geom ON city USING GIST (geom)",
        "CREATE INDEX IF NOT EXISTS idx_district_geom ON district USING GIST (geom)",
        "CREATE INDEX IF NOT EXISTS idx_village_geom ON village USING GIST (geom)",
        "CREATE INDEX IF NOT EXISTS idx_facility_geom ON facility USING GIST (geom)",
    ]
    for stmt in indexes:
        try:
            db.execute(text(stmt))
            logger.info(f"Created index: {stmt.split()[-1]}")
        except Exception as e:
            logger.warning(f"Could not create index: {e}")
    db.commit()


def generate_province_geometries(db: Session):
    stmt = text("""
        UPDATE province p
        SET geom = (
            SELECT ST_Multi(ST_Union(c.geom))
            FROM city c
            WHERE c.province_id = p.id
              AND c.geom IS NOT NULL
        )
        WHERE EXISTS (
            SELECT 1 FROM city c
            WHERE c.province_id = p.id
              AND c.geom IS NOT NULL
        )
    """)
    result = db.execute(stmt)
    db.commit()
    count = result.rowcount
    logger.info(f"Generated geometries for {count} provinces from city boundaries")
    return count


def store_dataset_metadata(
    db: Session,
    layer_name: str,
    record_count: int,
    source: str = "BIG",
    version: str = "2024",
    status: str = "imported",
):
    meta = DatasetMetadata(
        layer_name=layer_name,
        record_count=record_count,
        source=source,
        version=version,
        status=status,
    )
    db.add(meta)
    db.commit()
    return meta


def store_download_metadata(
    db: Session,
    layer_name: str,
    record_count: int,
    source: str = "BIG (KSP)",
    version: str = "2024",
):
    return store_dataset_metadata(
        db, layer_name, record_count, source, version, status="downloaded"
    )


def store_import_metadata(
    db: Session,
    layer_name: str,
    record_count: int,
    source: str = "BIG (KSP)",
    version: str = "2024",
):
    return store_dataset_metadata(
        db, layer_name, record_count, source, version, status="imported"
    )


def run_full_etl(
    db: Session,
    provider: Optional[DatasetProvider] = None,
    layers_to_process: Optional[list[str]] = None,
):
    provider = provider or get_default_provider()

    download_results = []
    for layer_cfg in LAYERS:
        if layers_to_process is None or layer_cfg["name"] in layers_to_process:
            try:
                gdf = provider.read_layer(layer_cfg)
                download_results.append(
                    {
                        "layer_name": layer_cfg["name"],
                        "record_count": len(gdf),
                        "status": "success",
                    }
                )
            except Exception as e:
                logger.error(
                    f"Failed to acquire layer {layer_cfg['name']}: {e}"
                )
                download_results.append(
                    {
                        "layer_name": layer_cfg["name"],
                        "record_count": 0,
                        "status": "failed",
                        "error": str(e),
                    }
                )

    logger.info("Data acquisition phase complete. Starting import phase...")

    load_results = load_all_layers(db, provider, layers_to_process)

    generate_province_geometries(db)
    logger.info("Province geometries generated from city boundaries.")

    create_gist_indexes(db)

    for dr in download_results:
        if dr["status"] == "success":
            store_download_metadata(db, dr["layer_name"], dr["record_count"])

    for lr in load_results:
        if lr["status"] == "success":
            store_import_metadata(db, lr["layer_name"], lr["record_count"])

    logger.info("Full ETL pipeline complete.")
    return {
        "download": download_results,
        "import": load_results,
    }
