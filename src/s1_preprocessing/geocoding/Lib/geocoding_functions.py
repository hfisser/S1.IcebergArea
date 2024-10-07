# ---- This is <geocoding_functions.py> ----

"""
Some helpful functions for geocoding using gdal

"""
import os
import sys
import shutil
import copy

import numpy as np
from osgeo import gdal, osr, gdal_array
from loguru import logger

import Lib.read_write_img as rwi

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 


def create_srs_and_WKT(source_epsg = 4326):
    """create spatial reference system (srs) and corresponding WKT string
      
    Parameters
    ----------
    source_epsg: epsg code for srs (default = 4326, which is WGS84 geographic lat/lon)
      
    Returns
    -------
    srs: spatial reference system object
    tie_point_WKT: srs in WKT string format
    """    
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(source_epsg)
    tie_point_WKT = srs.ExportToWkt() # convert srs to WKT string
    
    return srs, tie_point_WKT

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 
# should tie points be a default value?? Number of tie points depends on what??

def extract_GCPS_from_lat_lon_bands(image_band, lat_band, lon_band, tie_points = 21):
    """build list of GCPS from lat and lon bands
      
    Parameters
    ----------
    image_band: array containing the image data
    lat_band: array containing the latitude grid corresponding to the image band
    lon_band: array containing the longitude grid corresponding to the image band
    tie_points: number of tie points per dimension (default=21)
    
    Returns
    -------
    gcps: list containing GCPS extracted from the lat, lon bands

    """ 
    # check that img, lat, and lon dimensions match
    if image_band.shape != lat_band.shape or image_band.shape != lon_band.shape :
      logger.error('image_band, lat_band, and lon_band must have the same array shape')
      raise ValueError(
        'image_band, lat_band, and lon_band must have the same array shape'
      )

    # get number of lines and samples of original image
    lines, samples = image_band.shape
    logger.debug(f'number of lines-x-samples: {lines}-x-{samples}')

    # extract tie-point-grid.
    tie_points_x = np.linspace(
      0, samples-1, tie_points, endpoint=True
    ).astype(int)
    tie_points_y = np.linspace(
      0, lines-1, tie_points, endpoint=True
    ).astype(int)

    # extract lats and lons for tie points
    tie_points_lat = lat_band[np.ix_(tie_points_y, tie_points_x)]
    tie_points_lon = lon_band[np.ix_(tie_points_y, tie_points_x)]

    # build list of gcps
    gcps = []
    for xi in range(tie_points):
      for yi in range(tie_points):
        tpgcp = gdal.GCP(
          tie_points_lon[yi, xi].astype(float),
          tie_points_lat[yi, xi].astype(float),
          0,
          tie_points_x[xi].astype(float)+1.0,
          tie_points_y[yi].astype(float)+1.0
        )
        gcps.append(tpgcp)
        
    # clean up
    lat_band       = None
    lon_band       = None
    tie_points_x   = None
    tie_points_y   = None
    tie_points_lat = None
    tie_points_lon = None
    tpgcp          = None
    
    return gcps

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 

# TO DO: when changing the values of scaled_gcps, it also changes the values in original_gpcs! How to avoid this?? deepcopy() does not work on gdal GCPS tuple

# TO DO: what kind of file to store gcps? json, txt, csv ??

# NEEDS TO BE TESTED!!!!! is it possible to give list of GCPS as input instead of tuple??

