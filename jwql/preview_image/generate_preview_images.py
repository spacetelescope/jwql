#! /usr/bin/env python

"""Generate preview images for all files in the ``jwql`` filesystem.

Execution of this script will generate preview images and thumbnail
images for each file in the ``jwql`` filesystem.  Preview images have
axes labels, titles, and colorbars, wheras thumbnail images are
smaller and contain no labels.  Images are saved into the
``preview_image_filesystem`` and ``thumbnail_filesystem``, organized
by subdirectories pertaining to the ``program_id`` in the filenames.

Authors
-------

    Matthew Bourque


Use
---

    This script is intended to be executed as such:

    ::

        python generate_preview_images.py
"""

import glob
import os

from jwql.permissions import permissions
from jwql.preview_image.preview_image import PreviewImage
from jwql.utils.utils import get_config
from jwql.utils.utils import filename_parser


def generate_preview_images():
    """The main function of the generate_preview_image module."""

    filesystem = get_config()['filesystem']
    preview_image_filesystem = get_config()['preview_image_filesystem']
    thumbnail_filesystem = get_config()['thumbnail_filesystem']
    filenames = glob.glob(os.path.join(filesystem, '*/*.fits'))

    for filename in filenames:

        # Determine the save location
        try:
            identifier = 'jw{}'.format(filename_parser(filename)['program_id'])
        except ValueError as error:
            identifier = os.path.basename(filename).split('.fits')[0]

        output_directory = os.path.join(preview_image_filesystem, identifier)
        thumbnail_output_directory = os.path.join(thumbnail_filesystem, identifier)

        # Create the output directories if necessary
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            permissions.set_permissions(output_directory, verbose=False)
        if not os.path.exists(thumbnail_output_directory):
            os.makedirs(thumbnail_output_directory)
            permissions.set_permissions(thumbnail_output_directory, verbose=False)

        # Create and save the preview image and thumbnail
        args = zip((False, True), (output_directory, thumbnail_output_directory))
        for thumbnail_bool, directory in args:
            try:
                im = PreviewImage(filename, "SCI")
                im.clip_percent = 0.01
                im.scaling = 'log'
                im.cmap = 'viridis'
                im.output_format = 'jpg'
                im.thumbnail = thumbnail_bool
                im.output_directory = directory
                im.make_image()
            except ValueError as error:
                print(error)

if __name__ == '__main__':

    generate_preview_images()
