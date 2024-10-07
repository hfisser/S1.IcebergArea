import os
import rasterio as rio


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
