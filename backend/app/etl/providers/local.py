import logging
import os

import geopandas as gpd

from .base import DatasetProvider

logger = logging.getLogger(__name__)


class LocalFileProvider(DatasetProvider):
    def __init__(self, data_dir: str = "data/raw/big"):
        self.data_dir = data_dir

    def read_layer(self, layer_cfg: dict) -> gpd.GeoDataFrame:
        filepath = os.path.join(self.data_dir, layer_cfg["filename"])
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"GeoJSON file not found: {filepath}")
        gdf = gpd.read_file(filepath)
        if gdf.empty:
            raise ValueError(f"GeoJSON file is empty: {filepath}")

        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        logger.info(
            f"Loaded {len(gdf)} records from {filepath} "
            f"(CRS: EPSG:{gdf.crs.to_epsg()})"
        )
        return gdf
