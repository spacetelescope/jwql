#! /usr/bin/env python

"""This script can be used to create a new set of preview and thumbnail image listfiles
to be used by generate_preview_image.py. The listfiles will be saved into the same
directories as the preview images and thumbnail images themselves, as defined in
config.json

Author:  B. Hilbert
"""
from glob import glob
import os
import re

from jwql.utils.utils import get_config


def create_files():
    """Create a new set of listfiles"""
    inst_strings = ['guider', 'nrc', 'miri', 'nis', 'nrs']


    config = get_config()
    prev_img_dir = config["preview_image_filesystem"]
    thumb_img_dir = config["thumbnail_filesystem"]

    # Preview images
    #/internal/data1/preview_images/jw01014/jw01014001001_02101_00001_guider1_rateints_integ4.jpg
    for inst_abbrev in ['miri']: #inst_strings:

        # Instrument abbreviation to use in output filename
        file_abbrev = inst_abbrev
        if file_abbrev == 'guider':
            file_abbrev = 'fgs'

        # Get list of preview images for each instrument and save
        preview_files = sorted(glob(os.path.join(prev_img_dir, f'j*/j*{inst_abbrev}*jpg')))
        prev_listfile = os.path.join(prev_img_dir, f'preview_image_inventory_{file_abbrev}.txt')
        write_file(preview_files, prev_listfile)

        # Get list of thumbnail images for each instrument and save
        thumb_files = sorted(glob(os.path.join(thumb_img_dir, f'j*/j*{inst_abbrev}*thumb')))
        thumb_listfile = os.path.join(thumb_img_dir, f'thumbnail_inventory_{file_abbrev}.txt')
        write_file(thumb_files, thumb_listfile)

def write_file(filelist, output_file):
    """Write a list of filenames to an ascii file

    Parameters
    ----------
    filelist : list
        List of strings

    output_file : str
        Filename to write strings to
    """
    with open(output_file, 'w') as fobj:
        for filename in filelist:
            fobj.write(f'{filename}\n')


if __name__ == '__main__':
    create_files()