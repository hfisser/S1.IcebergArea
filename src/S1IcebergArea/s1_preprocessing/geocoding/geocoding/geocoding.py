# ---- This is <geocoding.py> ----

"""
Module for geocoding of image files.
""" 

import os
import sys
import pathlib
import shutil

from loguru import logger

import numpy as np

from osgeo import ogr, osr, gdal, gdalconst
from PIL import Image, ImageDraw

import S1IcebergArea.s1_preprocessing.geocoding.config_geocoding as conf
import S1IcebergArea.s1_preprocessing.geocoding.Lib.S1_product_functions as S1
import S1IcebergArea.s1_preprocessing.geocoding.Lib.read_write_img as rwi
import S1IcebergArea.s1_preprocessing.geocoding.Lib.geocoding_functions as gf

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

# TO DO: what is rwi.get_all_bands returns more than 1 band?? Does this still work?

def geocode_image_from_lat_lon(
  img_path,
  lat_path,
  lon_path,
  output_path,
  epsg,
  pixel_spacing,
  tie_points=21,
  order=3,
  resampling='near',
  overwrite=False,
  loglevel='INFO',
):

  """Geocode image (feature or labels) using GCPS from lat/lon bands

  Parameters
  ----------
  img_path : path to input image file (feature, labels, etc)
  lat_path : path to input latitude image
  lon_path : path to input longitude image
  output_path : path to geocoded output tif file
  epsg : output epsg code (polar stereographic = 3996)
  pixel_spacing : output pixel spacing in units of the output projection 
  tie_points : number of tie points per dimension (default=21)
  order : order of polynomial used for gdalwarp (default=3)
  resampling : resampling method to use for gdalwarp(default='near')
  overwrite : overwrite existing files (default=False)
  loglevel : loglevel setting (default='INFO')
  """

  # # remove default logger handler and add personal one
  # logger.remove()
  # logger.add(sys.stderr, level=loglevel)

  # logger.info('Geocoding input image using lat/lon bands')

  # logger.debug(f'{locals()}')
  # logger.debug(f'file location: {__file__}')

  # # get directory where module is installed
  # module_path = pathlib.Path(__file__).parent.parent
  # logger.debug(f'module_path: {module_path}')

  # # get directory where config module is installed, which contains snap graphs
  # config_path = pathlib.Path(conf.__file__).parent
  # logger.debug(f'config_path: {config_path}')

# -------------------------------------------------------------------------- #

  # convert folder/file strings to paths
  img_path    = pathlib.Path(img_path).expanduser().absolute()
  lat_path    = pathlib.Path(lat_path).expanduser().absolute()
  lon_path    = pathlib.Path(lon_path).expanduser().absolute()
  output_path = pathlib.Path(output_path).expanduser().absolute()

  # convert string to integer
  tie_points = int(tie_points)
  
  logger.debug(f'img_path:    {img_path}')
  logger.debug(f'lat_path:    {lat_path}')
  logger.debug(f'lon_path:    {lon_path}')
  logger.debug(f'output_path: {output_path}')

  if not img_path.is_file():
    logger.error(f'Cannot find img_path: {img_path}')
    raise FileNotFoundError(
      f'Cannot find img_path: {img_path}'
    )

  if not lat_path.is_file():
    logger.error(f'Cannot find lat_path: {lat_path}')
    raise FileNotFoundError(
      f'Cannot find lat_path: {lat_path}'
    )

  if not lon_path.is_file():
    logger.error(f'Cannot find lon_path: {lon_path}')
    raise FileNotFoundError(
      f'Cannot find lon_path: {lon_path}'
    )

  # check if outfile already exists
  if output_path.is_file() and not overwrite:
    logger.info('Output file already exists, use `-overwrite` to force')
    return

# -------------------------------------------------------------------------- #

  # create tmp_folder for merged temporary outputs
  tmp_folder = output_path.parent / 'tmp'
  if tmp_folder.is_dir():
    logger.debug('Removing existing tmp_folder')
    shutil.rmtree(tmp_folder)
  tmp_folder.mkdir(parents=True, exist_ok=False)

  # build tif_with_gcps_path (temporarily needed, deleted at the end)
  tif_with_gcps_path = tmp_folder / f'{output_path.stem}_gcps.tif'

  logger.debug(f'tif_with_gcps_path (temporary output): {tif_with_gcps_path}')

