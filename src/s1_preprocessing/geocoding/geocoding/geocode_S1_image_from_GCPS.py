# ---- This is <geocode_S1_image_from_GCPS.py> ----

import geocoding
import argparse
from loguru import logger

# -------------------------------------------------------------------------- #
# -------------------------------------------------------------------------- #

def make_parser():

  p = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=\
      geocoding.geocode_S1_image_from_GCPS.__doc__.split("\n")[0],
  )

  p.add_argument(
    'img_path', 
    help='path to S1 input image file (feature, labels, etc)'
  )
  p.add_argument(
    'safe_folder',
    help='path to S1 input image SAFE folder'
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
    help='output pixel spacing in units of the output projection (e.g. 200 m for epsg 3996)'
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
    # this optional argument acts as a flag, calling the argument sets its value to True
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
    geocoding.geocode_S1_image_from_GCPS(**vars(args))
  except Exception as E:
    logger.critical(E)

# -------------------------------------------------------------------------- #

# ---- End of <geocode_S1_image_from_GCPS.py> ----
