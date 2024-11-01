import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from skimage.measure import label
from scipy.special import gammaincc
from scipy.optimize import minimize
from rasterio.features import shapes
from shapely.geometry import Polygon
from joblib import Parallel, delayed
from S1IcebergArea.s1_preprocessing.Preprocessing import Preprocessing
from S1IcebergArea.fast_moving_window import fast_edge_nanmean29, fast_edge_nanmean49

"""
CFAR implementation. Code modified froms: Laust Færch (https://github.com/LaustFaerch/cfar-object-detection)
"""


class CFAR:
    def __init__(self) -> None:
        pass

    def run_gamma(self, hh, hv, pfa, ows):
        """
        :param: hh: np.float32 (y, x) the HH channel in decibel intensities.
        :param: hv: np.float32 (y, x) the HH channel in decibel intensities.
        :param pfa: float the probability of false alarm.
        :param ows: CFAR outer window size in pixels (side length).
        """
        outliers, clutter, contrast = [], [], []
        for channel in [hh, hv]:
            prep = Preprocessing()
            channel_linear_intensity = prep.decibels_to_linear(channel)
            outliers_channel, edge_mean_channel = self._gamma(channel_linear_intensity, pfa, ows, ~np.isnan(channel_linear_intensity))  # run on linear intensities
            outliers.append(outliers_channel)
            edge_mean_db = np.float16(prep.linear_to_decibels(edge_mean_channel))
            clutter.append(edge_mean_db)  # in decibels
            contrast.append(np.float16(channel - edge_mean_db))  # both in decibels
        return np.int8(outliers), np.float16(clutter), np.float16(contrast)  # binary, decibels, decibels

    def _to_polygons(self, outliers, transform, crs):
        """
        :param: outliers np.int8 binary outliers (1=outlier, 0=no outlier).
        """
        polygons = gpd.GeoDataFrame()
        labels = label(outliers).astype(np.float32)  # float32 for shapes() method
        #logging.info("Eliminating out-of-size-range ice features")
        #logging.info("Convolution")
        #labels_convoled_3x3 = convolve(np.int8(labels != 0), np.ones((3, 3)))
        #labels[labels_convoled_3x3 < 3] = 0  # eliminate pixels with less than 2 neighbors
        #labels_convoled_3x3 = convolve(np.int8(labels != 0), np.ones((3, 3)))
        #labels[labels_convoled_3x3 < 3] = 0  # eliminate pixels with less than 2 neighbors
        #labels_convoled_3x3 = convolve(np.int8(labels != 0), np.ones((3, 3)))
        #labels[labels_convoled_3x3 < 3] = 0  # eliminate pixels with less than 2 neighbors
        #labels_convoled_3x3 = convolve(np.int8(labels != 0), np.ones((3, 3)))
        #labels[labels_convoled_3x3 < 3] = 0  # eliminate pixels with less than 2 neighbors
        #labels[labels == 0] = np.nan
        results = Parallel(n_jobs=6)(delayed(self._do_polygonize)(labels, value, transform, crs) for value in np.unique(labels[np.isfinite(labels)]))
        polygons = gpd.GeoDataFrame(pd.concat(results))
        polygons.geometry = polygons["geometry"]
        #polygons = polygons[np.bool8(polygons.area >= MINIMUM_SIZE) * np.bool8(polygons.area < MAXIMUM_SIZE)]
        polygons.crs = self.meta_s2["crs"]
        polygons.index = list(range(len(polygons)))
        polygons.index = list(range(len(polygons)))
        polygons["area"] = polygons.area
        return polygons

    def _do_polygonize(self, labels, value, transform, crs):
        polygons = gpd.GeoDataFrame()
        shapes_results = shapes(labels, mask=labels == value, connectivity=4, transform=self.meta_s2["transform"])
        for i, (s, v) in enumerate(shapes_results):
            if v != 0:
                polygons.loc[i, "geometry"] = Polygon(s["coordinates"][0])
                polygons.loc[i, "raster_val"] = v
        return polygons

    def _gamma(self, channel, pfa, ows, mask=0):
        if np.all(mask == 0):
            mask = np.ones_like(channel) > 0        
        enl = self.calc_enl(np.where(channel < np.nanmedian(channel) * 2, channel, np.nan))
        multiplier = self.get_gamma_multiplier(pfa=pfa, enl=enl)
        funs = {
            29: fast_edge_nanmean29,
            49: fast_edge_nanmean49,
            }
        if ows not in funs.keys():
            raise ValueError("OWS has to be either 29 pixels or 49 pixels.")
        inner_window_sizes = {ow: int(iw) for ow, iw in zip(funs.keys(), np.float32(list(funs.keys())) - 4)}
        edge_mean = funs[ows](channel, mask)
        Δ = (channel > (edge_mean * multiplier))
        return self._mask_edges(Δ, inner_window_sizes[ows], False), edge_mean

    def get_gamma_multiplier(self, pfa, enl):
        try:
            shape = pfa.shape
            if np.max(shape) > 1:
                multiplier = np.zeros_like(pfa)
                for pfa_value in np.unique(pfa):
                    multiplier[pfa == pfa_value] = self._find_gamma_multiplier(pfa_value, enl)
        except AttributeError:
            multiplier = self._find_gamma_multiplier(pfa, enl)
        return multiplier

    def _find_gamma_multiplier(self, pfa, L):  # Find the required multiplier for a desired PFA level numerically
        x0 = 3  # initial guess
        res = minimize(self._gamma_pfa_minimization, x0, args=(pfa, L), method="Nelder-Mead", tol=1e-6)
        # TODO: I have had some convergence issues.
        # Maybe test if using another method than 'Nelder-Mead' gives better results
        # For now, I have just added a warning
        if res.x[0] == x0:
            warnings.warn("gamma CFAR might not have converged", category=UserWarning)
        return res.x[0]

    def _gamma_pfa_minimization(self, x, pfa, L):
        return np.abs(self._gamma_pfa(x, L) - pfa)
    
    @staticmethod
    def _gamma_pfa(t, L):
        # scipy.stats.gammaincc is already regualized with 1/gamma(L)
        return gammaincc(L, t * L)

    @staticmethod
    def calc_enl(samples):
        """
        simple mom method for estimating the ENL
        theoretically only works for gamma, but are commonly used for other distributions as well
        """
        return np.nanmean(samples)**2 / np.nanstd(samples)**2

    @staticmethod
    def _mask_edges(a, N, fill=False):
        a[0:N, :] = fill
        a[:, 0:N] = fill
        a[-N:, :] = fill
        a[:, -N:] = fill
        return a    

    @staticmethod
    def _merge_touching_polygons(gdf):
        geoms = gpd.GeoSeries(gdf.geometry.buffer(0.1).unary_union.buffer(-0.1)).explode(index_parts=False)
        gdf_merged = gpd.GeoDataFrame({"geometry": list(geoms.geometry)})
        gdf_merged.geometry = gdf_merged.geometry
        gdf_merged.crs = gdf.crs
        gdf_merged.index = list(range(len(gdf_merged)))
        return gdf_merged