# -------------------------------------------------------------------------- #

  logger.info(f'Input image: {img_path}')
  logger.info(f'Output image: {output_path}')
  logger.info(f'Output pixel spacing: {pixel_spacing}')
  logger.info(f'Output epsg code: {epsg}')

# -------------------------------------------------------------------------- #
  
  # read image, latitude, and longitude images
  img = rwi.get_all_bands(img_path.as_posix())
  lat = rwi.get_all_bands(lat_path.as_posix())
  lon = rwi.get_all_bands(lon_path.as_posix())
  
  # create list of gcps from lat-lon bands
  gcps = gf.extract_GCPS_from_lat_lon_bands(img, lat, lon, tie_points)
  
  # create srs
  srs, tie_point_WKT = gf.create_srs_and_WKT()

  # reoreferencing of the feature band
  gf.georeference_band(img, gcps, tif_with_gcps_path, tie_point_WKT)
    
  # clean up
  srs = None
  
# -------------------------------------------------------------------------- #
  # gdalwarp
  gf.warp_feature_to_target_projection(tif_with_gcps_path, output_path, epsg, pixel_spacing)

  # remove snap tmp_dir
  shutil.rmtree(tmp_folder)

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def geocode_S1_image_from_GCPS(
  img_path,
  safe_folder,
  output_path,
  epsg,
  pixel_spacing=200,
  order=3,
  resampling='near',
  overwrite=False,
  loglevel='INFO',
):

  """Geocode S1 image (feature or labels) using GCPS from original product

  Parameters
  ----------
  img_path : path to S1 input image file (feature, labels, etc)
  safe_folder : path to S1 image SAFE folder
  output_path : path to geocoded output tif file
  epsg : output epsg code (polar stereographic = 3996)
  pixel_spacing : output pixel spacing in units of the output projection (e.g. 200 m for epsg 3996)
  order : order of polynomial used for gdalwarp (default=3)
  resampling : resampling method to use for gdalwarp(default='near')
  overwrite : overwrite existing files (default=False)
  loglevel : loglevel setting (default='INFO')
  """

  # remove default logger handler and add personal one
  logger.remove()
  logger.add(sys.stderr, level=loglevel)

  logger.info('Geocoding input image using original product GCPS')

  logger.debug(f'{locals()}')
  logger.debug(f'file location: {__file__}')

  # get directory where module is installed
  module_path = pathlib.Path(__file__).parent.parent
  logger.debug(f'module_path: {module_path}')

  # get directory where config module is installed, which contains snap graphs
  config_path = pathlib.Path(conf.__file__).parent
  logger.debug(f'config_path: {config_path}')

# -------------------------------------------------------------------------- #

  # convert folder strings to paths
  img_path    = pathlib.Path(img_path).expanduser().absolute()
  safe_folder = pathlib.Path(safe_folder).expanduser().absolute()
  output_path = pathlib.Path(output_path).expanduser().absolute()

  logger.debug(f'img_path:   {img_path}')
  logger.debug(f'safe_folder: {safe_folder}')
  logger.debug(f'output_path: {output_path}')

  if not img_path.is_file():
    logger.error(f'Cannot find img_path: {img_path}')
    raise FileNotFoundError(
      f'Cannot find img_path: {img_path}'
    )

  if not safe_folder.is_dir():
    logger.error(f'Cannot find Sentinel-1 SAFE folder: {safe_folder}')
    raise NotADirectoryError(
      f'Cannot find Sentinel-1 SAFE folder: {safe_folder}'
    )

  # check if outfile already exists
  if output_path.is_file() and not overwrite:
    logger.info('Output file already exists, use `-overwrite` to force')
    return

# -------------------------------------------------------------------------- #

  # create tmp_folder for merged temporary outputs
  tmp_folder = output_path.parent / 'tmp'
  if tmp_folder.is_dir():
    logger.debug('Removing existing tmp_folder')
    shutil.rmtree(tmp_folder)
  tmp_folder.mkdir(parents=True, exist_ok=False)

  # build tif_with_gcps_path (temporarily needed, deleted at the end)
  tif_with_gcps_path = tmp_folder / f'{output_path.stem}_gcps.tif'

  logger.debug(f'tif_with_gcps_path (temporary output): {tif_with_gcps_path}')

  # build path to manifest.safe file
  safe_path = safe_folder / 'manifest.safe'
  
  gcps_path = safe_path
  
