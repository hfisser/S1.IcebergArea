import os
import pickle
import importlib
import rasterio as rio

FILE_NAME_MODEL_HH = "S1_EW_GRDM_HH_BackscatterRL_CB_v0.0.pickle"
FILE_NAME_MODEL_HV = "S1_EW_GRDM_HV_BackscatterRL_CB_v0.0.pickle"


class IO:
    def __init__(self) -> None:
        pass

    @staticmethod
    def read_raster(file):
        with rio.open(file) as src:
            data, meta = src.read(), src.meta
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
            with open(os.path.join(dir_model, dict(hh=FILE_NAME_MODEL_HH, hv=FILE_NAME_MODEL_HV))[pol.lower()], "rb") as src:
                model = pickle.load(src)
                print(model)

    @staticmethod
    def get_gpt_graph_file(which):
        with importlib.resources.path("S1IcebergArea", "s1_preprocessing") as dir_gpt_graphs:
            file = os.path.join(dir_gpt_graphs, "SnapGpt", "graphs", {"band_math": "band_math.xml", "calibration": "s1_ratiometric_calibration.xml"}[which])
        return file
