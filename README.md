## S1.IcebergArea
Predict backscatter-sensitive iceberg areas from Sentinel-1 extra-wide (EW) swath data. This Python module enables users to predict iceberg above-waterline areas from Sentinel-1 EW ground-range detected medium resolution (GRDM) data. The algorithm has been developed and tested for icebergs in open water. The algorithm predicts iceberg areas based on backscatter statistics of icebergs delineated using constant false alarm rate (CFAR) algorithm with a gamma distribution.

### Citation
Publication..

### Installation
Install 

```shell
conda env create -f environment.yml
conda activate s1icebergareas
pip install ...
```

### Example
```python
from S1IcebergArea import S1IcebergArea
dir_safe = "/my/s1_data/S1A_EW_GRDM_1SDH_20240917T191651_20240917T191725_055709_06CDC8_7EF4.SAFE"  # unzipped
dir_tmp = "/my/temporary_folder"
s1_iceberg_area = S1IcebergArea(dir_tmp)
s1_iceberg_area.prepare_s1(dir_safe)
icebergs = s1_iceberg_area.run_model()
```
### Data
Sentinel-1 EW GRDM, HH and HV channel.

### How it works
The module processes the Sentinel-1 data in three steps. Follow three steps:
1. Preprocessing with calibration, geocoding, noise removal (HV).
2. CFAR iceberg delineation, using a CFAR gamma detector with a 10<sup>-6</sup> probability of false alarm, a 29-pixel outer window size, and a 21-pixel guard window size. CFAR runs separately for the HH channel, and the HV channel.
3. Iceberg area prediction, using the backscatter-sensitive iceberg area model (*BackscatterRL* CatBoost model). The model runs separately for the HH channel, and the HV channel.

### Background
Icebergs appear as strong reflectors in synthetic aperture radar (SAR) data. In a varying background (*ocean clutter*), CFAR algorithms detect icebergs as outliers. A connected set of outlier pixel is then grouped as an iceberg with an area. However, these CFAR-based iceberg areas exhibit considerable errors, as they inherit variations in the ocean clutter, and in the iceberg backscatter, along with effects of the spatial resolution. The backscatter-sensitive iceberg area model is aware of these variations, and predicts iceberg areas using a CatBoost regression. The algorithm was trained end evaluated with reference to Sentinel-2 iceberg areas in several hundred acquisitions across the Arctic in the years 2016-2023 from May to September. 

### Credits
This Python module depends on several third-party Python modules. Besides standard Python modules, we use code from three packages:
1. The [Sentinel1Denoised package](https://github.com/nansencenter/sentinel1denoised/blob/master/README.md).
2. Laust Færch implemented the CFAR algorithm used in this module: [CFAR object detection](https://github.com/LaustFaerch/cfar-object-detection). The code was modified.
3. Johannes Lohse and Catherine Taelman wrote the geocoding module for synthetic aperture radar data: [geocoding](). The code was modified.