# -------------------------------------------------------------------------- #

  logger.info(f'Input image: {img_path}')
  logger.info(f'Output image: {output_path}')
  logger.info(f'Output pixel spacing: {pixel_spacing}')
  logger.info(f'Output epsg code: {epsg}')

# -------------------------------------------------------------------------- #
  
  # create srs and WKT (4326 is WGS84 geographic lat/lon)
  srs, tie_point_WKT = gf.create_srs_and_WKT()
  
  # embed gcps with feature in tif file
  gf.embed_gcps_with_feature(img_path, gcps_path, tif_with_gcps_path, srs)
  
  #warp with to target epsg
  gf.warp_feature_to_target_projection(tif_with_gcps_path, output_path, epsg, pixel_spacing)
    
  # remove snap tmp_dir
  shutil.rmtree(tmp_folder)
      
  return

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #


def geocode_RS2_image_from_GCPS(
  img_path,
  original_product_path,
  output_path,
  epsg,
  pixel_spacing,
  order=3,
  resampling='near',
  overwrite=False,
  loglevel='INFO',
):

  """Geocode RS2 image (feature or labels) using GCPS from original product

  Parameters
  ----------
  img_path : path to RS2 input image (feature, labels, etc) in .img format
  original_product_path : path to original RS2 product folder (basename)
  output_path : path to geocoded output tif file
  epsg : output epsg code (polar stereographic = 3996)
  pixel_spacing : output pixel spacing in units of the target projection (epsg 3996 is in m)
  order : order of polynomial used for gdalwarp (default=3)
  resampling : resampling method to use for gdalwarp(default='near')
  overwrite : overwrite existing files (default=False)
  loglevel : loglevel setting (default='INFO')
  """

  # remove default logger handler and add personal one
  logger.remove()
  logger.add(sys.stderr, level=loglevel)

  logger.info('Geocoding input image using original product GCPS')

  logger.debug(f'{locals()}')
  logger.debug(f'file location: {__file__}')

  # get directory where module is installed
  module_path = pathlib.Path(__file__).parent.parent
  logger.debug(f'module_path: {module_path}')

  # get directory where config module is installed, which contains snap graphs
  config_path = pathlib.Path(conf.__file__).parent
  logger.debug(f'config_path: {config_path}')

# -------------------------------------------------------------------------- #

  # convert folder strings to paths
  img_path    = pathlib.Path(img_path).expanduser().absolute()
  original_product_path = pathlib.Path(original_product_path).expanduser().absolute()
  output_path = pathlib.Path(output_path).expanduser().absolute()

  logger.debug(f'img_path:   {img_path}')
  logger.debug(f'original_product_path: {original_product_path}')
  logger.debug(f'output_path: {output_path}')

  if not img_path.is_file():
    logger.error(f'Cannot find img_path: {img_path}')
    raise FileNotFoundError(
      f'Cannot find img_path: {img_path}'
    )

  if not original_product_path.is_dir():
    logger.error(f'Cannot find RS2 product folder: {original_product_path}')
    raise NotADirectoryError(
      f'Cannot find RS2 product folder: {original_product_path}'
    )

  # check if outfile already exists
  if output_path.is_file() and not overwrite:
    logger.info('Output file already exists, use `-overwrite` to force')
    return

# -------------------------------------------------------------------------- #

  # create tmp_folder for merged temporary outputs
  tmp_folder = output_path.parent / 'tmp'
  if tmp_folder.is_dir():
    logger.debug('Removing existing tmp_folder')
    shutil.rmtree(tmp_folder)
  tmp_folder.mkdir(parents=True, exist_ok=False)

  # build tif_with_gcps_path (temporarily needed, deleted at the end)
  tif_with_gcps_path = tmp_folder / f'{output_path.stem}_gcps.tif'

  logger.debug(f'tif_with_gcps_path (temporary output): {tif_with_gcps_path}')

  # build path to product.xml file
  product_path = original_product_path / 'product.xml'

