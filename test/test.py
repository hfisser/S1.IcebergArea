import os
import geopandas as gpd
from glob import glob
from datetime import datetime
from S1IcebergArea.S1IcebergArea import S1IcebergArea



file_s1 = "/media/henrik/DATA/raster/s1/25WER/S1A_EW_GRDM_1SDH_20160823T192418_20160823T192518_012732_01408B_805A_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif"
file_s1 = "/media/henrik/DATA/raster/s1/25WER/S1B_EW_GRDM_1SDH_20190801T090215_20190801T090251_017390_020B35_A5A0_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif"

files_s1 = [
    "/media/henrik/DATA/raster/s1/25WER/S1A_EW_GRDM_1SDH_20160823T192418_20160823T192518_012732_01408B_805A_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif",
    "/media/henrik/DATA/raster/s1/25WER/S1B_EW_GRDM_1SDH_20190801T090215_20190801T090251_017390_020B35_A5A0_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif",
    "/media/henrik/DATA/raster/s1/25WER/S1B_EW_GRDM_1SDH_20200820T192357_20200820T192447_023011_02BAF8_3BBD_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif"
]
#files_s1 = ["/media/henrik/DATA/raster/s1/25WER/S1B_EW_GRDM_1SDH_20200820T192357_20200820T192447_023011_02BAF8_3BBD_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif"]
#files_s1 = ["/media/henrik/DATA/raster/s1/25WER/S1B_EW_GRDM_1SDH_20200825T193209_20200825T193259_023084_02BD45_28C4_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue.tif"]

files_s1 = [files_s1[-1]]


def test(file_s1):
    file_aoi = glob(os.path.join("/home/henrik/Output/icebergs/validation", os.path.basename(os.path.dirname(file_s1)), "ocean_buffered_300*{}.gpkg".format(os.path.basename(file_s1).split(".")[0])))[0]
    #file_aoi = "/media/henrik/DATA/aoi.gpkg"  ########
    aoi = gpd.read_file(file_aoi)
    iceberg_area = S1IcebergArea()
    #iceberg_area.prepare_s1(dir_safe, os.path.dirname(dir_safe))
    t0 = datetime.now()
    icebergs = iceberg_area.run_model(file_s1=file_s1, aoi=aoi)
    suffix = os.path.basename(file_s1).split(".")[0]
    icebergs["hh"].to_file(f"/media/henrik/DATA/icebergs_hh_{suffix}.gpkg")
    icebergs["hv"].to_file(f"/media/henrik/DATA/icebergs_hv_{suffix}.gpkg")
    icebergs["hh_hv_merged"].to_file(f"/media/henrik/DATA/icebergs_hh_hv_merged_{suffix}.gpkg")
    print("Elapsed:", (datetime.now() - t0).total_seconds() / 60)


if __name__ == "__main__":
    for file_s1 in files_s1:
        test(file_s1)
