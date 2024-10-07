import warnings
import numpy as np
import geopandas as gpd
from skimage.measure import label
from scipy.special import gammaincc
from scipy.optimize import minimize
from rasterio.features import shapes
from shapely.geometry import Polygon
from src.s1_preprocessing.Preprocessing import Preprocessing
from fast_moving_window import fast_edge_nanmean29, fast_edge_nanmean49

"""
CFAR implementation. Code modified froms: Laust Færch (https://github.com/LaustFaerch/cfar-object-detection)
"""


class CFAR:
    def __init__(self) -> None:
        pass

    def run_gamma(self, channel, pfa, ows):
        """
        :param: channel: np.float32 (y, x) the channel.
        :param pfa: float the probability of false alarm.
        :param ows: CFAR outer window size in pixels (side length).
        """
        prep = Preprocessing()
        channel_linear_intensity = prep.decibels_to_linear(channel)
        outliers, edge_mean = self._gamma(channel_linear_intensity, pfa, ows, ~np.isnan(channel_linear_intensity))  # run on linear intensities
        edge_mean_db = np.float16(prep.linear_to_decibels(edge_mean))
        contrast = np.float16(channel - edge_mean_db)  # both in decibels
        return np.int8(outliers), edge_mean_db, contrast  # binary, decibels, decibels

    def to_polygons(self, outliers, transform, crs):
        """
        :param: outliers np.int8 binary outliers (1=outlier, 0=no outlier).
        :param: transform Affine transform corresponding to the outliers, from rasterio meta.
        :param: crs str EPSG code (e.g. 'EPSG:3996') specifies the coordinate reference system.
        """
        polygons = gpd.GeoDataFrame()
        label_objects = label(outliers).astype(np.float32)  # float32 for shapes() method
        results = ({"properties": {"raster_val": v}, "geometry": s}
        for _, (s, v) in enumerate(shapes(label_objects, transform=transform)))
        for i, polygon in enumerate(results):
            polygons.loc[i, "geometry"] = Polygon(polygon["geometry"]["coordinates"][0])
            polygons.loc[i, "raster_val"] = polygon["properties"]["raster_val"]
        polygons.geometry = polygons["geometry"]
        polygons = polygons[polygons.area < np.nanmax(polygons.area)]  # eliminate bounding box (always created)
        polygons.crs = crs
        polygons.index = list(range(len(polygons)))
        polygons["area"] = polygons.area

        polygons = polygons[polygons.type == "Polygon"]  # no MultiPolygons
        polygons = polygons[np.add(np.int8(~polygons.is_empty), np.int8(polygons.is_valid)) == 2]
        polygons.index = list(range(len(polygons)))
        if len(polygons) > 0:
            polygons = self._merge_touching_polygons(polygons)
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
    def merge_touching_polygons(gdf):
        geoms = gpd.GeoSeries(gdf.geometry.buffer(0.1).unary_union.buffer(-0.1)).explode(index_parts=False)
        gdf_merged = gpd.GeoDataFrame({"geometry": list(geoms.geometry)})
        gdf_merged.geometry = gdf_merged.geometry
        gdf_merged.crs = gdf.crs
        gdf_merged.index = list(range(len(gdf_merged)))
        return gdf_merged