# -------------------------------------------------------------------------- #

  logger.info(f'Input image: {img_path}')
  logger.info(f'Output image: {output_path}')
  logger.info(f'Output pixel spacing: {pixel_spacing}')
  logger.info(f'Output epsg code: {epsg}')

# -------------------------------------------------------------------------- #


  # create srs and WKT (default epsg = 4326, WGS84 geographic lat/lon)
  srs, tie_point_WKT = gf.create_srs_and_WKT()

  # embed gcps with feature in tif file
  gf.embed_gcps_with_feature(img_path, product_path, tif_with_gcps_path, srs)

  #warp with to target epsg
  gf.warp_feature_to_target_projection(tif_with_gcps_path, output_path, epsg, pixel_spacing)

  # remove snap tmp_dir
  shutil.rmtree(tmp_folder)

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

# TO BE TESTED!!! 

def geocode_TSX_image_from_lat_lon(
  img_path,
  original_product_path,
  output_path,
  epsg,
  pixel_spacing,
  tie_points = 21,
  order=3,
  resampling='near',
  overwrite=False,
  loglevel='INFO',
):

  """Geocode TSX image using lat/lon bands extracted from original product

  Parameters
  ----------
  img_path : path to TSX input image file (feature, labels, etc)
  original_product_path : path to original TSX product folder (basename)
  output_path : path to geocoded output tif file
  epsg : output epsg code (polar stereographic = 3996)
  pixel_spacing : output pixel spacing in units of the target projection (epsg 3996 is in m)
  tie_points: number of tie points per dimension (default=21)
  order : order of polynomial used for gdalwarp (default=3)
  resampling : resampling method to use for gdalwarp(default='near')
  overwrite : overwrite existing files (default=False)
  loglevel : loglevel setting (default='INFO')
  """

  # remove default logger handler and add personal one
  logger.remove()
  logger.add(sys.stderr, level=loglevel)

  logger.info('Geocoding input image using original product lat/lon bands')

  logger.debug(f'{locals()}')
  logger.debug(f'file location: {__file__}')

  # get directory where module is installed
  module_path = pathlib.Path(__file__).parent.parent
  logger.debug(f'module_path: {module_path}')

  # get directory where config module is installed, which contains snap graphs
  config_path = pathlib.Path(conf.__file__).parent
  logger.debug(f'config_path: {config_path}')

# -------------------------------------------------------------------------- #

  # convert folder strings to paths
  img_path    = pathlib.Path(img_path).expanduser().absolute()
  original_product_path = pathlib.Path(original_product_path).expanduser().absolute()
  output_path = pathlib.Path(output_path).expanduser().absolute()

  logger.debug(f'img_path:   {img_path}')
  logger.debug(f'original_product_path: {original_product_path}')
  logger.debug(f'output_path: {output_path}')

  if not img_path.is_file():
    logger.error(f'Cannot find img_path: {img_path}')
    raise FileNotFoundError(
      f'Cannot find img_path: {img_path}'
    )

  if not original_product_path.is_dir():
    logger.error(f'Cannot find TSX product folder: {original_product_path}')
    raise NotADirectoryError(
      f'Cannot find TSX product folder: {original_product_path}'
    )

  # check if outfile already exists
  if output_path.is_file() and not overwrite:
    logger.info('Output file already exists, use `-overwrite` to force')
    return

# -------------------------------------------------------------------------- #

  # create tmp_folder for merged temporary outputs
  tmp_folder = output_path.parent / 'tmp'
  if tmp_folder.is_dir():
    logger.debug('Removing existing tmp_folder')
    shutil.rmtree(tmp_folder)
  tmp_folder.mkdir(parents=True, exist_ok=False)

  # build tif_with_gcps_path (temporarily needed, deleted at the end)
  tif_with_gcps_path = tmp_folder / f'{output_path.stem}_gcps.tif'

  logger.debug(f'tif_with_gcps_path (temporary output): {tif_with_gcps_path}')

  # no GCPS for TSX products, so extract lat/lon bands and geocode with those
  product_path = original_product_path / 'product.xml'

# -------------------------------------------------------------------------- #

  logger.info(f'Input image: {img_path}')
  logger.info(f'Output image: {output_path}')
  logger.info(f'Output pixel spacing: {pixel_spacing}')
  logger.info(f'Output epsg code: {epsg}')

