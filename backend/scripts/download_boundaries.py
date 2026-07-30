import sys
import os
import argparse
import json
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.etl.big import LAYERS, store_download_metadata
from app.etl.providers import BIGFeatureServiceProvider, LocalFileProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Download Indonesian administrative boundaries"
    )
    parser.add_argument(
        "--provider",
        choices=["big-api", "local"],
        default="big-api",
        help="Source provider (default: big-api; local copies existing files to output-dir)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/big",
        help="Output directory for GeoJSON files (default: data/raw/big)",
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        choices=[l["name"] for l in LAYERS],
        default=None,
        help="Specific layers to download (default: all)",
    )
    parser.add_argument(
        "--record-metadata",
        action="store_true",
        help="Store download metadata in database",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    target_layers = [
        l for l in LAYERS if args.layers is None or l["name"] in args.layers
    ]

    logger.info(
        f"Starting download via {args.provider} provider to {output_dir}"
    )
    logger.info(f"Layers: {args.layers or 'all'}")

    start = datetime.utcnow()
    results = []

    if args.provider == "big-api":
        provider = BIGFeatureServiceProvider(cache_dir=output_dir)
        for layer_cfg in target_layers:
            try:
                gdf = provider.read_layer(layer_cfg)
                out_path = os.path.join(output_dir, layer_cfg["filename"])
                gdf.to_file(out_path, driver="GeoJSON", encoding="utf-8")
                results.append(
                    {
                        "layer_name": layer_cfg["name"],
                        "filename": layer_cfg["filename"],
                        "record_count": len(gdf),
                        "output_path": out_path,
                        "status": "success",
                    }
                )
                logger.info(
                    f"Downloaded {layer_cfg['name']}: {len(gdf)} records"
                )
            except Exception as e:
                logger.error(
                    f"Failed to download layer {layer_cfg['name']}: {e}"
                )
                results.append(
                    {
                        "layer_name": layer_cfg["name"],
                        "filename": layer_cfg["filename"],
                        "record_count": 0,
                        "output_path": "",
                        "status": "failed",
                        "error": str(e),
                    }
                )
    elif args.provider == "local":
        provider = LocalFileProvider(data_dir=output_dir)
        for layer_cfg in target_layers:
            try:
                gdf = provider.read_layer(layer_cfg)
                results.append(
                    {
                        "layer_name": layer_cfg["name"],
                        "filename": layer_cfg["filename"],
                        "record_count": len(gdf),
                        "output_path": os.path.join(output_dir, layer_cfg["filename"]),
                        "status": "success",
                    }
                )
                logger.info(
                    f"Copied {layer_cfg['name']}: {len(gdf)} records"
                )
            except Exception as e:
                logger.error(
                    f"Failed to read layer {layer_cfg['name']}: {e}"
                )
                results.append(
                    {
                        "layer_name": layer_cfg["name"],
                        "filename": layer_cfg["filename"],
                        "record_count": 0,
                        "output_path": "",
                        "status": "failed",
                        "error": str(e),
                    }
                )

    elapsed = (datetime.utcnow() - start).total_seconds()

    summary_path = os.path.join(output_dir, "download_metadata.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "download_date": start.isoformat(),
                "elapsed_seconds": elapsed,
                "provider": args.provider,
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"Download metadata saved to {summary_path}")

    if args.record_metadata:
        db = SessionLocal()
        try:
            for r in results:
                if r["status"] == "success":
                    store_download_metadata(
                        db, r["layer_name"], r["record_count"]
                    )
                    logger.info(
                        f"Metadata recorded for layer: {r['layer_name']}"
                    )
        finally:
            db.close()

    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    total = sum(
        r.get("record_count", 0) for r in results if r["status"] == "success"
    )

    logger.info(
        f"Download complete: {successful}/{len(results)} layers, "
        f"{total} total features, {elapsed:.1f}s"
    )
    if failed:
        logger.warning(f"{failed} layer(s) failed to download")
        sys.exit(1)


if __name__ == "__main__":
    main()
