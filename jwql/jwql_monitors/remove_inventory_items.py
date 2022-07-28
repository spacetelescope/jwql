#! /usr/bin/env python

"""Remove items from the preview image or thumbnail inventory file based on instrument and/or program number.
This will open the preview image or thumbnail invnetory file for the given instrument, and delete all lines that
contain the given string. The location of the preview or thumbnail inventory file to be examined is determined
using the JWQL config.json file.

Authors
-------

    - Bryan Hilbert

Use
---

    This script is intended to be executed as shown below. In this example, it will remove all entries from
    the nircam preview image inventory file that contain the string "jw01022". The -i option is used to
    designate the instrument. The -p option is used to designate the preview image inventory file ('p')
    or the thumbnail inventory file ('t'). The -s option is used to define the string to search for in
    each line.

    ::

        python remove_intentory_items.py -i nircam -p p -s jw01022

"""

import argparse
import os
from jwql.utils.utils import get_config


def run(instrument, prev_or_thumb, str_to_exclude):
    """The main function. Locates the inventory file using config.json, opens
    it, and removes any lines containing ``str_to_exclude``.

    Parameters
    ----------
    instrument : str
        Name of instrument, all lowercase. e.g. 'nircam'

    prev_or_thumb : str
        Either 'p', which specifies to work on the preview image inventory file,
        or 't', indicating to work on the thumbnail inventory file.

    str_to_exclude : str
        Any lines in the inventory file contianing this string will be removed.
    """
    config = get_config()

    if prev_or_thumb == 'p':
        basedir = config['preview_image_filesystem']
        filename = f'preview_image_inventory_{instrument}.txt'
    elif prev_or_thumb == 't':
        basedir = config['thumbnail_filesystem']
        filename = f'thumbnail_inventory_{instrument}.txt'
    filename = os.path.join(basedir, filename)

    newlines = []
    fobj = open(filename, 'r')
    count = 0
    while True:
        count += 1

        # Get next line from file
        line = fobj.readline()

        # if line is empty
        # end of file is reached
        if not line:
            break

        if str_to_exclude not in line:
            newlines.append(line)
    fobj.close()

    os.remove(filename)

    newfile = open(filename, 'w')
    newfile.writelines((newlines))
    newfile.close()


def define_options(parser=None, usage=None, conflict_handler='resolve'):
    """Add command line options

    Parrameters
    -----------
    parser : argparse.parser
        Parser object

    usage : str
        Usage string

    conflict_handler : str
        Conflict handling strategy

    Returns
    -------
    parser : argparse.parser
        Parser object with added options
    """
    if parser is None:
        parser = argparse.ArgumentParser(usage=usage, conflict_handler=conflict_handler)

    parser.add_argument('-i', '--instrument', type=str, default=None, choices=['niriss', 'nircam', 'nirspec', 'miri', 'fgs'], help='Instrument.  (default=%(default)s)')
    parser.add_argument('-p', '--prev_or_thumb', type=str, default=None, choices=['p', 't'], help='Work on preview images (p) or thumbnails (t)')
    parser.add_argument('-s', '--str_to_exclude', type=str, help='String controlling which entries are removed.')
    return parser


if __name__ == '__main__':
    parser = define_options()
    args = parser.parse_args()

    run(args.instrument, args.prev_or_thumb, args.str_to_exclude)
