import logging
import os

import geopandas as gpd
from shapely import wkb
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform

from .base import DatasetProvider

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
ALFANAS_ROOT = os.path.join(_BACKEND_DIR, "data", "raw", "alfanas")

LAYER_PATHS = {
    "kecamatan": "district/Kecamatan.shp",
    "desa": "village/Kel_Desa.shp",
}

LAYER_FIELD_MAP = {
    "kecamatan": {
        "KODE_KEC": "code",
        "KECAMATAN": "name",
        "KAB_KOTA": "parent_name",
    },
    "desa": {
        "KODE_KD": "kdpumdes",
        "KEL_DESA": "namobj",
        "KODE_KEC": "kdpumkec",
        "JENIS_KD": "tipadm",
    },
}

_INVALID_VTYPE = {"0", "4", "999"}

_COLS_TO_KEEP = {
    "code", "name", "parent_name",
    "kdpumdes", "namobj", "kdpumkec", "tipadm",
    "geometry",
}

_NAME_FALLBACK = {
    "kecamatan": ("KECAMATAN", "KODE_KEC"),
    "desa": ("KEL_DESA", "KODE_KD"),
}


class AlfAnasProvider(DatasetProvider):
    def __init__(self, data_dir: str = ALFANAS_ROOT):
        self.data_dir = data_dir
        self._cache: dict[str, gpd.GeoDataFrame] = {}

    def read_layer(self, layer_cfg: dict) -> gpd.GeoDataFrame:
        name = layer_cfg["name"]
        if name in self._cache:
            logger.info(f"Using cached layer: {name}")
            return self._cache[name].copy()

        if name not in LAYER_PATHS:
            raise ValueError(
                f"Layer '{name}' is not available from AlfAnasProvider. "
                f"Available: {list(LAYER_PATHS.keys())}"
            )

        gdf = self._read_shp(name)
        gdf = self._fill_name_fallback(gdf, name)
        gdf = self._sanitize_village_type(gdf)
        gdf = self._rename_fields(gdf, name)
        gdf = self._drop_unused(gdf)
        gdf = self._normalize_crs(gdf)
        gdf = self._strip_z(gdf)
        gdf = self._ensure_multipolygon(gdf)

        self._cache[name] = gdf.copy()
        logger.info(f"Cached {name}: {len(gdf)} features")
        return gdf

    def _read_shp(self, layer_name: str) -> gpd.GeoDataFrame:
        path = os.path.join(self.data_dir, LAYER_PATHS[layer_name])
        if not os.path.exists(path):
            raise FileNotFoundError(f"Shapefile not found: {path}")
        gdf = gpd.read_file(path)
        logger.info(f"Read {len(gdf)} features from {path}")
        return gdf

    def _fill_name_fallback(
        self, gdf: gpd.GeoDataFrame, layer_name: str
    ) -> gpd.GeoDataFrame:
        mapping = _NAME_FALLBACK.get(layer_name)
        if not mapping:
            return gdf
        name_col, fallback_col = mapping
        if name_col not in gdf.columns or fallback_col not in gdf.columns:
            return gdf
        null_mask = gdf[name_col].isna() | (gdf[name_col] == "")
        fallback_count = null_mask.sum()
        if fallback_count:
            gdf.loc[null_mask, name_col] = gdf.loc[null_mask, fallback_col]
            logger.info(
                f"Filled {fallback_count} missing names in '{name_col}' "
                f"with '{fallback_col}'"
            )
        return gdf

    def _sanitize_village_type(
        self, gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        if "JENIS_KD" not in gdf.columns:
            return gdf
        invalid_mask = gdf["JENIS_KD"].isin(_INVALID_VTYPE)
        invalid_count = invalid_mask.sum()
        if invalid_count:
            gdf.loc[invalid_mask, "JENIS_KD"] = None
            logger.info(
                f"Sanitized {invalid_count} invalid JENIS_KD values to NULL"
            )
        return gdf

    def _rename_fields(
        self, gdf: gpd.GeoDataFrame, layer_name: str
    ) -> gpd.GeoDataFrame:
        mapping = LAYER_FIELD_MAP.get(layer_name, {})
        for src, tgt in mapping.items():
            if src in gdf.columns:
                gdf = gdf.rename(columns={src: tgt})
        return gdf

    def _drop_unused(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        cols_to_drop = [c for c in gdf.columns if c not in _COLS_TO_KEEP]
        if cols_to_drop:
            gdf = gdf.drop(columns=cols_to_drop)
            logger.info(f"Dropped columns: {cols_to_drop}")
        return gdf

    def _normalize_crs(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
            logger.info("Normalized CRS to EPSG:4326")
        return gdf

    def _ensure_multipolygon(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        def to_multipolygon(geom):
            if geom is None:
                return None
            if geom.geom_type == "Polygon":
                return MultiPolygon([geom])
            if geom.geom_type == "MultiPolygon":
                return geom
            return None

        gdf.geometry = gdf.geometry.apply(to_multipolygon)
        logger.info("Ensured all geometries are MultiPolygon")
        return gdf

    def _strip_z(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        has_z = gdf.geometry.apply(lambda g: g is not None and g.has_z)
        if not has_z.any():
            logger.info("No Z dimension to strip")
            return gdf
        z_count = has_z.sum()

        def _drop_z(geom):
            return wkb.loads(wkb.dumps(geom, output_dimension=2))

        gdf.loc[has_z, "geometry"] = gdf.loc[has_z, "geometry"].apply(
            lambda g: _drop_z(g) if g is not None else g
        )
        logger.info(f"Stripped Z dimension from {z_count} geometries")
        return gdf
