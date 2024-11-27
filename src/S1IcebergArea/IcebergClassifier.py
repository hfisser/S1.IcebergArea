import os
import scipy
import numpy as np
import pandas as pd
import rasterio as rio
import geopandas as gpd
from glob import glob
from scipy.stats import chi2
from scipy.spatial import distance
from joblib import Parallel, delayed

FILE_TRAINING_HH = "/home/henrik/Output/icebergs/validation/matches/matches_merged_hh_1e-06_outer_window49.csv"
FILE_TRAINING_HV = FILE_TRAINING_HH.replace("hh", "hv")

FEATURE_NAMES = [
    "hh_mean",
    "hv_mean",
    "ia_mean"
]

THRESHOLD_BACKSCATTER = 0.05
THRESHOLD_PERIMETER_INDEX = 0.005
THRESHOLD_LENGTH_ROOT_LENGTH_RATIO = 0.005

PERIMETER_INDEX_STATS = dict(
    hh=(0.6872505214102617, 0.09071944729743565),
    hv=(0.6746545582476059, 0.09212859328629924)
)
LENGTH_ROOT_LENGTH_RATIO_STATS = dict(
    hh=(1.7762282304810593, 0.1682613392370232),
    hv=(1.7996105378415033, 0.17163124666311017)
)


class IcebergClassifier:
    def __init__(self) -> None:
        self.hh_iceberg_reference = pd.read_csv(FILE_TRAINING_HH)
        self.hv_iceberg_reference = pd.read_csv(FILE_TRAINING_HV)
        self.features = dict(hh=self._reshape_features("hh"), hv=self._reshape_features("hv"))
        #self.cov_matrix = dict(hh=self._calc_cov_matrix("hh"), hv=self._calc_cov_matrix("hv"))
    
    def predict(self, icebergs, detection_channel):
        #data_reference = self.hh_iceberg_reference if detection_channel == "hh" else self.hv_iceberg_reference
        #perimeter_index = np.float32(data_reference["perimeter_index_s1"])
        features = self.features[detection_channel]
        iceberg_data = np.float32([icebergs[feature_name] for feature_name in FEATURE_NAMES]).swapaxes(0, 1)
        md_perimeter_index = np.float32((icebergs["perimeter_index"] - PERIMETER_INDEX_STATS[detection_channel][0]) / PERIMETER_INDEX_STATS[detection_channel][1])
        md_perimeter_index = np.clip(md_perimeter_index, -1000, 0)
        md_length_root_length_ratio = np.abs(icebergs["length_root_length_ratio"] - LENGTH_ROOT_LENGTH_RATIO_STATS[detection_channel][0]) / LENGTH_ROOT_LENGTH_RATIO_STATS[detection_channel][1]
        icebergs[f"md_perimeter_index_{detection_channel}"] = md_perimeter_index
        icebergs[f"sf_perimeter_index_{detection_channel}"] = chi2.sf(md_perimeter_index ** 2, 1)
        icebergs[f"md_length_root_length_ratio_{detection_channel}"] = md_length_root_length_ratio
        icebergs[f"sf_length_root_length_ratio_{detection_channel}"] = chi2.sf(md_length_root_length_ratio ** 2, 1)
        perimeter_index_condition = np.int8(icebergs[f"sf_perimeter_index_{detection_channel}"] >= THRESHOLD_PERIMETER_INDEX)
        length_root_length_ratio_condition = np.int8(icebergs[f"sf_length_root_length_ratio_{detection_channel}"] >= THRESHOLD_LENGTH_ROOT_LENGTH_RATIO)
        col_md = f"md_{detection_channel}"
        col_sf = col_md.replace("md", "sf")
        icebergs[col_md] = Parallel(n_jobs=6)(delayed(self._mahalanobis_distance)(iceberg_data[i], features, detection_channel) for i in range(iceberg_data.shape[0]))
        icebergs[col_sf] = chi2.sf(icebergs[col_md] ** 2, 1)
        icebergs[f"is_iceberg_{detection_channel}"] = np.int8(icebergs[col_sf] >= THRESHOLD_BACKSCATTER) * perimeter_index_condition * length_root_length_ratio_condition
        return icebergs

    def _mahalanobis_distance(self, iceberg, features, detection_channel):
        idx = 0 if detection_channel == "hh" else 1
        ia = features[:, -1]
        features = features[np.bool8(ia >= iceberg[-1] - 2) * np.bool8(ia < iceberg[-1] + 2)]
        features = features[:, :-1]
        iceberg = iceberg[:-1]
        md = (iceberg[idx] - np.mean(features[:, idx])) / np.std(features[:, idx])
        return np.clip(md, -1000, 0)
        #idx_hh, idx_hv = FEATURE_NAMES.index("hh_mean"), FEATURE_NAMES.index("hv_mean")
        #iceberg[idx_hh] = self._to_linear_intensities(iceberg[idx_hh])
        #iceberg[idx_hv] = self._to_linear_intensities(iceberg[idx_hv])
        #return distance.mahalanobis(iceberg, np.mean(features, 0), self.cov_matrix[detection_channel])

    def _reshape_features(self, detection_channel):
        data = dict(hh=self.hh_iceberg_reference, hv=self.hv_iceberg_reference)[detection_channel]
        features = np.vstack([np.float32(data["_".join([feature_name, "s1"])]) for feature_name in FEATURE_NAMES]).swapaxes(0, 1)
        idx_hh, idx_hv = FEATURE_NAMES.index("hh_mean"), FEATURE_NAMES.index("hv_mean")
        #features[:, idx_hh] = self._to_linear_intensities(features[:, idx_hh])
        #features[:, idx_hv] = self._to_linear_intensities(features[:, idx_hv])
        return features
    
    def _calc_cov_matrix(self, pol):
        return scipy.linalg.inv(np.cov(self.features[pol][:, :-1].T))

    @staticmethod
    def _to_linear_intensities(values):
        return np.power(10, np.divide(values, 10))     



if __name__ == "__main__":
    for pol in ["hh", "hv"]:
        file_icebergs = f"/media/henrik/DATA/icebergs_{pol}_tmp.gpkg"
        icebergs = gpd.read_file(file_icebergs)
        training = IcebergClassifier()
        training.predict(icebergs, pol).to_file(file_icebergs.replace(".gpkg", "_prediction.gpkg"))

