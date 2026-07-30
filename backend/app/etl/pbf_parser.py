import logging
from typing import Optional

import geopandas as gpd
import pyrosm

logger = logging.getLogger(__name__)

OSM_TAG_FILTERS = {
    "School": {"amenity": ["school", "university", "college"]},
    "Hospital": {"amenity": ["hospital"]},
    "Clinic": {"amenity": ["clinic", "doctors"]},
    "BusStop": {"highway": ["bus_stop"], "amenity": ["bus_station"]},
    "Park": {"leisure": ["park", "garden", "playground"]},
}


def parse_pbf(
    pbf_path: str,
    facility_types: Optional[list[str]] = None,
    bounding_box: Optional[tuple[float, float, float, float]] = None,
) -> gpd.GeoDataFrame:
    if facility_types is None:
        facility_types = list(OSM_TAG_FILTERS.keys())
    else:
        invalid = set(facility_types) - set(OSM_TAG_FILTERS.keys())
        if invalid:
            raise ValueError(f"Unknown facility types: {invalid}")

    osm = pyrosm.OSM(pbf_path, engine="out_of_core", workers=1)
    frames = []

    for ftype in facility_types:
        tag_filter = OSM_TAG_FILTERS[ftype]
        gdf = osm.get_pois(custom_filter=tag_filter)
        if gdf is None or len(gdf) == 0:
            logger.info(f"{ftype}: 0 features found")
            continue
        gdf = gdf.copy()
        gdf["facility_type"] = ftype
        frames.append(gdf)
        logger.info(
            f"{ftype}: {len(gdf)} features extracted"
        )

    if not frames:
        return gpd.GeoDataFrame({"geometry": []}, crs="EPSG:4326")

    result = gpd.pd.concat(frames, ignore_index=True)
    if bounding_box:
        result = result.cx[
            bounding_box[0] : bounding_box[2],
            bounding_box[1] : bounding_box[3],
        ]
    return result
