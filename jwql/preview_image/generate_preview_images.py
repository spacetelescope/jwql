#! /usr/bin/env python

"""Generate preview images for all files in the ``jwql`` filesystem.

Execution of this script will generate preview images for each file in
the ``jwql`` filesystem, if it does not already exist.

Authors
-------

    Matthew Bourque


Use
---

    This script is intended to be executed as such:

    ::

        python generate_preview_images.py

Notes
-----

    Some of this code could be simplified by using a filename parser
    utility function, which is in the works for ``jwql``.
"""

import glob
import os

from jwql.permissions import permissions
from jwql.preview_image.preview_image import PreviewImage
from jwql.utils.utils import get_config


def generate_preview_images():
    """The main function of the generate_preview_image module."""

    filesystem = get_config()['filesystem']
    preview_image_filesystem = get_config()['preview_image_filesystem']
    filenames = glob.glob(os.path.join(filesystem, '*/*.fits'))

    for filename in filenames:

        # Determine the save location
        rootname_elements = os.path.basename(filename).split('.fits')[0].split('_')
        preview_image_dir = '{}_{}'.format(
            rootname_elements[0],  # Program ID + observation + visit
            rootname_elements[1])  # Visit group + parallel sequence ID + activity
        output_directory = os.path.join(preview_image_filesystem, preview_image_dir)

        # Create the output directory if necessary
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            permissions.set_permissions(output_directory, verbose=False)

        # Create and save the preview image
        try:
            im = PreviewImage(filename, "SCI")
            im.clip_percent = 0.01
            im.scaling = 'log'
            im.cmap = 'viridis'
            im.output_format = 'jpg'
            im.output_directory = output_directory
            im.make_image()
        except ValueError as error:
            print(error)


if __name__ == '__main__':

    generate_preview_images()
