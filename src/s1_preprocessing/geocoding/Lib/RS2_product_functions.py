# ---- This is <RS2_product_functions.py> ----

"""
Collection of useful simple functions for working with RS2 data.
"""

import os
from loguru import logger

from osgeo import gdal

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def get_RS2_datestring(f_base):
  """Build datestring from RS2 basename

  Parameters
  ----------
  f_base : RS2 input basename

  Returns
  -------
  date : datestring
  datetime : datetime string
  datestring : datestring for figure labeling

  Examples
  --------
  date, datetime, datestring = get_RS2_datestring(f_base)
  """

  try:
    date     = f_base.split('_')[1]
    time     = f_base.split('_')[2]
    datetime = f'{date}T{time}'

    yyyy = datetime[0:4];
    mm   = datetime[4:6]
    dd   = datetime[6:8]
    HH   = datetime[9:11]
    MM   = datetime[11:13]
    SS   = datetime[13:15]
    datestring = yyyy + '/' + mm + '/' + dd + ', ' + HH + ':' + MM

  except:
    logger.warning(
      'Unable to extract date and time from f_base, ' +
      'recommend using RS2 naming conventions'
    )
    date, datetime, datestring = [], [], []

  return date, datetime, datestring

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def get_RS2_product_info(f_base):
  """Get product info from RS2 basename

  Parameters
  ----------
  f_base : RS2 input basename

  Returns
  -------
  product_mode : product mode
  product_type : product type
  product_pols : product polarisation

  Examples
  --------
  product_mode, product_type, product_pols = get_RS2_product_info(f_base)
  """

  try:
    product_mode = f_base.split('_')[4]
    product_type = f_base.split('_')[6]
    product_pol  = f_base.split('_')[5]

    # split product_pol into individual polarisation strings
    # length of individual polarisation string is n=2
    n = 2
    product_pols = [
      product_pol[idx:idx+n] for idx in range(0,len(product_pol),n) 
    ]

  except:
    logger.warning(
      'Unable to extract product info from f_base, ' +
      'recommend using RS2 naming conventions'
    )
    product_mode, product_type, product_pols = [], [], []

  return product_mode, product_type, product_pols

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def get_RS2_zip_name(f_base):
  """Build zip-file name and manifest.safe file name from RS2 basename

  Parameters
  ----------
  f_base : RS2 input file basename

  Returns
  -------
  zip_file : zip-file name
  safe_file : manifest.safe file name

  Examples
  --------
  zip_file, safe_file = get_RS2_zip_name(f_base)
  """

  zip_file  = f_base + '.zip'
  safe_file = f_base + '.SAFE/' + 'manifest.safe'

  return zip_file, safe_file

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def get_img_dimensions(img_path):
  """Get dimensions of image in img_path

  Parameters
  ----------
  img_path : path to img file

  Returns
  -------
  Nx : pixels in x
  Ny : pixels in y

  Examples
  --------
  Nx, Ny = get_img_dimensions(img_path)
  """

  img = gdal.Open(img_path)
  Nx  = img.RasterXSize
  Ny  = img.RasterYSize
  img = None

  return Nx, Ny

def get_img_datatype(f_path):
    """Get datatype of image/tif in f_path
    
    Parameters
    ----------
    img_path : path to img or tif file
    
    Returns
    -------
    datatype : datatype number
    
    
    Examples
    --------
    datatype = get_img_datatype(f_path)
    """
    # open file
    img_file = gdal.Open(f_path)
    
    img_data_type = img_file.GetRasterBand(1).DataType
    data_type_name = gdal.GetDataTypeName(img_data_type)
    
    return data_type_name
    

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

# ---- End of <RS2_product_functions.py> ----
