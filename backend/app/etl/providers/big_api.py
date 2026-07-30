import json
import logging
import os

import geopandas as gpd
import requests

from .base import DatasetProvider

logger = logging.getLogger(__name__)

BIG_BASE_URL = (
    "https://kspservices.big.go.id/satupeta/rest/services/"
    "PUBLIK/BATAS_WILAYAH/MapServer"
)


class BIGFeatureServiceProvider(DatasetProvider):
    def __init__(
        self,
        cache_dir: str = "data/raw/big",
        base_url: str = BIG_BASE_URL,
        max_records: int = 1000,
    ):
        self.cache_dir = cache_dir
        self.base_url = base_url
        self.max_records = max_records

    def read_layer(self, layer_cfg: dict) -> gpd.GeoDataFrame:
        filepath = os.path.join(self.cache_dir, layer_cfg["filename"])

        if os.path.exists(filepath):
            logger.info(f"Using cached file: {filepath}")
            gdf = gpd.read_file(filepath)
            if gdf.crs is None or gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs("EPSG:4326")
            return gdf

        logger.info(f"Downloading layer {layer_cfg['id']} ({layer_cfg['name']})...")
        os.makedirs(self.cache_dir, exist_ok=True)
        features = self._query_layer(layer_cfg["id"])
        fc = {"type": "FeatureCollection", "features": features}

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(fc, f, ensure_ascii=False)
        logger.info(f"Saved {len(features)} features to {filepath}")

        gdf = gpd.read_file(filepath)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        return gdf

    def _query_layer(
        self,
        layer_id: int,
        where: str = "1=1",
        out_fields: str = "*",
    ) -> list:
        features = []
        offset = 0
        url = f"{self.base_url}/{layer_id}/query"

        logger.info(f"Querying layer {layer_id} from BIG Feature Service...")

        while True:
            resp = requests.get(
                url,
                params={
                    "where": where,
                    "outFields": out_fields,
                    "returnGeometry": "true",
                    "f": "geojson",
                    "resultOffset": offset,
                    "resultRecordCount": self.max_records,
                },
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("features", [])
            if not batch:
                break
            features.extend(batch)
            logger.info(
                f"Layer {layer_id}: received {len(batch)} features "
                f"(offset {offset})"
            )
            offset += len(batch)
            if len(batch) < self.max_records:
                break

        logger.info(
            f"Layer {layer_id}: downloaded {len(features)} features total"
        )
        return features
