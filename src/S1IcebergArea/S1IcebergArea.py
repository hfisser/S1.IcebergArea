import numpy as np
from S1IcebergArea.io.IO import IO
from rasterstats import zonal_stats
from S1IcebergArea.CFAR import CFAR
from S1IcebergArea.s1_preprocessing.Preprocessing import Preprocessing

"""
This code runs models for iceberg area prediction from Sentinel-1 EW GRDM data (HH, HV). The models use the iceberg area initially delineated by a CFAR gamma iceberg detector, backscatter statistics, and the incidence angle in the prediction.
"""

PFA = 1e-6
OWS = 29
STATS = "mean"
FEATURES = [        
    "area",
    "hh_mean",
    "hh_clutter_mean",
    "hh_contrast_mean",
    "hv_mean",
    "hv_clutter_mean",
    "hv_contrast_mean",
    "ia_mean",
]

file_s1 = ""
file_icebergs = ""
dir_tmp = ""


class S1IcebergArea:
    def __init__(self) -> None:
        self.io = IO()
        self.prep = Preprocessing()
        self.file_s1 = None
        self.icebergs = None
        self.data_s1, self.meta_s1 = None, None
        
    def prepare_s1(self, dir_safe, dir_out):
        """
        Prepares Sentinel-1 data for area prediction. Calibration, noise removal (HV), geocoding.
        :param: dir_safe str the directory of the .SAFE folder. Ends on .SAFE.
        :param: dir_out str the directory where the preprocessed Sentinel-1 data shall be written to.
        """
        self.file_s1 = self.prep.preprocess_s1(dir_safe, dir_out)
        return self.file_s1
        
    def run_model(self, file_s1=None, aoi=None):
        """
        Runs a gamma CFAR and the BackscatterRL CatBoost (CB) area model.
        :param: (optional) file_s1 str file path of the Sentinel-1 EW GRDM data as output of prepare_s1().
        :param: (optional) aoi GeoDataFrame with one or several geometries delineating the area of interest in the Sentinel-1 data.
        """
        self.file_s1 = file_s1 if file_s1 is not None else self.file_s1
        if self.file_s1 is None:
            raise ValueError("Please provide a Sentinel-1 file as file_s1 argument and/or run prepare_s1(), which will store the file_s1 information.")
        self.data_s1, self.meta_s1 = self.io.read_raster(self.file_s1, aoi)  # read S1 data
        cfar = CFAR()
        outliers, clutter, contrast = cfar.run_gamma(self.data_s1[0], self.data_s1[1], PFA, OWS)  # detect outliers using gamma CFAR
        icebergs_both_channels = dict()
        for i, pol in enumerate(["hh", "hv"]):
            self.icebergs = cfar._to_polygons(outliers[i], self.meta_s1["transform"], self.meta_s1["crs"])  # delineate connected pixels as icebergs
            self.icebergs = self.icebergs[self.icebergs["area"] > 45 ** 2]  # drop single pixel detections (45 instead of 40 to allow for potential inaccuracies in polygon area)
            self._extract_backscatter_stats(clutter, contrast)  # for channels extract backscatter, clutter, contrast, and incidence angle statistics for delineated icebergs
            features = self._reshape_features()  # prepare feature array for area prediction
            self._predict_area(features, pol)  # predict iceberg areas using BackscatterRL CB model
            icebergs_both_channels[pol] = self.icebergs.copy()
        return icebergs_both_channels  # contains CFAR area and predicted area, one GeoDataFrame per channel
    
    def _extract_backscatter_stats(self, clutter, contrast):
        for i, key in enumerate(["hh", "hv", "ia"]):  # channels and incidence angle
            data = self.data_s1[i]
            stats = zonal_stats(self.icebergs, self.prep.decibels_to_linear(data) if key != "ia" else data, affine=self.meta_s1["transform"], stats=STATS, nodata=np.nan)  # calc stats in linear intensities
            for j, stat in enumerate(stats):  # individual statistics (only mean in this case)
                for stat_name, value in stat.items():
                    self.icebergs.loc[j, f"{key}_{stat_name}"] = self.prep.linear_to_decibels(value) if key != "ia" else value  # save stats in decibels
        for i, (key, data) in enumerate(zip(["clutter", "contrast"], [clutter, contrast])):
            for pol_idx, pol in enumerate(["hh", "hv"]):
                stats = zonal_stats(self.icebergs, self.prep.decibels_to_linear(data[pol_idx]), affine=self.meta_s1["transform"], stats=STATS, nodata=np.nan)  # calc stats in linear intensities
                for j, stat in enumerate(stats):  # individual stats (only mean in this case)
                    for stat_name, value in stat.items():
                        self.icebergs.loc[j, f"{pol}_{key}_{stat_name}"] = self.prep.linear_to_decibels(value)  # save stats in decibels

    def _predict_area(self, features, pol):
        model = self.io.read_model(pol)
        prediction = model.predict(features)  # predict root length
        self.icebergs["area_BackscatterRL_CB_{}".format(pol.upper())] = prediction ** 2  # root length to area
        self.icebergs["area_CFAR"] = self.icebergs["area"]  # original CFAR-delineated area
        del self.icebergs["area"]  # delete this to be clear about original of area

    def _reshape_features(self):
        features = np.float32([self.icebergs[feature] for feature in FEATURES]).swapaxes(0, 1)
        area_idx = FEATURES.index("area")
        features[:, area_idx] = np.sqrt(features[:, area_idx])  # root length goes into model (square root of area)
        return features
