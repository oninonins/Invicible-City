import glob
import logging
import os

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import transform

from .base import DatasetProvider

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
DMXSAN_ROOT = os.path.join(_BACKEND_DIR, "data", "raw", "dmxsan")

LAYER_PATHS = {
    "provinsi": "province/*.geojson",
    "kabupaten_kota": "city/*.geojson",
}

FIELD_MAP = {
    "provinsi": {
        "WADMPR": ["namobj"],
    },
    "kabupaten_kota": {
        "WADMKK": ["wadmkk", "namobj"],
        "WADMPR": ["wadmpr"],
    },
}


class DmxsanProvider(DatasetProvider):
    def __init__(self, data_dir: str = DMXSAN_ROOT):
        os.environ["OGR_GEOJSON_MAX_OBJ_SIZE"] = "0"
        self.data_dir = data_dir
        self._cache: dict[str, gpd.GeoDataFrame] = {}

    def read_layer(self, layer_cfg: dict) -> gpd.GeoDataFrame:
        name = layer_cfg["name"]
        if name in self._cache:
            logger.info(f"Using cached layer: {name}")
            return self._cache[name].copy()

        if name not in LAYER_PATHS:
            raise ValueError(
                f"Layer '{name}' is not available from DmxsanProvider. "
                f"Available: {list(LAYER_PATHS.keys())}"
            )

        gdf = self._load_and_merge(name)
        gdf = self._rename_fields(gdf, name)
        gdf = self._normalize_crs(gdf)
        gdf = self._strip_z(gdf)
        gdf = self._drop_objectid(gdf)

        self._cache[name] = gdf.copy()
        logger.info(f"Cached {name}: {len(gdf)} features")
        return gdf

    def _load_and_merge(self, layer_name: str) -> gpd.GeoDataFrame:
        pattern = LAYER_PATHS[layer_name]
        full_pattern = os.path.join(self.data_dir, pattern)
        files = sorted(glob.glob(full_pattern))

        if not files:
            raise FileNotFoundError(
                f"No GeoJSON files found for layer '{layer_name}' "
                f"at pattern: {full_pattern}"
            )

        logger.info(
            f"Loading {len(files)} files for layer '{layer_name}'..."
        )

        frames = []
        for fp in files:
            try:
                gdf = gpd.read_file(fp)
                if not gdf.empty:
                    frames.append(gdf)
            except Exception as e:
                logger.warning(f"Skipping {fp}: {e}")

        if not frames:
            raise ValueError(
                f"No valid features loaded for layer '{layer_name}'"
            )

        merged = pd.concat(frames, ignore_index=True)
        logger.info(
            f"Merged {len(frames)} files into {len(merged)} features"
        )
        return merged

    def _rename_fields(
        self, gdf: gpd.GeoDataFrame, layer_name: str
    ) -> gpd.GeoDataFrame:
        mapping = FIELD_MAP.get(layer_name, {})
        for src_col, target_cols in mapping.items():
            if src_col not in gdf.columns:
                continue
            first_tgt = target_cols[0]
            gdf = gdf.rename(columns={src_col: first_tgt})
            for tgt in target_cols[1:]:
                gdf[tgt] = gdf[first_tgt]
        return gdf

    def _normalize_crs(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        return gdf

    def _strip_z(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        def drop_z(x, y, z=None):
            return (x, y)

        gdf.geometry = gdf.geometry.apply(
            lambda g: transform(drop_z, g) if g is not None and g.has_z else g
        )
        logger.info("Stripped Z dimension from geometries")
        return gdf

    def _drop_objectid(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        cols = [c for c in gdf.columns if c.lower() == "objectid"]
        if cols:
            gdf = gdf.drop(columns=cols)
        return gdf
