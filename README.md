# S1.IcebergArea
Predict backscatter-sensitive iceberg above-waterline areas from Sentinel-1 extra-wide (EW) swath data.

### Citation
Henrik Fisser, Anthony P. Doulgeris, Wolfgang Dierking,
Backscatter-sensitive retrieval of iceberg areas from Sentinel-1 Extra Wide Swath SAR data,
Remote Sensing of Environment, Volume 331, 2025, 115042, ISSN 0034-4257,
https://doi.org/10.1016/j.rse.2025.115042.

### Installation

#### Requirement
You need a [SNAP](https://step.esa.int/main/download/snap-download/) installation and the path to the graph processing tool (GPT) has to be added to the system path. SNAP normally does this for you during installation. Check if GPT is accessible on the command line:
```shell
gpt -h
```
Then install dependencies and the S1.IcebergArea package in an Anaconda environment:

```shell
conda env create -f environment.yml  # conda environment, install dependencies needed for Sentinel1Denoised
conda activate s1icebergarea  # activate it
pip install https://github.com/nansencenter/sentinel1denoised/archive/v1.4.0.tar.gz  # install Sentinel1Denoised package for noise correction in HV channel
pip install ...  # install S1.IcebergArea package with its dependencies
```
### Example
```python
import os
import geopandas as gpd
from S1IcebergArea.S1IcebergArea import S1IcebergArea

dir_safe = "/my/s1_data/S1A_EW_GRDM_1SDH_20240917T191651_20240917T191725_055709_06CDC8_7EF4.SAFE"  # unzipped
aoi = gpd.read_file("/my/aois/aoi.gpkg")
s1_iceberg_area = S1IcebergArea()  # initialize S1IcebergArea class
s1_iceberg_area.prepare_s1(dir_safe, os.path.dirname(dir_safe))  # run calibration, noise removal
icebergs = s1_iceberg_area.run_model(aoi=aoi)  # run area model
```
### Data
Sentinel-1 EW ground-range detected medium resolution (GRDM) data, HH and HV channel.

### Output
A dictionary holding one geopandas GeoDataFrame per polarization channel. The GeoDataFrames contain the delineated iceberg outlines, backscatter statistics, the CFAR iceberg area ("area_CFAR"), and the predicted iceberg area ("area_BackscatterRL_CB").

### Algorithm
The algorithm has been developed and tested for icebergs in open water. The algorithm predicts iceberg areas based on backscatter statistics of icebergs. The implementation in this package follows three steps:
1. Preprocessing with calibration, geocoding, noise removal (HV).
2. CFAR iceberg delineation, using a CFAR gamma detector with a 10<sup>-6</sup> probability of false alarm, a 29-pixel outer window size, and a 21-pixel guard window size. CFAR runs separately for the HH channel, and the HV channel.
3. Iceberg area prediction, using the backscatter-sensitive iceberg area model (*BackscatterRL* CatBoost model). The model runs separately for the HH channel, and the HV channel.

### Background
Icebergs appear as strong reflectors in synthetic aperture radar (SAR) data. In a varying surrounding *ocean clutter*, CFAR algorithms detect icebergs as outliers. A connected set of outlier pixel is grouped as an iceberg with an area. However, these CFAR-based iceberg areas exhibit considerable errors, as they inherit variations in the ocean clutter, and in the iceberg backscatter, along with effects of the spatial resolution. The *BackscatterRL* CatBoost models are aware of these variations. The models were trained end evaluated with reference to Sentinel-2 iceberg areas in several hundred acquisitions across the Arctic in the years 2016-2023 from May to September. 

### Credits
Besides standard Python packages, we use code from three packages:
1. The [Sentinel1Denoised package](https://github.com/nansencenter/sentinel1denoised/blob/master/README.md).
2. Laust Færch implemented the CFAR algorithm used in this module: [CFAR object detection](https://github.com/LaustFaerch/cfar-object-detection). A modified version was used.
3. Johannes Lohse and Catherine Taelman wrote the geocoding module for synthetic aperture radar data: [geocoding](https://github.com/jlo031/geocoding). A modified version was used.



