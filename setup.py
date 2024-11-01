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
    description = ("Package for predicting iceberg above-waterline areas from Sentinel-1 data."),
    license = "Tbd",
    long_description=read("README.md"),
    install_requires = [
        "catboost==1.2.5",
        "fiona==1.9.6",
        "geopandas==0.12.2",
        "ipython",
        "loguru",
        "lxml",
        "netCDF4==1.5.7",
        "numba==0.56.4",
        "numpy==1.23.5",
        "rasterio==1.2.10",
        "rasterstats==0.20.0",
        "scikit-image==0.19.3",
        "scipy==1.10.0",
    ],
    packages = find_packages(where="src"),
    package_dir = {"": "src"},
    package_data = {"": ["*.pickle", os.path.join("SnapGpt", "graphs", "*.xml")]},
    entry_points = {
        "console_scripts": [
        ]
    },
    include_package_data=True,
)
