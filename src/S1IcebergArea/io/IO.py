import os
import pickle
import importlib
import numpy as np
import rasterio as rio
from rasterio.mask import mask

FILE_NAME_MODEL_HH = "S1_EW_GRDM_HH_BackscatterRL_CB_v0.0.pickle"
FILE_NAME_MODEL_HV = "S1_EW_GRDM_HV_BackscatterRL_CB_v0.0.pickle"

MIN_IA = 19.6

class IO:
    def __init__(self) -> None:
        pass

    @staticmethod
    def read_raster(file, aoi=None):
        with rio.open(file) as src:
            meta = src.meta
            if aoi is None:
                data = src.read()
            else:
                data, transform = mask(src, list(aoi.to_crs(meta["crs"]).geometry), crop=True, nodata=np.nan)
                meta.update(transform=transform, height=data.shape[-2], width=data.shape[-1])
        data[:, data[-1] < MIN_IA] = np.nan  # to avoid scene edge
        return data, meta

    @staticmethod
    def write_raster(file, data, meta):
        n = 1 if len(data.shape) == 2 else 2
        meta.update(count=n, dtype=data.dtype)
        with rio.open(file, "w", **meta) as dst:
            if len(data.shape) == 2:
                dst.write(data, 1)
            else:
                dst.write(data)

    @staticmethod
    def read_model(pol):
        with importlib.resources.path("S1IcebergArea", "model") as dir_model:
            with open(os.path.join(dir_model, dict(hh=FILE_NAME_MODEL_HH, hv=FILE_NAME_MODEL_HV)[pol.lower()]), "rb") as src:
                model = pickle.load(src)
        return model

    @staticmethod
    def get_gpt_graph_file(which):
        with importlib.resources.path("S1IcebergArea", "s1_preprocessing") as dir_gpt_graphs:
            file = os.path.join(dir_gpt_graphs, "SnapGpt", "graphs", {"band_math": "band_math.xml", "calibration": "s1_radiometric_calibration.xml"}[which])
        return file
