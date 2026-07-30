import sys
import os
import argparse
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.etl.pbf_parser import parse_pbf
from app.etl.facility import normalize, load_facilities, store_import_metadata
from app.etl.big import create_gist_indexes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVINCES_DIR = os.path.join(BASE_DIR, "data", "raw", "osm", "provinces")
DEFAULT_PBF = os.path.join(
    BASE_DIR, "data", "raw", "osm", "indonesia-latest.osm.pbf",
)

FACILITY_TYPES = ["School", "Hospital", "Clinic", "BusStop", "Park"]

# List of valid province slugs for validation and help text
VALID_PROVINCE_SLUGS = [
    "aceh",
    "bali",
    "banten",
    "bengkulu",
    "di-yogyakarta",
    "dki-jakarta",
    "gorontalo",
    "jambi",
    "jawa-barat",
    "jawa-tengah",
    "jawa-timur",
    "kalimantan-barat",
    "kalimantan-selatan",
    "kalimantan-tengah",
    "kalimantan-timur",
    "kalimantan-utara",
    "kepulauan-bangka-belitung",
    "kepulauan-riau",
    "lampung",
    "maluku",
    "maluku-utara",
    "nusa-tenggara-barat",
    "nusa-tenggara-timur",
    "papua",
    "papua-barat",
    "papua-barat-daya",
    "papua-pegunungan",
    "papua-selatan",
    "papua-tengah",
    "riau",
    "sulawesi-barat",
    "sulawesi-selatan",
    "sulawesi-tengah",
    "sulawesi-tenggara",
    "sulawesi-utara",
    "sumatera-barat",
    "sumatera-selatan",
    "sumatera-utara",
]


def resolve_pbf_path(province: str | None, pbf_path: str | None) -> str:
    if province:
        slug = province.lower().replace("_", "-")
        path = os.path.join(PROVINCES_DIR, f"{slug}.osm.pbf")
        if not os.path.isfile(path):
            logger.error(
                f"Province PBF not found: {path}\n"
                f"  Download per-province PBF dari Geofabrik Indonesia extract "
                f"atau https://download.geofabrik.de/asia/indonesia.html\n"
                f"  Simpan file sebagai: {path}"
            )
            sys.exit(1)
        return path
    return pbf_path or DEFAULT_PBF


def main():
    parser = argparse.ArgumentParser(
        description="Import OSM facilities into PostGIS"
    )
    parser.add_argument(
        "--province",
        help="Province slug (e.g. jakarta, east-java, jawa-timur). "
             f"Valid: {', '.join(VALID_PROVINCE_SLUGS)}",
    )
    parser.add_argument(
        "--pbf",
        default=None,
        help=f"Path to PBF file (default: {DEFAULT_PBF})",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=FACILITY_TYPES,
        default=FACILITY_TYPES,
        help="Facility types to import (default: all 5)",
    )
    parser.add_argument(
        "--skip-indexes",
        action="store_true",
        help="Skip GiST index creation",
    )
    parser.add_argument(
        "--list-provinces",
        action="store_true",
        help="List all valid province slugs and exit",
    )
    args = parser.parse_args()

    if args.list_provinces:
        print("Valid province slugs:")
        for s in VALID_PROVINCE_SLUGS:
            print(f"  {s}")
        sys.exit(0)

    pbf_path = resolve_pbf_path(args.province, args.pbf)

    if not os.path.isfile(pbf_path):
        logger.error(f"PBF file not found: {pbf_path}")
        logger.error(
            "Download from: https://download.geofabrik.de/asia/indonesia-latest.osm.pbf"
        )
        sys.exit(1)

    logger.info(f"Parsing PBF: {pbf_path}")
    logger.info(f"Facility types: {args.types}")

    start = datetime.utcnow()

    raw = parse_pbf(pbf_path, facility_types=args.types)
    logger.info(f"Raw features extracted: {len(raw)}")

    normalized = normalize(raw)
    logger.info(f"Normalized facilities: {len(normalized)}")

    if normalized.empty:
        logger.warning("No facilities to import after normalization")
        sys.exit(0)

    db = SessionLocal()
    try:
        count = load_facilities(db, normalized)
        elapsed = (datetime.utcnow() - start).total_seconds()

        if not args.skip_indexes:
            create_gist_indexes(db)

        store_import_metadata(db, count)

        logger.info(
            f"Import complete: {count} facilities in {elapsed:.1f}s"
        )
    except Exception as e:
        logger.error(f"Import failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
