import sys
import os
import argparse
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.services import ufs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Refresh UFS v0 benchmarks and scores"
    )
    parser.add_argument(
        "--benchmarks",
        action="store_true",
        help="Refresh national benchmarks only",
    )
    parser.add_argument(
        "--city",
        type=int,
        help="Compute + cache UFS for a city (and its districts)",
    )
    parser.add_argument(
        "--all-districts",
        action="store_true",
        help="Compute + cache UFS for every district",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.benchmarks:
            ufs.refresh_benchmarks(db)
            logger.info("Benchmarks refreshed")

        if args.city is not None:
            result = ufs.compute_city_ufs(db, args.city)
            logger.info(
                "City %s UFS: overall=%s category=%s districts=%s",
                args.city, result["overall_score"], result["category"],
                result["district_count"],
            )

        if args.all_districts:
            from sqlalchemy import text
            ids = [r[0] for r in db.execute(text("SELECT id FROM district ORDER BY id")).all()]
            for i, district_id in enumerate(ids, 1):
                r = ufs.compute_district_ufs(db, district_id)
                if i % 1000 == 0 or i == len(ids):
                    logger.info("progress %d/%d", i, len(ids))
                if r["overall_score"] < 0 or r["overall_score"] > 100:
                    logger.warning("out-of-range score for district %s", district_id)
            logger.info("Computed %d district scores", len(ids))
    finally:
        db.close()


if __name__ == "__main__":
    main()
