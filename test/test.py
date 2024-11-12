import os
import geopandas as gpd
from glob import glob
from S1IcebergArea.S1IcebergArea import S1IcebergArea

file_s1 = "/media/henrik/DATA/raster/s1/25WER/S1A_EW_GRDM_1SDH_20240824T191650_20240824T191725_055359_06C050_7794_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif"
file_aoi = glob(os.path.join("/home/henrik/Output/icebergs/validation", os.path.basename(os.path.dirname(file_s1)), "ocean_buffered_300*{}.gpkg".format(os.path.basename(file_s1).split(".")[0])))[0]
aoi = gpd.read_file(file_aoi)


def test():
    iceberg_area = S1IcebergArea()
    #iceberg_area.prepare_s1(dir_safe, os.path.dirname(dir_safe))
    icebergs = iceberg_area.run_model(file_s1=file_s1, aoi=aoi)
    icebergs["hh"].to_file("/media/henrik/DATA/icebergs_hh.gpkg")
    icebergs["hv"].to_file("/media/henrik/DATA/icebergs_hv.gpkg")


if __name__ == "__main__":
    test()
