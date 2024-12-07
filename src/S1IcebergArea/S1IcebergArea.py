
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from S1IcebergArea.io.IO import IO
from rasterstats import zonal_stats
from S1IcebergArea.CFAR import CFAR
from joblib import Parallel, delayed
from shapely.geometry import LineString
from S1IcebergArea.IcebergClassifier import IcebergClassifier
from S1IcebergArea.s1_preprocessing.Preprocessing import Preprocessing

"""
This code runs models for iceberg area prediction from Sentinel-1 EW GRDM data (HH, HV). The models use the iceberg area initially delineated by a CFAR gamma iceberg detector, backscatter statistics, and the incidence angle in the prediction.
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-3s %(message)s")

N_JOBS = 4
POLARIZATIONS = ["hh", "hv"]
PFA = 1e-6
OWS = 49
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
        logging.info("Reading S1 data")
        self.data_s1, self.meta_s1 = self.io.read_raster(self.file_s1, aoi)  # read S1 data
        cfar = CFAR()
        logging.info("Running CFAR")
        outliers, clutter, contrast = cfar.run_gamma(self.data_s1[1], self.data_s1[0], PFA, OWS)  # detect outliers using gamma CFAR
        icebergs_both_channels = dict()
        for i, pol in enumerate(POLARIZATIONS):
            pol_upper = pol.upper()
            self.icebergs = cfar._to_polygons(outliers[i], self.meta_s1["transform"], self.meta_s1["crs"])  # delineate connected pixels as icebergs
            if len(self.icebergs) == 0:
                continue
            self.icebergs = self.icebergs[self.icebergs["area"] >= 45 ** 2]  # drop single pixel detections (45 instead of 40 to allow for potential inaccuracies in polygon area)
            self.icebergs.index = list(range(len(self.icebergs)))
            logging.info(f"{pol_upper} - Extracting statistics")
            self._extract_backscatter_stats(clutter, contrast)  # for channels extract backscatter, clutter, contrast, and incidence angle statistics for delineated icebergs
            logging.info(f"{pol_upper} - Predicting area")
            features = self._reshape_features()  # prepare feature array for area prediction
            self._predict_area(features, pol)  # predict iceberg areas using BackscatterRL CB model
            self.icebergs["perimeter_index"] = self._calc_perimeter_index(self.icebergs.geometry)
            self.icebergs["length"] = Parallel(n_jobs=N_JOBS)(delayed(self._calculate_length)(polygon) for polygon in self.icebergs.geometry)
            self.icebergs["length_root_length_ratio"] = np.float32(self.icebergs["length"] / np.sqrt(self.icebergs.area))
            logging.info(f"{pol_upper} - Classifying icebergs")
            classifier = IcebergClassifier()     
            icebergs_both_channels[pol] = classifier.predict(self.icebergs, pol)
        logging.info("Merging channels")
        if len(icebergs_both_channels) > 0:
            icebergs_both_channels["hh_hv_merged"] = self._merge_channels(icebergs_both_channels)
        #icebergs_both_channels["hh_hv_merged"] = self._calculate_synthesized_areas(icebergs_both_channels["hh_hv_merged"])
        logging.info("Finished S1 iceberg detection and area retrieval")
        return icebergs_both_channels

    def _calculate_synthesized_areas(self, icebergs):   
        areas_s1 = np.float32(icebergs["AREA_BACKSCATTERRL_CB"])     
        ratio = np.clip(np.float32(np.sqrt(areas_s1) / 440 * 100) ** 2 / 10000, 0, 1)
        icebergs["AREA_SYN"] = (1 - ratio) * areas_s1 + ratio * np.float32(icebergs["AREA_CFAR"])
        return icebergs

    def _merge_channels(self, icebergs_both_channels):           
        col_area_hh = "area_BackscatterRL_CB_HH"
        col_area_hv = col_area_hh.replace("HH", "HV")
        col_area_final = col_area_hh.replace("_HH", "").upper()
        col_area_cfar_final = "AREA_CFAR"
        try:
            hh = icebergs_both_channels["hh"]
        except KeyError:
            hh = None
        try:
            hv = icebergs_both_channels["hv"]
        except KeyError:
            hv = None
        if any([hh is None, hv is None]):
            pol = "hh" if hv is None else "hv"
            concat = hh if pol == "hh" else hv
            concat[col_area_cfar_final] = concat[f"area_CFAR_{pol}"]
            concat[col_area_final] = concat[col_area_hh if pol == "hh" else col_area_hv]
            concat["is_iceberg"] = concat[f"is_iceberg_{pol}"]
            concat.rename(columns={"sf": "sf_backscatter"}, inplace=True)
            for col in concat:
                if col[-3:] == f"_{pol}":
                    concat.rename(columns={col: col[:-3]}, inplace=True)
            concat["DETECTION_CHANNEL"] = pol.upper()
        else:
            for i, row_hh in hh.iterrows():
                intersecting_idxs, intersecting_areas = [], []
                for j, row_hv in hv.iterrows():
                    if row_hh["geometry"].buffer(20).intersects(row_hv["geometry"]):
                        intersecting_idxs.append(j)
                        intersecting_areas.append(row_hv[f"area_CFAR"])
                if len(intersecting_areas) == 0:
                    continue
                intersecting_idxs = np.int64(intersecting_idxs)
                if np.nanmax(intersecting_areas) > row_hh["area_CFAR"]:
                    for idx in intersecting_idxs[intersecting_idxs != intersecting_idxs[np.argmax(intersecting_areas)]]:
                        hv.drop(index=idx, inplace=True)
                    hh.drop(index=i, inplace=True)
                else:
                    for idx in intersecting_idxs:
                        hv.drop(index=idx, inplace=True)
            hh["DETECTION_CHANNEL"] = "HH"
            hv["DETECTION_CHANNEL"] = "HV"
            for col in hh:
                if col[-3:].lower() == "_hh":
                    hh.rename(columns={col: col[:-3]}, inplace=True)
            for col in hv:
                if col[-3:].lower() == "_hv":
                    hv.rename(columns={col: col[:-3]}, inplace=True)
            hh.rename(columns={"area_BackscatterRL_CB": col_area_final}, inplace=True)
            hv.rename(columns={"area_BackscatterRL_CB": col_area_final}, inplace=True)
            concat = gpd.GeoDataFrame(pd.concat([hh, hv]))
            concat.rename(columns={"sf": "sf_backscatter"}, inplace=True)
            concat.geometry = concat["geometry"]
            concat.crs = hh.crs
            concat.index = list(range(len(concat)))
            concat.rename(columns={"area_CFAR": col_area_cfar_final}, inplace=True)
        #condition = concat["AREA_CFAR"] >= 36100
        #concat.loc[condition, "AREA"] = concat["AREA_CFAR"]
        #concat.loc[~condition, "AREA"] = concat[col_area_final]
        concat.rename(columns={"md": "md_backscatter"}, inplace=True)
        return concat
       
    def _extract_backscatter_stats(self, clutter, contrast):
        channels_data_order = ["hv", "hh", "ia"]
        stats_list = Parallel(n_jobs=N_JOBS)(delayed(self._do_extract_statistics)(self.data_s1[i], channel) for i, channel in enumerate(channels_data_order))  # reverted order!
        for key, stats in zip(channels_data_order, stats_list):
            self.icebergs[f"{key}_mean"] = np.float32(self.prep.linear_to_decibels(stats["mean"]) if key != "ia" else stats["mean"])
        for key, data in zip(["clutter", "contrast"], [clutter, contrast]):
            stats_list = Parallel(n_jobs=N_JOBS)(delayed(self._do_extract_statistics)(data[i], pol) for i, pol in enumerate(POLARIZATIONS))
            for pol, stats in zip(POLARIZATIONS, stats_list):
                self.icebergs[f"{pol}_{key}_mean"] = np.float32(self.prep.linear_to_decibels(stats["mean"]))

    def _do_extract_statistics(self, data, channel):
        stats_df = pd.DataFrame(zonal_stats(self.icebergs, self.prep.decibels_to_linear(data) if channel != "ia" else data, affine=self.meta_s1["transform"], stats=STATS, nodata=np.nan))
        return stats_df

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

    @staticmethod
    def _calculate_length(polygon):
        polygon = polygon.simplify(20)
        line_lengths = []
        for p in polygon.exterior.coords:
            for p1 in polygon.exterior.coords:
                line_lengths.append(LineString([p, p1]).length)
        return np.nanmax(line_lengths)

    @staticmethod
    def _calc_perimeter_index(polygons):
        return (2 * np.sqrt(np.pi * polygons.area)) / polygons.exterior.length

    @staticmethod
    def _add_polarization_to_column(df, pol):
        for col in df:
            if "index_r" in col or "index_l" in col:
                del df[col]
            if col[-2:].lower() != pol and col != "geometry":
                df.rename(columns={col: "_".join([col, pol])}, inplace=True)
        return df
