import json
import logging
import time
from datetime import datetime
from typing import Optional

import geopandas as gpd
import numpy as np
from geoalchemy2.shape import from_shape
from psycopg2.extras import execute_values
from shapely import wkb
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.models.etl import DatasetMetadata

logger = logging.getLogger(__name__)


def _to_point(geom):
    if geom is None:
        return None
    if geom.geom_type == "Point":
        return geom
    try:
        return geom.centroid
    except Exception:
        return None


def _get_val(row, field):
    v = getattr(row, field, None)
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    if isinstance(v, str) and (v.strip() == "" or v.strip() == "None"):
        return None
    return v


def normalize(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    original_count = len(gdf)
    geom_col = gdf.geometry.name

    records = []
    for row in gdf.itertuples(index=False):
        name = _get_val(row, "name")
        if not name:
            continue

        geom = getattr(row, geom_col, None)
        pt = _to_point(geom)
        if pt is None:
            continue

        ftype = _get_val(row, "facility_type")
        if not ftype:
            continue

        osm_id = _get_val(row, "osm_id")
        if osm_id is None:
            osm_id = _get_val(row, "id")
        osm_id_str = str(int(osm_id)) if osm_id is not None else None

        tags = getattr(row, "tags", None)
        if tags is not None:
            if isinstance(tags, str):
                tags_dict = json.loads(tags) if tags.strip() else None
            elif isinstance(tags, dict):
                tags_dict = tags
            else:
                try:
                    tags_dict = dict(tags)
                except (TypeError, ValueError):
                    tags_dict = None
        else:
            tags_dict = None

        records.append({
            "name": str(name).strip(),
            "facility_type": ftype,
            "lat": pt.y,
            "lng": pt.x,
            "geom": pt,
            "source": "OSM",
            "external_id": osm_id_str,
            "raw_tags": tags_dict,
            "source_updated_at": datetime.utcnow(),
        })

    result = gpd.GeoDataFrame(records, geometry="geom", crs="EPSG:4326")
    skipped = original_count - len(result)
    if skipped:
        logger.warning(
            f"Normalize: skipped {skipped} records "
            f"({original_count - len(gdf)} no name, "
            f"{len(gdf) - len(records)} no valid geometry/type)"
        )
    logger.info(
        f"Normalize: {len(result)} valid facilities from {original_count} raw features"
    )
    return result


def load_facilities(db: Session, gdf: gpd.GeoDataFrame) -> int:
    if gdf.empty:
        logger.info("No facilities to load")
        return 0

    geom_col = gdf.geometry.name

    t0 = time.time()
    prepared = []
    for row in gdf.itertuples(index=False):
        name = row.name
        ftype = row.facility_type
        lat = row.lat
        lng = row.lng
        source = row.source
        eid = row.external_id
        tags = row.raw_tags
        geom = getattr(row, geom_col, None)
        if geom is None:
            continue
        geom_wkb = wkb.dumps(geom, output_dimension=2)
        tags_json = json.dumps(tags) if tags else None
        prepared.append((name, ftype, lat, lng, source, eid, tags_json, geom_wkb))

    t1 = time.time()
    logger.info(f"[timing] serialize {len(prepared)} facilities: {t1-t0:.2f}s")

    # Dedup by (source, external_id) to avoid PostgreSQL "ON CONFLICT DO UPDATE
    # command cannot affect row a second time"
    before_dedup = len(prepared)
    seen: set[tuple[str, str | None]] = set()
    deduped = []
    for row in prepared:
        key = (row[4], row[5])
        if key not in seen:
            seen.add(key)
            deduped.append(row)
        else:
            logger.debug(f"Duplicate skipped: {key}")
    prepared = deduped
    dedup_removed = before_dedup - len(prepared)
    if dedup_removed:
        logger.info(f"[timing] dedup removed {dedup_removed} duplicates")

    if not prepared:
        return 0

    raw_conn = db.connection().connection

    t2 = time.time()
    with raw_conn.cursor() as cur:
        cur.execute("""
            CREATE TEMP TABLE temp_facility_import (
                name TEXT, facility_type TEXT,
                lat FLOAT, lng FLOAT,
                source TEXT, external_id TEXT,
                raw_tags JSONB,
                geom bytea,
                city_id INTEGER,
                district_id INTEGER
            ) ON COMMIT DROP
        """)
    t3 = time.time()
    logger.info(f"[timing] create temp table: {t3-t2:.2f}s")

    insert_temp = """
        INSERT INTO temp_facility_import
        (name, facility_type, lat, lng, source, external_id, raw_tags, geom)
        VALUES %s
    """
    with raw_conn.cursor() as cur:
        execute_values(cur, insert_temp, prepared, page_size=500)
    t4 = time.time()
    logger.info(f"[timing] batch insert into temp: {t4-t3:.2f}s")

    with raw_conn.cursor() as cur:
        cur.execute("""
            UPDATE temp_facility_import t
            SET
                city_id = d.city_id,
                district_id = d.id
            FROM district d
            WHERE ST_Intersects(ST_GeomFromWKB(t.geom, 4326), d.geom)
        """)
    t5 = time.time()
    logger.info(f"[timing] spatial join (district): {t5-t4:.2f}s")

    with raw_conn.cursor() as cur:
        cur.execute("""
            SELECT count(*) FROM temp_facility_import WHERE district_id IS NULL
        """)
        orphan_count = cur.fetchone()[0]
    if orphan_count:
        logger.warning(f"{orphan_count} facilities outside all district boundaries")

    insert_main = """
        INSERT INTO facility
            (name, facility_type, lat, lng, geom, source, external_id,
             raw_tags, source_updated_at, city_id, district_id)
        SELECT
            t.name, t.facility_type, t.lat, t.lng,
            ST_GeomFromWKB(t.geom, 4326),
            t.source, t.external_id, t.raw_tags,
            NOW(),
            t.city_id, t.district_id
        FROM temp_facility_import t
        ON CONFLICT (source, external_id) DO UPDATE SET
            name = EXCLUDED.name,
            facility_type = EXCLUDED.facility_type,
            lat = EXCLUDED.lat,
            lng = EXCLUDED.lng,
            geom = EXCLUDED.geom,
            raw_tags = EXCLUDED.raw_tags,
            source_updated_at = EXCLUDED.source_updated_at,
            city_id = EXCLUDED.city_id,
            district_id = EXCLUDED.district_id
    """
    with raw_conn.cursor() as cur:
        cur.execute(insert_main)
        inserted = cur.rowcount
    t6 = time.time()
    logger.info(
        f"[timing] insert into facility: {t6-t5:.2f}s "
        f"({inserted} rows inserted/updated)"
    )

    db.commit()
    t7 = time.time()
    logger.info(f"[timing] commit: {t7-t6:.2f}s")
    logger.info(
        f"[timing] total facility ETL: {t7-t0:.2f}s "
        f"({len(prepared)} prepared, {inserted} in table)"
    )

    return inserted


def store_import_metadata(db: Session, record_count: int, source: str = "OSM"):
    meta = DatasetMetadata(
        layer_name="facilities",
        record_count=record_count,
        source=source,
        version="2024",
        status="imported",
    )
    db.add(meta)
    db.commit()
