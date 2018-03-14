import os
import sys

from astropy.io import fits
from django.shortcuts import render
# from django.views import generic # Weultimately might want to use generic views?

from .db import DatabaseConnection

# Temporary fix until converted into a package...
current_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), 'preview_image')
sys.path.insert(0, parent_dir)
from preview_image import Image

# Temporary fix until converted into a package...
parent_dir = os.path.join(os.path.dirname(current_dir), 'utils')
sys.path.insert(0, parent_dir)
from utils import get_config

FILESYSTEM_DIR = get_config()['filesystem']

INST_LIST = ['FGS', 'MIRI', 'NIRCam', 'NIRISS', 'NIRSpec']
TOOLS = {'FGS': ['Bad Pixel Monitor'],
         'MIRI': ['Dark Current Monitor',
                  'Bad Pixel Monitor', 'Cosmic Ray Monitor', 'Photometry Monitor',
                  'TA Failure Monitor', 'Blind Pointing Accuracy Monitor',
                  'Filter and Calibration Lamp Monitor', 'Thermal Emission Monitor'],
         'NIRCam': ['Bias Monitor',
                    'Readnoise Monitor', 'Gain Level Monitor',
                    'Mean Dark Current Rate Monitor', 'Photometric Stability Monitor'],
         'NIRISS': ['Bad Pixel Monitor',
                    'Readnoise Monitor', 'AMI Calibrator Monitor', 'TSO RMS Monitor'],
         'NIRSpec': ['Optical Short Monitor', 'Target Acquisition Monitor',
                     'Detector Health Monitor', 'Ref Pix Monitor',
                     'Internal Lamp Monitor', 'Instrument Model Updates',
                     'Failed-open Shutter Monitor']}

def home(request):
    template = 'plots_example/home.html'
    context = {'inst_list': INST_LIST,
               'tools': TOOLS}

    return render(request, template, context)

def instrument(request, inst):
    template = 'plots_example/instrument.html'

    return render(request, template,
                  {'inst': inst,
                   'tools': TOOLS})

def view_image(request, inst, file, rewrite=False):
    template = 'plots_example/view_image.html'

    dirname = file[:7]

    # Check that a jpg does not already exist
    jpg_filename = os.path.splitext(file)[0] + '_integ0.jpg'
    jpg_filepath = os.path.join(FILESYSTEM_DIR, dirname, jpg_filename)

    # If it does, just call the existing jpg
    if os.path.exists(jpg_filepath) and not rewrite:
        pass

    # If it doesn't, make it using preview_image
    else:
        fits_filepath = os.path.join(FILESYSTEM_DIR, dirname, file)

        # Only process FITS files that are 3D+ (preview_image can't handle 2D)
        if any([end in fits_filepath for end in ['rate.fits', 'cal.fits', 'i2d.fits']]):
            jpg_filename = 'Cannot currently create JPEG preview for 2-dimensional FITS files.'
        else:
            im = Image(fits_filepath, 'SCI')
            im.make_image()

    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': TOOLS,
                   'jpg': jpg_filename})

def view_header(request, inst, file):
    template = 'plots_example/view_header.html'

    dirname = file[:7]

    fits_filepath = os.path.join(FILESYSTEM_DIR, dirname, file)

    header = fits.getheader(fits_filepath, ext=0).tostring(sep='\n')

    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': TOOLS,
                   'header': header})

def unlooked_images(request, inst):
    imdat = DatabaseConnection().get_filenames_for_instrument(inst)
    template = 'plots_example/unlooked.html'

    return render(request, template,
                  {'inst': inst,
                   'imdat': imdat,
                   'tools': TOOLS})