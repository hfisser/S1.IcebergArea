# ---- This is <geocode_image_from_lat_lon.py> ----

import geocoding
import argparse
from loguru import logger

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def make_parser():

  p = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=\
      geocoding.geocode_image_from_lat_lon.__doc__.split("\n")[0],
  )

  p.add_argument(
    'img_path', 
    help='path to input image file (feature, labels, etc)'
  )
  p.add_argument(
    'lat_path',
    help='path to input latidue image'
  )
  p.add_argument(
    'lon_path',
    help='path to input longitude image'
  )
  p.add_argument(
    'output_path',
    help='path to geocoded output tif file'
  )
  p.add_argument(
    'epsg',
    help='output epsg code (polar stereographic = 3996)'
  )
  p.add_argument(
    'pixel_spacing',
    help='output pixel spacing in units of the output projection'
  )
  p.add_argument(
    '-tie_points',
    default=21,
    help='number of tie points per dimension (default=21)'
  )
  p.add_argument(
    '-order',
    default=3,
    help='order of polynomial used for gdalwarp (default=3)'
  )
  p.add_argument(
    '-resampling',
    default='near',
    help='resampling method to use for gdalwarp(default=near)'
  )
  p.add_argument(
    '-overwrite',
    action='store_true',
    help = "overwrite existing files"
  )
  p.add_argument(
    '-loglevel',
    choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
    default='INFO',
    help='set logger level (default=INFO)'
  )

  return p

# -------------------------------------------------------------------------- #

if __name__ == '__main__':

  p = make_parser()
  args = p.parse_args()

  try:
    geocoding.geocode_image_from_lat_lon(**vars(args))
  except Exception as E:
    logger.critical(E)

# -------------------------------------------------------------------------- #

# ---- End of <geocode_image_from_lat_lon.py> ----
