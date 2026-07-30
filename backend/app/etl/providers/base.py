from abc import ABC, abstractmethod

import geopandas as gpd


class DatasetProvider(ABC):
    @abstractmethod
    def read_layer(self, layer_cfg: dict) -> gpd.GeoDataFrame:
        pass