# -------------------------------------------------------------------------- #

  # create srs and WKT (default epsg = 4326, which is WGS84 geographic lat/lon)
  srs, tie_point_WKT = gf.create_srs_and_WKT()
  
  # extract lat lon bands from TSX using snap graph
  feature_band = rwi.get_all_bands(img_path.as_posix())
  lat_band = None
  lon_band = None
  
  gcps = gf.extract_GCPS_from_lat_lon_bands(feature_band, lat_band, lon_band, tie_points = 21)
  
  # reoreferencing of the feature band
  gf.georeference_band(feature_band, gcps, tif_with_gcps_path, tie_point_WKT)

  #warp with to target epsg
  gf.warp_feature_to_target_projection(tif_with_gcps_path, output_path, epsg, pixel_spacing)

  # remove snap tmp_dir
  shutil.rmtree(tmp_folder)

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def geocode_S1_image_from_SNAP(
  img_path,
  safe_folder,
  output_path,
  pixel_spacing=200,
  overwrite=False,
  loglevel='INFO',
):

  """Geocode S1 image to EPSG:3996 using SNAP (RD Ellipsoid Cor)

  Parameters
  ----------
  img_path : path to S1 input image file (feature, labels, etc)
  safe_folder : path to S1 image SAFE folder
  output_path : path to geocoded output tif file
  pixel_spacing : output pixel spacing in meter (default=200m)
  overwrite : overwrite existing files (default=False)
  loglevel : loglevel setting (default='INFO')
  """

  # remove default logger handler and add personal one
  logger.remove()
  logger.add(sys.stderr, level=loglevel)

  logger.info('Geocoding input image using SNAP (Average-Height RD)')

  logger.debug(f'{locals()}')
  logger.debug(f'file location: {__file__}')

  # get directory where module is installed
  module_path = pathlib.Path(__file__).parent.parent
  logger.debug(f'module_path: {module_path}')

  # get directory where config module is installed, which contains snap graphs
  config_path = pathlib.Path(conf.__file__).parent
  logger.debug(f'config_path: {config_path}')

# -------------------------------------------------------------------------- #

  # convert folder strings to paths
  img_path    = pathlib.Path(img_path).expanduser().absolute()
  safe_folder = pathlib.Path(safe_folder).expanduser().absolute()
  output_path = pathlib.Path(output_path).expanduser().absolute()

  logger.debug(f'img_path:    {img_path}')
  logger.debug(f'safe_folder: {safe_folder}')
  logger.debug(f'output_path: {output_path}')
  logger.debug(f'conf.GPT:    {conf.GPT}')

  if not img_path.is_file():
    logger.error(f'Cannot find img_path: {img_path}')
    raise FileNotFoundError(
      f'Cannot find img_path: {img_path}'
    )

  if not safe_folder.is_dir():
    logger.error(f'Cannot find Sentinel-1 SAFE folder: {safe_folder}')
    raise NotADirectoryError(
      f'Cannot find Sentinel-1 SAFE folder: {safe_folder}'
    )

  # check if outfile already exists
  if output_path.is_file() and not overwrite:
    logger.info('Output file already exists, use `-overwrite` to force')
    return

# -------------------------------------------------------------------------- #

  # create tmp_folder for merged temporary outputs
  tmp_folder = output_path.parent / 'tmp'
  if tmp_folder.is_dir():
    logger.debug('Removing existing tmp_folder')
    shutil.rmtree(tmp_folder)
  tmp_folder.mkdir(parents=True, exist_ok=False)

  # build dim_path and merged_path (temporarily needed, deleted at the end)
  dim_path    = tmp_folder / f'dim_product.dim'
  merged_path = tmp_folder / f'merged_product.dim'

  logger.debug(f'dim_path: {dim_path}')
  logger.debug(f'merged_path: {merged_path}')

  # build img_path_hdr (header file is needed to read correct band name)
  img_path_hdr = img_path.parent / f'{img_path.stem}.hdr'
  logger.debug(f'img_path_hdr: {img_path_hdr}')

  # find band_name in header file
  band_name = 'Band_1'
  with open(img_path_hdr.as_posix(), 'r')  as f:
    hdr_text = f.read().splitlines()

  for line in hdr_text:
    if 'band names' in line:
      logger.debug(f'header line containing band name: "{line}"')
      band_name = line.split('{ ')[1].split(' }')[0]
      logger.debug(f'band_name: "{band_name}"')

