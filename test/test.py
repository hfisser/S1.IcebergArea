import os
import geopandas as gpd
from S1IcebergArea.S1IcebergArea import S1IcebergArea

dir_safe = "/media/henrik/DATA/S1A_EW_GRDM_1SDH_20240917T191651_20240917T191725_055709_06CDC8_7EF4.SAFE"
aoi = gpd.read_file("/media/henrik/DATA/aoi_tmp.gpkg")


def test():
    iceberg_area = S1IcebergArea()
    iceberg_area.prepare_s1(dir_safe, os.path.dirname(dir_safe))
    icebergs = iceberg_area.run_model(aoi=aoi)
    icebergs["hh"].to_file(os.path.join(os.path.dirname(dir_safe), "icebergs_hh_tmp.gpkg"))
    icebergs["hv"].to_file(os.path.join(os.path.dirname(dir_safe), "icebergs_hv_tmp.gpkg"))


if __name__ == "__main__":
    test()
