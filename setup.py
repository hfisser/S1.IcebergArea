import os
from setuptools import setup, find_packages

def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()

setup(
    name = "S1.IcebergArea",
    version = "0.0.0",
    author = "Henrik Fisser",
    author_email = "henrik.fisser@uit.no",
    description = ("Package for predicting iceberg above-waterline areas for Sentinel-1 data."),
    license = "Tbd",
    long_description=read("README.md"),
    install_requires = [
        "numpy",
        "scipy",
        "scikit-learn",
        "scikit-image",
        "lxml",
        "ipython",
        "loguru",
        "netCDF4",
        "rasterstats",
        "rasterio",
        "geopandas",
        "scikit-image",
        "numba",
        "catboost"
    ],
    packages = find_packages(where="src"),
    package_dir = {"": "src"},
    package_data = {"": ["*.pickle", "*.xml"]},
    entry_points = {
        "console_scripts": [
        ]
    },
    include_package_data=True,
)