# -------------------------------------------------------------------------- #

  logger.info(f'Input image: {img_path}')
  logger.info(f'Output image: {output_path}')
  logger.info(f'Input band: {band_name}')
  logger.info(f'Output pixel spacing: {pixel_spacing}')
  logger.info(f'Output epsg code: 3996')

# -------------------------------------------------------------------------- #

  # build 3 snap graphs that are needed


  # 1)
  # extract IA from .SAFE product and write to tmp_folder (dim_path)

  snap_IA_graph_file = conf.snap_S1_IA
  snap_IA_graph_path = config_path / 'snap_graphs' / snap_IA_graph_file

  if not snap_IA_graph_path.is_file():
    logger.error(f'Cannot find snap_IA_graph_path: {snap_IA_graph_path}')
    raise FileNotFoundError(
      f'Cannot find snap_IA_graph_path: {snap_IA_graph_path}'
    )

  snap_IA_cmd = f'"{conf.GPT}" ' + \
    f'{snap_IA_graph_path} ' + \
    f'-PinFile={safe_folder} ' + \
    f'-PoutFile={dim_path}'


  # 2)
  # merge IA dim product (dim_path) with image that shall be geocoded

  snap_merge_cmd = f'"{conf.GPT}" merge ' + \
    f'-SmasterProduct={dim_path} ' + \
    f'-PgeographicError=NaN ' + \
    f'-t {merged_path} ' + \
    f'{img_path_hdr}'


  # 3)
  # geocode correct band of merged dim product (merged_path)

  snap_geocode_graph_file = conf.snap_dim_product_RD
  snap_geocode_graph_path = \
    config_path / 'snap_graphs' / snap_geocode_graph_file
  
  if not snap_geocode_graph_path.is_file():
    logger.error(
      f'Cannot find snap_geocode_graph_path: {snap_geocode_graph_path}'
    )
    raise FileNotFoundError(
      f'Cannot find snap_geocode_graph_path: {snap_geocode_graph_path}'
    )
  snap_geocode_cmd = f'"{conf.GPT}" ' + \
    f'{snap_geocode_graph_path} ' + \
    f'-PinFile={merged_path} ' + \
    f'-PoutFile={output_path} ' + \
    f'-PpixelSpacing={pixel_spacing} ' + \
    f'-PsourceBand={band_name}'
    
# -------------------------------------------------------------------------- #

  logger.info(
    'Running snap to create .dim product needed for merging and geocoding'
  )
  logger.debug(f'Executing: {snap_IA_cmd}')
  os.system(snap_IA_cmd)

  logger.info('Running snap to merge image to .dim product')
  logger.debug(f'Executing: {snap_merge_cmd}')
  os.system(snap_merge_cmd)

  logger.info('Running snap to geocode merged product')
  logger.debug(f'Executing: {snap_geocode_cmd}')
  os.system(snap_geocode_cmd)

  # remove snap tmp_dir
  shutil.rmtree(tmp_folder)

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def convert_osm_landmask_2_SAR_geometry(
  lat_path,
  lon_path,
  shapefile_path,
  output_path,
  tie_points=21,
  overwrite=False,
  loglevel='INFO',
):

  """Create SAR geometry landmask from OSM shapefile

  Parameters
  ----------
  lat_path : path to input latidue image
  lon_path : path to input longitude image
  shapefile_path : path to OSM shapefile
  output_path : path to output mask file
  tie_points : number of tie points per dimension (default=21)
  overwrite : overwrite existing files (default=False)
  loglevel : loglevel setting (default='INFO')
  """

  # remove default logger handler and add personal one
  logger.remove()
  logger.add(sys.stderr, level=loglevel)

  logger.info('Creating SAR geometry landmask from OSM shapefile')

  logger.debug(f'{locals()}')
  logger.debug(f'file location: {__file__}')

  # get directory where module is installed
  module_path = pathlib.Path(__file__).parent.parent
  logger.debug(f'module_path: {module_path}')

  # get directory where config module is installed, which contains snap graphs
  config_path = pathlib.Path(conf.__file__).parent
  logger.debug(f'config_path: {config_path}')

