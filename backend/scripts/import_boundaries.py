import sys
import os
import argparse
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.etl.big import (
    LAYERS,
    load_all_layers,
    create_gist_indexes,
    generate_province_geometries,
    store_import_metadata,
)
from app.etl.providers import (
    LocalFileProvider,
    BIGFeatureServiceProvider,
    DmxsanProvider,
    AlfAnasProvider,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Import Indonesian administrative boundaries into PostGIS"
    )
    parser.add_argument(
        "--provider",
        choices=["local", "big-api", "dmxsan", "alfanas"],
        default="local",
        help="Data source provider (default: local, requires GeoJSON in --input-dir)",
    )
    parser.add_argument(
        "--input-dir",
        default="data/raw/big",
        help="Input directory for local provider (default: data/raw/big)",
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        choices=[l["name"] for l in LAYERS],
        default=None,
        help="Specific layers to import (default: all)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip geometry validation (not recommended)",
    )
    parser.add_argument(
        "--skip-indexes",
        action="store_true",
        help="Skip GiST index creation",
    )
    args = parser.parse_args()

    if args.provider == "local":
        input_dir = os.path.abspath(args.input_dir)
        if not os.path.isdir(input_dir):
            logger.error(f"Input directory does not exist: {input_dir}")
            sys.exit(1)
        provider = LocalFileProvider(data_dir=input_dir)
        logger.info(f"Using local provider: {input_dir}")
    elif args.provider == "big-api":
        provider = BIGFeatureServiceProvider(cache_dir=args.input_dir)
        logger.info(
            f"Using BIG API provider (cache: {args.input_dir})"
        )
    elif args.provider == "dmxsan":
        provider = DmxsanProvider()
        logger.info("Using DmxsanProvider from data/raw/dmxsan")
    elif args.provider == "alfanas":
        provider = AlfAnasProvider()
        logger.info("Using AlfAnasProvider from data/raw/alfanas")
    else:
        logger.error(f"Unknown provider: {args.provider}")
        sys.exit(1)

    logger.info(f"Starting BIG boundary import, layers: {args.layers or 'all'}")

    db = SessionLocal()
    try:
        start = datetime.utcnow()

        results = load_all_layers(db, provider, args.layers)

        failed_layers = [r for r in results if r["status"] == "failed"]
        if failed_layers:
            logger.warning(f"Rolling back after {len(failed_layers)} failed layer(s)")
            db.rollback()

        logger.info("Generating province geometries from city boundaries...")
        generate_province_geometries(db)

        if not args.skip_indexes:
            logger.info("Creating GiST indexes...")
            create_gist_indexes(db)

        for r in results:
            if r["status"] == "success":
                store_import_metadata(
                    db, r["layer_name"], r["record_count"]
                )

        elapsed = (datetime.utcnow() - start).total_seconds()

        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")
        total = sum(
            r.get("record_count", 0) for r in results if r["status"] == "success"
        )

        logger.info(
            f"Import complete: {successful}/{len(results)} layers, "
            f"{total} total records, {elapsed:.1f}s"
        )

        if failed:
            logger.warning(f"{failed} layer(s) failed to import")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