def scale_gcps(original_gcps, multilook_window, output_path = None):
    """scale original gcps according to multilook factor
      
    Parameters
    ----------
    original_gcps: tuple (or LIST??) of gcps before multilooking (as extracted by dataset.GetGCPS() in gdal) 
    multilook_window: multilook window as list (format: [nr_looks_in_range, nr_of_looks_in_azimuth])
    output_path: path to output file where scaled gcps are stored (default = None, so then output not saved!)
    
    Returns
    -------
    scaled_gcps: tuple containing the scaled gcps

    """  
    range_looks = int(multilook_window[0])
    azimuth_looks = int(multilook_window[1])
    
    # make copy of original gcps
    scaled_gcps = original_gcps + tuple()
    
    # loop over original gcps and scale their (pixel,line) coordinate by multilook factor
    for original_gcp, scaled_gcp in zip(original_gcps, scaled_gcps):
        
        # original gcp pixel and line
        gcp_pixel = original_gcp.GCPPixel
        gcp_line = original_gcp.GCPLine
 
        # scale gcps
        gcp_pixel_ml = np.rint(gcp_pixel * 1 / range_looks)
        gcp_line_ml = np.rint(gcp_line * 1 / azimuth_looks)

        # store scaled gcp value in scaled_gcps tuple
        scaled_gcp.GCPPixel = gcp_pixel_ml
        scaled_gcp.GCPLine = gcp_line_ml
        
    if output_path != None:
        print('TO DO!')
    
    return scaled_gcps

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 

def extract_lat_lon_bands_from_projected_image(projected_image_path):
    """Extract lat and lon bands from a projected (=geocoded) image 
      
    Parameters
    ----------
    projected_image_path: path to the projected image (any file extension that can be opened by gdal works)
    
    Returns
    -------
    lat_band: grid of latitudes of shape (image_height, image_width)
    lon_band: grid of longitudes of shape (image_height, image_width)

    """ 
    # open geotiff file with a known projection
    ds = gdal.Open(projected_image_path)
    
    if ds is None:
        logger.error(f'Could not open image file {projected_image_path}')
        sys.exit(1)
        
    # get image dimensions (in pixels) of that geotiff file
    width  = ds.RasterXSize
    height = ds.RasterYSize
    
    # define wgs wkt
    wgs84_wkt = """
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"]]"""
    
    # get old crs from original image
    old_cs = osr.SpatialReference()
    old_cs.ImportFromWkt(ds.GetProjectionRef())
    
    # create new crs for WGS84
    new_cs = osr.SpatialReference()
    new_cs.ImportFromWkt(wgs84_wkt)
    
    # create transform between old and new crs
    transform = osr.CoordinateTransformation(old_cs, new_cs)
    
    # now get the GeoTransform from the original image
    # this returns the 6 coefficients of the affine transformation mapping pixel,line to X_geo,Y_geo
    gt = ds.GetGeoTransform()
    
    # you can use it to calculate all pixel coordinates of the image in the old crs
    original_image_coords = []
    
    for line in range(height):
        for pixel in range(width):
            Xgeo = gt[0] + pixel*gt[1] + line*gt[2]
            Ygeo = gt[3] + pixel*gt[4] + line*gt[5]
            
            original_image_coords.append([Xgeo, Ygeo])
     
    # get lat,lan values for all pixels in original image using the transform
    lat_lons = transform.TransformPoints(tuple(original_image_coords))
    
    # convert list to grid that matches the original image width and height
    # note: 3rd dim returned by the transform = elevation
    lat_lon_array= np.array(lat_lons)
    lat_lon_grid = lat_lon_array.reshape(height, width, 3)
    lat_band = lat_lon_grid[:,:,0]
    lon_band = lat_lon_grid[:,:,1]
    
    return lat_band, lon_band

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 

# TO DO: srs as argument instead of tie_point_WKT?, as the latter can be extracted from the first

def georeference_band(feature_band, gcps_list, output_tif_path, tie_point_WKT):
    """embed gcps with feature (band) into a geotif file
      
    Parameters
    ----------
    feature_band: array containing the feature to be georefenced
    gcps_list: list with gcps
    output_tif_path: path to output geotif file 
    tie_point_WKT: srs.ExportToWkt(), srs: spatial reference system object
    
    Returns
    -------
    -
    
    """    
    # dims and data type of feature band
    lines, samples = feature_band.shape
    data_type_in = gdal_array.NumericTypeCodeToGDALTypeCode(feature_band.dtype.type)
    
    # initialize new GTiff file for output
    GTdriver = gdal.GetDriverByName('GTiff')
    out = GTdriver.Create(
      output_tif_path.as_posix(),
      samples,
      lines,
      1,
      data_type_in
    )

    # write feature to tif file
    band_out = out.GetRasterBand(1)
    band_out.WriteArray(feature_band)
    band_out.FlushCache()

    # embed the tie_points
    out.SetGCPs(gcps_list, tie_point_WKT) # or srs.ExportToWkt() for second argument
    out.FlushCache()
    del out
    
    return
  
    
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 