# -------------------------------------------------------------------------- #

  # convert folder/file strings to paths
  lat_path       = pathlib.Path(lat_path).expanduser().absolute()
  lon_path       = pathlib.Path(lon_path).expanduser().absolute()
  shapefile_path = pathlib.Path(shapefile_path).expanduser().absolute()
  output_path    = pathlib.Path(output_path).expanduser().absolute()

  # convert tie_point string to integer
  tie_points = int(tie_points)

  logger.debug(f'lat_path:       {lat_path}')
  logger.debug(f'lon_path:       {lon_path}')
  logger.debug(f'shapefile_path: {shapefile_path}')
  logger.debug(f'output_path:    {output_path}')

  if not lat_path.is_file():
    logger.error(f'Cannot find lat_path: {lat_path}')
    raise FileNotFoundError(
      f'Cannot find lat_path: {lat_path}'
    )

  if not lon_path.is_file():
    logger.error(f'Cannot find lon_path: {lon_path}')
    raise FileNotFoundError(
      f'Cannot find lon_path: {lon_path}'
    )

  if not shapefile_path.is_file():
    logger.error(f'Cannot find shapefile_path: {shapefile_path}')
    raise FileNotFoundError(
      f'Cannot find shapefile_path: {shapefile_path}'
    )

  # check if outfile already exists
  if output_path.is_file() and not overwrite:
    logger.info('Output file already exists, use `-overwrite` to force')
    return
  elif output_path.is_file() and overwrite:
    logger.info('Removing existing output file')
    os.remove(output_path)

# -------------------------------------------------------------------------- #

  # The water-polygons-split-4326 ocean dataset is distributed in
  # water_polygons.shp with inside (1, True) to be used as 1's and
  # outside as 0's in the mask.


  # open image dataset
  ds = gdal.Open(lat_path.as_posix(), gdal.GA_ReadOnly)

  # get image dimensions
  n_rows = ds.RasterYSize
  n_cols = ds.RasterXSize
       
  # find southern latitude limits, in case we need Antarctica.
  lats = ds.ReadAsArray().astype(np.float32)
  lat_min = np.nanmin(lats)
  lat = None

  logger.debug(f'Minimum latitude: {lat_min}')

  # clean up
  del ds

# -------------------------------------------------------------------------- #

  # get gcps and projection from lat and lon
  (gcps, tpWKT) = get_lat_lon_tp(
    lat_path, lon_path, tie_points, loglevel=loglevel
  )

  # create initial mask image of correct size
  # create white image (ones) and later fill polygons to zero
  mask = Image.new('L', (n_cols, n_rows), 1)

  # create output file dummy
  driver = gdal.GetDriverByName('Envi')
  driver.Register()
  dsOut = driver.Create(
    output_path.as_posix(), n_cols, n_rows, 1, gdal.GDT_Byte
  )
  band = dsOut.GetRasterBand(1)
  band.WriteArray(np.array(mask).astype(bool))

  dsOut.SetGCPs(gcps, tpWKT)
  dsOut.FlushCache()

  # close and clean up
  del band

# -------------------------------------------------------------------------- #

  # create coordinate transformation from image coords to lat/lon
  tr = gdal.Transformer(dsOut, None, ['METHOD=GCP_POLYNOMIAL'])

  logger.info('Masking from input shapefile')
  logger.info('Current versions assumes land polygons in shapefile')
  logger.info('Resulting mask will be: water=1, land=0')

# -------------------------------------------------------------------------- #

  # open shapefile (assumes that polygons are in the first layer - true for OSM)
  shp = ogr.Open(shapefile_path.as_posix())
  layer = shp.GetLayer(0)
  n_features = layer.GetFeatureCount()

  logger.debug(f'found {n_features} features in shapefile')

  # loop through all land polygons
  points = []
  for i in range(n_features):
 
    if np.mod(i,10000) == 0:
      logger.debug(f'processing feature {i} of {n_features}')

    # get current polygon
    feature = layer.GetFeature(i)
    geometry = feature.GetGeometryRef()
    ring = geometry.GetGeometryRef(0)
    n_points = ring.GetPointCount()

    # loop through polygon points and convert lat/lon to pixel coordinates
    points = []
    for idx, p in enumerate(ring.GetPoints()):
      # The trick is this line. The first 1 asks the transformer to do an
      # inverse transformation, so this is transforms lat/lon coords to pixel coords
      (success, point) = tr.TransformPoint(1, p[0], p[1], 0)
      if success:
        px = point[0]
        py = point[1]
        points.append((px, py))

    # Rasterize the polygon in image coordinates.
    # The polygon function requires at least two points.
    if len(points) > 2:
      # NB: given land masks=fill to zero, plus boundary zero.
      ImageDraw.Draw(mask).polygon(points, outline=0, fill=0)

