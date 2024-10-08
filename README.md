## S1.IcebergArea
This Python module enables users to predict iceberg above-waterline areas from Sentinel-1 extra-wide (EW) swath ground-range detected medium resolution (GRDM) data. The algorithm predicts iceberg areas based on backscatter statistics of icebergs delineated using constant false alarm rate (CFAR) algorithm with a gamma distribution.

### Input
A Sentinel-1 EW GRDM .SAFE folder.

### Output
Detected icebergs with a CFAR iceberg area, and a predicted iceberg area in a geopandas GeoDataFrame.

### How it works
The module processes the Sentinel-1 data in three steps:
1. Preprocessing with calibration, geocoding, noise removal (HV).
2. CFAR iceberg delineation, using a CFAR gamma detector with a 10<sup>-6</sup> probability of false alarm, a 29-pixel outer window size, and a 21-pixel guard window size.
3. Iceberg area prediction, using the *BackscatterRL* CatBoost model.
Follow these three steps for sensible results.

### References
Publication..

### Credits
This Python module depends on several third-party Python modules. Besides standard Python modules, we specifically use code from two modules:
1. Laust Færch implemented the CFAR algorithm used in this module: [CFAR object detection](https://github.com/LaustFaerch/cfar-object-detection).
2. Johannes Lohse and Catherine Taelman wrote the geocoding module for synthetic aperture radar data: [geocoding]().
