import os
import pickle
import numpy as np
from rasterstats import zonal_stats
from io.IO import IO
from CFAR import CFAR
from s1_preprocessing.S1Prep import S1Prep
from s1_preprocessing.Preprocessing import Preprocessing
"""
This code runs models for iceberg area prediction from Sentinel-1 EW GRDM data (HH, HV). The models use the iceberg area initially delineated by a CFAR gamma iceberg detector, backscatter statistics, and the incidence angle in the prediction.
"""

PFA = 1e-6
OWS = 29
STATS = "mean"
FEATURES = [        
    "area",
    "hh_mean",
    "hh_background_mean",
    "hh_contrast_mean",
    "hv_mean",
    "hv_background_mean",
    "hv_contrast_mean",
    "ia_mean",
]
FILE_NAME_MODEL = "S1_EW_GRDM_BackscatterRL_CB_v0.0"

file_s1 = ""
file_icebergs = ""
dir_tmp = ""


class S1IcebergArea:
    def __init__(self, dir_tmp, file_s1) -> None:
        self.dir_tmp = dir_tmp
        self.file_s1 = file_s1
        self.file_model = os.path.join("model", FILE_NAME_MODEL)
        self.io = IO()
        self.prep = Preprocessing()
        self.icebergs = None
        self.data_s1, self.meta_s1 = None, None

    def prepare_s1(self, dir_safe, dir_out):
        """
        Prepares Sentinel-1 data for area prediction. Calibration, noise removal (HV), geocoding.
        :param: dir_safe str the directory of the .SAFE folder. Ends on .SAFE.
        :param: dir_out str the directory where the preprocessed Sentinel-1 data shall be written to.
        """
        self.file_s1 = self.prep.preprocess_s1(dir_safe, dir_out)
        
    def run_model(self):
        """
        Runs a gamma CFAR and the BackscatterRL CatBoost (CB) area model.
        """
        self.data_s1, self.meta_s1 = self.io.read_raster(self.file_s1)  # read S1 data
        cfar = CFAR()
        outliers, clutter, contrast = cfar.run_gamma(self.data_s1, PFA, OWS)  # detect outliers using gamma CFAR
        self.icebergs = cfar.to_polygons(outliers, self.meta_s1["transform"], self.meta_s1["crs"])  # delineate connected pixels as icebergs
        self._extract_backscatter_stats(clutter, contrast)  # extract backscatter, clutter, contrast, and incidence angle statistics for delineated icebergs
        features = self._reshape_features()  # prepare feature array for area prediction
        self._predict_area(features)  # predict iceberg areas using BackscatterRL CB model
        return self.icebergs  # contains CFAR area and predicted area
    
    def _extract_backscatter_stats(self, clutter, contrast):
        for i, key in enumerate(["hh", "hv", "ia"]):  # channels and incidence angle
            data = self.data_s1[i]
            stats = zonal_stats(self.icebergs, self.prep.decibels_to_linear(data) if key != "ia" else data, affine=self.meta_s1["transform"], stats=STATS, nodata=np.nan)  # calc stats in linear intensities
            for j, stat in enumerate(stats):  # individual statistics (only mean in this case)
                for stat_name, value in stat.items():
                    self.icebergs.loc[j, f"{key}_{stat_name}"] = self.prep.linear_to_decibels(value) if key != "ia" else value  # save stats in decibels
        for i, (key, data) in enumerate(zip(["clutter", "contrast"], [clutter, contrast])):
            stats = zonal_stats(self.icebergs, self.prep.decibels_to_linear(data), affine=self.meta_s1["transform"], nodata=np.nan)  # calc stats in linear intensities
            for j, stat in enumerate(stats):  # individual stats (only mean in this case)
                for stat_name, value in stat.items():
                    self.icebergs.loc[j, f"{key}_{stat_name}"] = self.prep.linear_to_decibels(value)  # save stats in decibels

    def _predict_area(self, features):
        with open(self.file_model) as src:
            model = pickle.load(src)
        prediction = model.predict(features)  # predict root length
        self.icebergs["area_predicted"] = np.sqrt(prediction)  # root length to area
        self.icebergs["area_cfar"] = self.icebergs["area"]  # original CFAR-delineated area
        del self.icebergs["area"]  # delete this to be clear about original of area

    def _reshape_features(self):
        features = np.float32([self.icebergs[feature] for feature in FEATURES]).swapaxes(0, 1)
        area_idx = np.argmax(FEATURES == "area")
        features[:, area_idx] = np.sqrt(features[:, area_idx])  # root length goes into model (square root of area)
        return features


if __name__ == "__main__":
    iceberg_area = S1IcebergArea(dir_tmp, file_s1)
    iceberg_area.run_model()