# -------------------------------------------------------------------------- #

  # convert to a numpy array (not sure if this is necessary)
  mask = np.array(mask).astype(bool)

  # now re-do the output mask file, with new mask.
  # NB: geo-coding should already be embedded.
  band = dsOut.GetRasterBand(1)
  band.WriteArray(mask)

  dsOut.SetGCPs(gcps, tpWKT)
  dsOut.FlushCache()

  # Close and clean up
  del band

  del dsOut

  return

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def get_lat_lon_tp(
  lat_path,
  lon_path,
  tie_points=11,
  loglevel='INFO'
):

  """Create tie-point grid from lat/lon bands

  Parameters
  ----------
  lat_path : path to input latitude image
  lon_path : path to input longitude image
  tie_points : number of tie points per dimension (default=21)
  loglevel : loglevel setting (default='INFO')

  Returns
  -------
  gcps : list of tie points
  tie_point_WKT : tie-point well-known text projection
  """

  # remove default logger handler and add personal one
  logger.remove()
  logger.add(sys.stderr, level=loglevel)

  logger.info('Creating landmask from OSM shapefile')

  logger.debug(f'{locals()}')
  logger.debug(f'file location: {__file__}')

  # get directory where module is installed
  module_path = pathlib.Path(__file__).parent.parent
  logger.debug(f'module_path: {module_path}')

  # get directory where config module is installed, which contains snap graphs
  config_path = pathlib.Path(conf.__file__).parent
  logger.debug(f'config_path: {config_path}')

# -------------------------------------------------------------------------- #

  # convert folder/file strings to paths
  lat_path       = pathlib.Path(lat_path).expanduser().absolute()
  lon_path       = pathlib.Path(lon_path).expanduser().absolute()

  # convert tie_point string to integer
  tie_points = int(tie_points)

  logger.debug(f'lat_path: {lat_path}')
  logger.debug(f'lon_path: {lon_path}')

  if not lat_path.is_file():
    logger.error(f'Cannot find lat_path: {lat_path}')
    raise FileNotFoundError(
      f'Cannot find lat_path: {lat_path}'
    )

  if not lon_path.is_file():
    logger.error(f'Cannot find lon_path: {lon_path}')
    raise FileNotFoundError(
      f'Cannot find lon_path: {lon_path}'
    )

# -------------------------------------------------------------------------- #

  # read latitude, and longitude images
  lat = rwi.get_all_bands(lat_path.as_posix())
  lon = rwi.get_all_bands(lon_path.as_posix())

  # check that lat and lon dimenesions match
  if lat.shape != lon.shape :
    logger.error('lat, and lon must have the same array shape')
    raise ValueError(
      f'lat, and lon must have the same array shape'
    )

  # get original iamge data type, number of lines and samples
  data_type_in = gdal.Open(
    lat_path.as_posix(), gdal.GA_ReadOnly
  ).GetRasterBand(1).DataType
  lines, samples = lat.shape

  logger.debug(f'number of lines-x-samples: {lines}-x-{samples}')

  # extract tie-point-grid.
  tie_points_x = np.linspace(
    0, samples-1, tie_points, endpoint=True
  ).astype(int)
  tie_points_y = np.linspace(
    0, lines-1, tie_points, endpoint=True
  ).astype(int)

  # extract lats and lons for tie points
  tie_points_lat = lat[np.ix_(tie_points_y, tie_points_x)]
  tie_points_lon = lon[np.ix_(tie_points_y, tie_points_x)]

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


  # make WKT at this time too.
  srs, tie_point_WKT = gf.create_srs_and_WKT()

  return (gcps, tie_point_WKT)

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

# ---- End of <geocoding.py> ----