# TO DO: generalize for numpy array? instead of asking for img format or other format! --> see function above!
# POSSIBLE MERGE THESE TWO FUNCTIONS??

def embed_gcps_with_feature(img_path, gcps_path, output_tif_path, srs):
    """embed gcps with feature (band) into a geotif file
      
    Parameters
    ----------
    img_path: path to feature/band in img format
    gcps_path: path to gcps
    output_tif_path: path to output tif file 
    srs: spatial reference system object
    
    Returns
    -------
    -
    
    """     
    def get_image_and_properties(img_path):
        # read image
        img = rwi.get_all_bands(img_path.as_posix())
        
        # get original image data type, number of lines and samples
        data_type_in = gdal.Open(
          img_path.as_posix(), gdal.GA_ReadOnly
        ).GetRasterBand(1).DataType
        
        # TO DO: DOES THIS WORK FOR 3D img ?? (multiple bands!!)
        lines, samples = img.shape

        logger.debug(f'image data type: {data_type_in}')
        logger.debug(f'number of lines-x-samples: {lines}-x-{samples}')
        
        return img, data_type_in, lines, samples
    
    img, data_type_in, lines, samples = get_image_and_properties(img_path)
    
    GTdriver = gdal.GetDriverByName('GTiff')
    out = GTdriver.Create(
      output_tif_path.as_posix(),
      samples,
      lines,
      1,
      data_type_in
    )
  
    # write feature to new geotiff file
    band_out = out.GetRasterBand(1)
    band_out.WriteArray(img)
    band_out.FlushCache()
  
  # extract GCPS from original location or other file generated by user (e.g. if downsampling is used)
    geo = gdal.Open(gcps_path.as_posix())
  
    if geo is None:
        logger.error(f'Could not open GCPS file {gcps_path}')
        sys.exit(1)
    
  # embed GCPS with feature to geotiff
    out.SetGCPs(geo.GetGCPs(), srs.ExportToWkt())
    out.FlushCache()
    del out
    return

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 

# TO DO: other name option: gdalwarp()

def warp_feature_to_target_projection(feature_with_gcps_tif_path, output_tif_path, target_epsg, pixel_spacing, resampling = 'near', order = 3):
    """warp feature(s) to target epsg projection using gdalwarp
       
    Parameters
    ----------
    feature_with_gcps_tif_path: path to tif file containing the feature(s) with embedded gcps
    output_tif_path: path to output georeferenced feature (tif format)
    target_epsg: output epsg code
    pixel_spacing: output pixel spacing in units of the target projection
    resampling: resampling method to use for gdalwarp(default='near')
    order: order of polynomial used for gdalwarp (default=3)
    
    Returns
    -------
    -
    
    """ 
  # gdalwarp command to project the input image and save output tif to output_tif_path
    gdal_cmd = f'gdalwarp -overwrite -srcnodata 0 -dstnodata 0 ' + \
      f'-t_srs epsg:{target_epsg} ' + \
      f'-tr {pixel_spacing} {pixel_spacing} ' + \
      f'-r {resampling} ' + \
      f'-order {order} ' + \
      f'{feature_with_gcps_tif_path.as_posix()} {output_tif_path.as_posix()}'
  
    logger.info(f'Running gdalwarp to warp image to desired projection ({target_epsg})')
    logger.debug(f'Executing: {gdal_cmd}')
    os.system(gdal_cmd)
    
    return

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- # 

# ---- End of <geocoding_functions.py> ----