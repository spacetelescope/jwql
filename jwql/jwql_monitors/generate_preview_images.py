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

    - Matthew Bourque
    - Bryan Hilbert


Use
---

    This script is intended to be executed as such:

    ::

        python generate_preview_images.py
"""

import argparse
import glob
import logging
import multiprocessing
import os
import re

import matplotlib.pyplot as plt
import numpy as np

from jwql.utils import permissions
from jwql.utils.constants import (IGNORED_SUFFIXES,
                                  JWST_INSTRUMENT_NAMES_SHORTHAND,
                                  NIRCAM_LONGWAVE_DETECTORS,
                                  NIRCAM_SHORTWAVE_DETECTORS
                                  )
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.protect_module import lock_module
from jwql.utils.preview_image import Level3PreviewImage, PreviewImage
from jwql.utils.utils import get_config, filename_parser, remove_duplicate_files
from jwql.utils.monitor_utils import update_monitor_table, initialize_instrument_monitor

# Size of NIRCam inter- and intra-module chip gaps
SW_MOD_GAP = 1387  # pixels = int(43 arcsec / 0.031 arcsec/pixel)
LW_MOD_GAP = 741  # pixels = int(46 arcsec / 0.062 arcsec/pixel)
SW_DET_GAP = 145  # pixels = int(4.5 arcsec / 0.031 arcsec/pixel)
FULLX = 2048  # Width of the full detector
FULLY = 2048  # Height of the full detector

SETTINGS = get_config()


def array_coordinates(channelmod, detector_list, lowerleft_list):
    """Create an appropriately sized ``numpy`` array to contain the
    mosaic image given the channel and module of the data.

    Parameters
    ----------
    channelmod : str
        Indicator of the NIRCam channel/module of the data.
        Options are:
        ``LW`` - for longwave channel data
        ``SWA`` - for shortwave A module only (4 detectors) data
        ``SWB`` - for shortwave B module only (4 detectors) data
        ``SW`` - for shortwave both module data (8 detectors)

    detector_list : list
        List of detectors used in data to be simulated

    lowerleft_list : list
        Each element is a tuple giving the (x, y) coordinates
        corresponding to the lower left corner of the aperture within
        the full frame detector. These values come from the
        ``SUBSTRT1`` and 2 values in the file headers.

    Returns
    -------
    xdim : int
        Length of the output array needed to contain all detectors' data

    ydim : int
        Height of the output array needed to contain all detectors' data

    module_lowerlefts : dict
        Dictionary giving the ``(x, y)`` coordinate in the coordinate
        system of the full module(s) where the lower left corner of the
        data from a given detector will be placed. (e.g.
        ``NRCA1: (1888, 1888)`` means that the data from detector
        ``NRCA1`` should be placed into
        ``[1888: 1888+y_dim_of_data, 1888: 1888+x_dim_of_data]`` within
        the final array (which has total dimensions of ``(xdim, ydim)``
    """

    # Create dictionary of lower left pixel values for each
    # detector as it sits in the MODULE. B1-B4 values here will
    # need to have sw_mod_gap added to their x coordinates in
    # order to translate to the full A and B module coordinate system.
    # The only case where LW data will be in this function is where
    # both detectors are used, so set A5/B5 coordinates to be in
    # the full module A and B coordinate system. Note that these
    # tuples are (x,y), NOT (y,x)
    ashort = ["NRCA1", "NRCA2", "NRCA3", "NRCA4"]
    bshort = ["NRCB1", "NRCB2", "NRCB3", "NRCB4"]
    module_lowerlefts = {"NRCA1": (0, 0),
                         "NRCA2": (0, FULLY + SW_DET_GAP),
                         "NRCA3": (FULLX + SW_DET_GAP, 0),
                         "NRCA4": (FULLX + SW_DET_GAP, FULLY + SW_DET_GAP),
                         "NRCB1": (FULLX + SW_DET_GAP, FULLY + SW_DET_GAP),
                         "NRCB2": (FULLX + SW_DET_GAP, 0),
                         "NRCB3": (0, FULLY + SW_DET_GAP),
                         "NRCB4": (0, 0),
                         "NRCA5": (0, 0),
                         "NRCB5": (FULLX + LW_MOD_GAP, 0)}

    # If both module A and B are used, then shift the B module
    # coordinates to account for the intermodule gap
    if channelmod == "SW":
        mod_delta = (FULLX * 2 + SW_DET_GAP + SW_MOD_GAP, 0)
        for b_detector in bshort:
            module_lowerlefts[b_detector] = tuple([sum(x) for x in
                                                  zip(module_lowerlefts[b_detector],
                                                      mod_delta)])

    # The only subarrays we need to worry about are the SW SUBXXX
    # All other subarrays are on a single detector.
    # All we need to do is find the lower left values for NRCA1 and/or NRCB4.
    # From that we can calculate the rest. Also, if observing with both
    # A and B modules, only full frame is allowed, so no need to worry about
    # subarrays in both modules simultaneously.
    subx = 1
    suby = 1
    if 'SW' in channelmod:
        detector_list = np.array(detector_list)
        a1 = detector_list == 'NRCA1'
        b4 = detector_list == 'NRCB4'

        lowerleft_list = np.array(lowerleft_list)
        if np.sum(a1) == 1:
            subx, suby = lowerleft_list[a1][0]
        elif np.sum(b4) == 1:
            subx, suby = lowerleft_list[b4][0]
        else:
            missing_a14 = "SW data provided, but neither NRCA1 nor NRCB4 are present."
            logging.error(missing_a14)
            raise ValueError(missing_a14)

    # Adjust the lower left positions of the apertures within
    # the module(s) in the case of subarrays
    if ((subx != 1) | (suby != 1)):
        subarr_delta = {"NRCA1": (0, 0),
                        "NRCA2": (0, 0 - suby),
                        "NRCA3": (0 - subx, 0),
                        "NRCA4": (0 - subx, 0 - suby),
                        "NRCB1": (0 - subx, 0 - suby),
                        "NRCB2": (0 - subx, 0),
                        "NRCB3": (0, 0 - suby),
                        "NRCB4": (0, 0)}

        for det in ashort + bshort:
            module_lowerlefts[det] = tuple([sum(x) for x in zip(module_lowerlefts[det],
                                                                subarr_delta[det])])

    # Dimensions of array to hold all data
    # Adjust dimensions of individual detector for subarray if necessary
    aperturex = FULLX - (subx - 1)
    aperturey = FULLY - (suby - 1)

    # Full module(s) dimensions
    if channelmod in ['SWA', 'SWB']:
        xdim = 2 * aperturex + SW_DET_GAP
        ydim = 2 * aperturey + SW_DET_GAP
    elif channelmod == 'SW':
        xdim = 4 * aperturex + 2 * SW_DET_GAP + SW_MOD_GAP
        ydim = 2 * aperturey + SW_DET_GAP
    elif channelmod == 'LW':
        xdim = 2 * aperturex + LW_MOD_GAP
        ydim = aperturey

    return xdim, ydim, module_lowerlefts


def check_existence(filename, outdir):
    """Given a list of fits files, determine if a preview image has
    already been created in ``outdir``.

    Parameters
    ----------
    filename : str
        fits filename from which preview image will be
        generated

    outdir : str
        Directory that will contain the preview image if it exists

    Returns
    -------
    exists : bool
        ``True`` if preview image exists, ``False`` if it does not
    """
    filename = os.path.split(filename)[1]
    search_string = filename.split('.fits')[0] + '*jpg'

    current_files = glob.glob(os.path.join(outdir, search_string))
    if len(current_files) > 0:
        return True
    else:
        return False


def create_dummy_filename(filelist):
    """Create a dummy filename indicating the detectors used to create
    the mosaic. Check the list of detectors used to determine the proper
    text to substitute into the initial filename.

    Parameters
    ----------
    filelist : list
        List of filenames containing the data used to create the mosaic.
        It is assumed these filenames follow JWST filenaming
        conventions.

    Returns
    -------
    dummy_name : str
        The first filename in ``filelist`` is modified, such that the
        detector name is replaced with text indicating the source of the
        mosaic data.
    """

    det_string_list = []
    modules = []
    for filename in filelist:
        indir, infile = os.path.split(filename)
        parsed_filename = filename_parser(infile)
        if parsed_filename['recognized_filename']:
            det_string = parsed_filename['detector']
        else:
            # If filename_parser() does not recognize the file, skip it
            logging.warning((f'While using {infile} to create a dummy filename in create_dummy_filename(), the '
                             'filename parser failed.'))
            continue
        det_string_list.append(det_string)
        modules.append(det_string[3].upper())

    # Previous sorting means that either all of the
    # input files are LW, or all are SW. So we can check any
    # file to determine LW vs SW
    if '5' in det_string_list[0]:
        suffix = "NRC_LW_MOSAIC"
    else:
        moda = modules.count('A')
        modb = modules.count('B')
        if moda > 0:
            if modb > 0:
                suffix = "NRC_SWALL_MOSAIC"
            else:
                suffix = "NRC_SWA_MOSAIC"
        else:
            if modb > 0:
                suffix = "NRC_SWB_MOSAIC"
    dummy_name = filelist[0].replace(det_string_list[0], suffix)

    return dummy_name


def create_mosaic(filenames):
    """If an exposure comprises data from multiple detectors read in all
    the appropriate files and create a mosaic so that the preview image
    will show all the data together.

    Parameters
    ----------
    filenames : list
        List of filenames to be combined into a mosaic

    Returns
    -------
    mosaic_filename : str
        Name of fits file containing the mosaicked data
    """

    # Use preview_image to load data and create difference image
    # for each detector. Save in a list
    data = []
    detector = []
    data_lower_left = []
    for filename in filenames:
        image = PreviewImage(filename, "SCI")  # Now have image.data, image.dq
        data_dim = len(image.data.shape)
        if data_dim == 4:
            diff_im = image.difference_image(image.data)
        else:
            diff_im = image.data
        data.append(diff_im)
        file_info = filename_parser(filename)
        if file_info['recognized_filename']:
            detector.append(file_info['detector'].upper())
        else:
            # If filename_parser() does not recognize the file, skip it.
            logging.warning((f'While running create_mosaic() using {file_list[0]}, '
                             'filename_parser() failed to recognize the file pattern.'))
            pass
        data_lower_left.append((image.xstart, image.ystart))

    # Make sure SW and LW data are not being mixed. Create the
    # appropriately sized numpy array to hold all the data based
    # on the channel, module, and subarray size
    mosaic_channel = find_data_channel(detector)
    full_xdim, full_ydim, full_lower_left = array_coordinates(mosaic_channel, detector,
                                                              data_lower_left)

    # Create the array to hold all the data
    datashape = data[0].shape
    datadim = len(datashape)
    if datadim == 2:
        full_array = np.zeros((1, full_ydim, full_xdim)) * np.nan
    elif datadim == 3:
        full_array = np.zeros((datashape[0], full_ydim, full_xdim)) * np.nan
    else:
        raise ValueError('Difference image for {} must be either 2D or 3D.'.format(filenames[0]))

    # Place the data from the individual detectors in the appropriate
    # places in the final image
    for pixdata, detect in zip(data, detector):
        x0, y0 = full_lower_left[detect]
        if datadim == 2:
            yd, xd = pixdata.shape
            full_array[0, y0: y0 + yd, x0: x0 + xd] = pixdata
        elif datadim == 3:
            ints, yd, xd = pixdata.shape
            full_array[:, y0: y0 + yd, x0: x0 + xd] = pixdata

    # Create associated DQ array and set unpopulated pixels to be skipped
    # in preview image scaling
    full_dq = create_dq_array(full_xdim, full_ydim, full_array[0, :, :], mosaic_channel)

    return full_array, full_dq


def create_dq_array(xd, yd, mosaic, module):
    """Create DQ array that goes with the mosaic image. Set unpopulated
    pixels to be skipped in preview image scaling. Same for the
    reference pixels for all detectors

    Parameters
    ----------
    xd : int
        X-coordinate dimension of the DQ array

    yd : int
        Y-coordinate dimension of the DQ array

    mosaic : obj
        2D ``numpy`` array containing the mosaic image

    module : str
        Module used for mosaic. Options are ``LW``,`` SW``, ``SWA``,
        ``SWB``

    Returns
    -------
    dq : obj
        2D ``numpy`` array containing the DQ array. Pixels that are
        ``True`` are considered science pixels and are used when
        scaling the preview image. Pixels that are ``False`` are
        skipped.
    """

    # Create array
    dq = np.ones((yd, xd), dtype="bool")

    # Flag inter-chip and inter-module pixels as False
    dq[np.isnan(mosaic)] = 0

    # Flag reference pixels as False

    # Present in all cases other than subarrays
    if xd >= FULLX:
        dq[0:4, :] = 0
        dq[:, 0:4] = 0
        dq[2044:2048, :] = 0
        dq[:, 2044:2048] = 0

        if module == "LW":
            lwb_lower = FULLX + LW_MOD_GAP
            dq[:, lwb_lower:lwb_lower + 4] = 0
            dq[:, lwb_lower + 2044:lwb_lower + 2048] = 0

        if module in ["SWA", "SWB", "SW"]:
            # Present for full frame single module or both modules
            lowerval = FULLX + SW_DET_GAP
            dq[lowerval: lowerval + 4, :] = 0
            dq[(lowerval + 2044):, :] = 0
            dq[:, lowerval: lowerval + 4] = 0
            dq[:, (lowerval + 2044):(lowerval + 2048)] = 0

        if module == "SW":
            # Present only if both modules are used (full frame)
            modb_lower = lowerval + FULLX + SW_MOD_GAP
            dq[:, modb_lower:(modb_lower + 4)] = 0
            dq[:, (modb_lower + 2044):(modb_lower + 2048)] = 0
            modb_upper = modb_lower + FULLX + SW_DET_GAP
            dq[:, modb_upper:(modb_upper + 4)] = 0
            dq[:, (modb_upper + 2044):(modb_upper + 2048)] = 0

    else:
        # Subarrays: expand the pixels flagged due to chip gaps
        # by one row and column
        nan_indexes = np.where(np.isnan(mosaic))
        match = nan_indexes[0] == yd - 1
        vert_xmin = np.min(nan_indexes[1][match])
        vert_xmax = vert_xmin + SW_DET_GAP - 1

        match2 = nan_indexes[1] == xd - 1
        horiz_ymin = np.min(nan_indexes[0][match2])
        horiz_ymax = horiz_ymin + SW_DET_GAP - 1

        dq[:, vert_xmin - 4:vert_xmin] = 0
        dq[:, vert_xmax + 1:vert_xmax + 5] = 0
        dq[horiz_ymin - 4:horiz_ymin, :] = 0
        dq[horiz_ymax + 1:horiz_ymax + 5, :] = 0

    return dq


def define_options(parser=None, usage=None, conflict_handler='resolve'):
    """
    """
    if parser is None:
        parser = argparse.ArgumentParser(usage=usage, conflict_handler=conflict_handler)

    parser.add_argument('--overwrite', action='store_true', default=None, help='If set, existing preview images will be re-created and overwritten.')
    parser.add_argument('-p', '--programs', nargs='+', type=int, help='List of program IDs to generate preview images for. If omitted, all programs will be done.')
    parser.add_argument('--level3_only', action='store_true', help='Create preview images for level 3 files only.')
    return parser


def detector_check(detector_list, search_string):
    """Search a given list of detector names for the provided regular
    expression sting.

    Parameters
    ----------
    detector_list : list
        List of detector names (e.g. ``NRCA5``)

    search_string : str
        Regular expression string to use for search

    Returns
    -------
    total : int
        Number of detectors in ``detector_list`` that match
        ``search_string``
    """

    pattern = re.compile(search_string, re.IGNORECASE)
    match = [pattern.match(detector) for detector in detector_list]
    total = np.sum(np.array([m is not None for m in match]))

    return total


def find_data_channel(detectors):
    """Using a list of detectors, identify the channel(s) that the data
    are from.

    Parameters
    ----------
    detectors : list
        List of detector names

    Returns
    -------
    channel : str
        Identifier noting which channels the given detectors are in.
        Can be ``SWA`` for shortwave, module A only, ``SWB`` for
        shortwave, module B only, ``SW``, for shortwave modules A and B,
        and ``LW`` for longwave.
    """

    # Check the detector names for all files.
    nrc_swa_total = detector_check(detectors, "NRCA[1-4]")
    nrc_swb_total = detector_check(detectors, "NRCB[1-4]")
    nrc_lw_total = detector_check(detectors, "NRC[AB]5")

    both_channels = "Can't mix NIRCam SW and LW data in same mosaic."
    if nrc_swa_total != 0:
        if nrc_lw_total != 0:
            raise ValueError(both_channels)
        else:
            if nrc_swb_total != 0:
                channel = "SW"
            else:
                channel = "SWA"
    else:
        if nrc_swb_total != 0:
            if nrc_lw_total != 0:
                raise ValueError(both_channels)
            else:
                channel = "SWB"
        else:
            if nrc_lw_total != 0:
                channel = "LW"
            else:
                raise ValueError("No NIRCam SW nor LW data")
    return channel


def get_base_output_name(filename_dict):
    """Returns the base output name used for preview images and
    thumbnails.

    Parameters
    ----------
    filename_dict : dict
        A dictionary containing parsed filename parts via
        ``filename_parser``

    Returns
    -------
    base_output_name : str
        The base output name, e.g. ``jw96090001002_03101_00001_nrca2_rate``
    """

    base_output_name = 'jw{}{}{}_{}{}{}_{}_'.format(
        filename_dict['program_id'], filename_dict['observation'],
        filename_dict['visit'], filename_dict['visit_group'],
        filename_dict['parallel_seq_id'], filename_dict['activity'],
        filename_dict['exposure_id'])

    return base_output_name


@log_fail
@log_info
def generate_preview_images(overwrite, programs=None, level3_only=False):
    """The main function of the ``generate_preview_image`` module.
    See module docstring for further details.

    Parameters
    ----------
    overwrite : bool
        If True, any existing preview images and thumbnails are overwritten

    programs : list
        List of program ID numbers (e.g. 1068, 01220) for which to generate preview
        images. If None (the default), preview images are generated for all programs.

    level3_only : bool
        If True, create preview images only for level 3 files
    """
    # Get a list of programs to create preview images for. First, generate a list of all
    # possible programs. We can compare any user inputs to this list, and if there are no
    # user inputs, then use this entire list.
    all_programs = [os.path.basename(item) for item in glob.glob(os.path.join(SETTINGS['filesystem'], 'public', 'jw*'))]
    all_programs.extend([os.path.basename(item) for item in glob.glob(os.path.join(SETTINGS['filesystem'], 'proprietary', 'jw*'))])

    # Remove any repeats due to programs being listed in public and proprietary dirs at the same time.
    all_programs = list(set(all_programs))

    if programs is None:
        program_list = all_programs
    else:
        if not isinstance(programs, list):
            raise ValueError(f'program_list must be a list. In this call, it is {type(program_list)}')
        program_list = []
        for prog in programs:
            jwprog = f'jw{str(prog).zfill(5)}'
            if jwprog in all_programs:
                program_list.append(jwprog)
            else:
                logging.info(f'Program {prog} not present in filesystem. Excluding.')

    if len(program_list) > 0:
        # Sort into descending order
        program_list = sorted(program_list, reverse=True)
    else:
        no_prog_message = f'Empty list of programs. No preview images to be made.'
        logging.info(no_prog_message)
        raise ValueError(no_prog_message)

    # Process programs in parallel
    pool = multiprocessing.Pool(processes=int(SETTINGS['cores']))
    program_list = [(element, overwrite, level3_only) for element in program_list]
    results = pool.starmap(process_program, program_list)
    pool.close()
    pool.join()

    # Filter the nested list in results into separate lists of preview
    # images and thumbnail images
    full_preview_files = []
    full_thumbnail_files = []
    for r in results:
        full_preview_files.extend(r[0])
        full_thumbnail_files.extend(r[1])

    # Complete logging:
    logging.info("Completed.")


def group_filenames(filenames):
    """Given a list of JWST filenames, group together files from the
    same exposure. These files will share the same ``program_id``,
    ``observation``, ``visit``, ``visit_group``, ``parallel_seq_id``,
    ``activity``, ``exposure``, and ``suffix``. Only the ``detector``
    will be different. Currently only NIRCam files for a given exposure
    will be grouped together. For other instruments multiple files for
    a given exposure will be kept separate from one another and no
    mosaic will be made.  Stage 3 files will remain as individual
    files, and will not be grouped together with any other files.

    Parameters
    ----------
    filenames : list
        list of filenames

    Returns
    -------
    grouped : list
        grouped list of filenames where each element is a list and
        contains the names of filenames with matching exposure
        information.
    """

    # Some initializations
    grouped, matched_names = [], []
    filenames.sort()

    # Loop over each file in the list of good files
    for filename in filenames:

        # Holds list of matching files for exposure
        subgroup = []

        # Generate string to be matched with other filenames
        filename_dict = filename_parser(os.path.basename(filename))
        if not filename_dict['recognized_filename']:
            logging.warning((f'While running generate_preview_images.group_filenames() on {filename}, the '
                             'filename_parser() failed to recognize the file pattern.'))
            break

        # If the filename was already involved in a match, then skip
        if filename not in matched_names:

            # For stage 3 filenames, treat individually
            if 'stage_3' in filename_dict['filename_type']:
                matched_names.append(filename)
                subgroup.append(filename)

            # Group together stage 1 and 2 filenames
            elif filename_dict['filename_type'] == 'stage_1_and_2':

                # Determine detector naming convention
                if filename_dict['detector'].upper() in NIRCAM_SHORTWAVE_DETECTORS:
                    detector_str = 'NRC[AB][1234]'
                elif filename_dict['detector'].upper() in NIRCAM_LONGWAVE_DETECTORS:
                    detector_str = 'NRC[AB]5'
                else:  # non-NIRCam detectors
                    detector_str = filename_dict['detector'].upper()

                # Build pattern to match against
                base_output_name = get_base_output_name(filename_dict)
                match_str = '{}{}_{}.fits'.format(base_output_name, detector_str, filename_dict['suffix'])
                match_str = os.path.join(os.path.dirname(filename), match_str)
                pattern = re.compile(match_str, re.IGNORECASE)

                # Try to match the substring to each good file
                for file_to_match in filenames:
                    if pattern.match(file_to_match) is not None:
                        matched_names.append(file_to_match)
                        subgroup.append(file_to_match)

            else:
                # filename_dict['filename_type'] may be 'guider' or 'time_series', for instance. Treat individually.
                matched_names.append(filename)
                subgroup.append(filename)

        if len(subgroup) > 0:
            grouped.append(subgroup)

    return grouped


def preview_img_from_file(fname, file_info, preview_output_directory, thumbnail_output_directory):
    """Wrapper around functions for creating preview images from various file types

    Parameter
    ---------
    fname : str
        Filename

    file_info : dict
        Results from calling filename_parser on fname

    preview_output_directory : str
        Path in which to save the preview images

    thumbnail_output_directory : str
        Path in which to save the thumbnail images
    """
    # All stage 2 files and i2d.fits files
    if 'stage_3' not in file_info['filename_type'] and "_x1d" not in fname:
        try:
            # Stage 1/2 file
            img = PreviewImage(fname, "SCI")
            img.clip_percent = 0.01
            img.set_scaling()
            img.cmap = 'viridis'
            img.output_format = 'jpg'
            img.preview_output_directory = preview_output_directory
            img.thumbnail_output_directory = thumbnail_output_directory

            # Create a thumbnail for rate or dark files only. Create preview
            # images for all filetypes
            if 'rate.fits' in fname or 'dark.fits' in fname:
                img.make_image(max_img_size=8, create_thumbnail=True)
                logging.debug('\tCreated preview image and thumbnail for: {}'.format(fname))
            else:
                img.make_image(max_img_size=8, create_thumbnail=False)
                logging.debug('\tCreated preview image for: {}'.format(fname))

            return img.preview_images, img.thumbnail_images

        except (ValueError, AttributeError) as error:
            logging.warning(error)
            return (None, None)

    elif 'stage_3' not in file_info['filename_type'] and "_x1d" in fname:
        try:
            # Stage 2 x1ds, we build spectra from datamodels extension is None
            img = PreviewImage(fname, None)
            img.preview_output_directory = preview_output_directory

            # Rate or Dark images make thumbnails for program
            # Here we just need to make the x1d spectrum figures.
            img.make_spectrum_image()
            logging.debug('\tCreated preview image for: {}'.format(fname))

            return img.preview_images, img.thumbnail_images

        except (ValueError, AttributeError) as error:
            logging.warning(error)
            return (None, None)

    else:
        # Stage 3 fits file - create thumbnails for all level 3 products
        img = Level3PreviewImage(fname, create_thumbnail=file_info['create_thumbnail'],
                                 preview_output_directory=preview_output_directory,
                                 thumbnail_output_directory=thumbnail_output_directory,
                                 wfss_nbrightest_sources=2
                                 )
        if img.figures_created:
            return img.preview_images, img.thumbnail_images
        else:
            return (None, None)


def process_program(program, overwrite, level3_only):
    """Generate preview images and thumbnails for the given program.

    Parameters
    ----------
    program : str
        The program identifier (e.g. ``88600``)
    overwrite : bool
        If False, skip over preview images/thumbnails that already exist.
        Only create images that do not currenlty exist. If True, create
        preview_images and thumbnails for all input files, regardless of
        whether the images already exist.
    level3_only : bool
        If True, create preview images for level 3 files only

    Returns
    -------
    preview_image_files : list
        List of preview image filenames
    thumbnail_files : list
        List of thumbnail image filenames
    """

    logging.info('')
    logging.info('Processing {}'.format(program))

    # Gather files to process
    if not level3_only:
        filenames = glob.glob(os.path.join(SETTINGS['filesystem'], 'public', program, 'jw*/*.fits'))
        filenames.extend(glob.glob(os.path.join(SETTINGS['filesystem'], 'proprietary', program, 'jw*/*.fits')))
    else:
        filenames = []

    # Add level 3 files
    filenames.extend(glob.glob(os.path.join(SETTINGS['filesystem'], 'public', program, 'L3/*/*/*.fits')))
    filenames.extend(glob.glob(os.path.join(SETTINGS['filesystem'], 'proprietary', program, 'L3/*/*/*.fits')))

    # Add level 3 ecsv files for TSO observations
    filenames.extend(glob.glob(os.path.join(SETTINGS['filesystem'], 'public', program, 'L3/*/*/*whtlt.ecsv')))
    filenames.extend(glob.glob(os.path.join(SETTINGS['filesystem'], 'proprietary', program, 'L3/*/*/*whtlt.ecsv')))
    filenames.extend(glob.glob(os.path.join(SETTINGS['filesystem'], 'public', program, 'L3/*/*/*phot.ecsv')))
    filenames.extend(glob.glob(os.path.join(SETTINGS['filesystem'], 'proprietary', program, 'L3/*/*/*phot.ecsv')))

    # Remove any repeated filenames
    filenames = remove_duplicate_files(filenames)

    # remove specific "ignored" suffix files (currently "original" and "stream")
    filenames = [filename for filename in filenames if os.path.splitext(filename.split('_')[-1])[0] not in IGNORED_SUFFIXES]

    # Remove guiding files, as these are not currently visible in JWQL anyway
    filtered_filenames = []
    for filename in filenames:
        parsed = filename_parser(filename)
        if parsed['recognized_filename']:
            if 'guider_mode' not in parsed:
                filtered_filenames.append(filename)
        else:
            logging.warning((f'While running generate_preview_images.process_program() on {filename}, the '
                             'filename_parser() failed to recognize the file pattern.'))
    filenames = filtered_filenames

    # Sort in order to help keep track of thumbnail production for level 3 files
    # By sorting in reverse, we'll preferentially make thumbnails for x1d files if present,
    # which seems like a nice way to distinguish from level 2 thumbanils.
    filenames = sorted(filenames, reverse=True)

    # Move segm.fits files to the end of the list, because we don't really want thumbnails from
    # these, unless there are no other suffixes available for a given rootname
    filenames.sort(key=lambda f: f.endswith('_segm.fits'))

    # Put cal.fits and rate.fits files at the beginning of the list, in order to avoid a bug
    # where if the rateints preview image is created first, check_existence will skip the
    # rate file.
    filenames.sort(key=lambda f: not f.endswith('cal.fits'))
    filenames.sort(key=lambda f: not f.endswith('rate.fits'))

    # Dictionary to track whether a thumbnail has been created for a level 3 rootname
    # Keys are rootnames, values are booleans describing whether a thumbail image has been made
    thumbs = {}

    new_preview_counter = 0
    existing_preview_counter = 0
    thumbnail_files = []
    preview_image_files = []
    for filename in filenames:

        logging.debug(f'Working on {filename}')

        # Determine the save location
        parsed = filename_parser(filename)
        if parsed['recognized_filename']:
            identifier = f'jw{parsed["program_id"]}'
        else:
            # In this case, the filename_parser failed to recognize the filename
            identifier = os.path.basename(filename).split('.')[0]
            logging.warning((f'While running generate_preview_images.process_program() on filtered filename {filename}, the '
                             'filename_parser() failed to recognize the file pattern.'))
        preview_output_directory = os.path.join(SETTINGS['preview_image_filesystem'], identifier)
        thumbnail_output_directory = os.path.join(SETTINGS['thumbnail_filesystem'], identifier)

        # Check to see if the preview images already exist and skip if they do
        if not overwrite:
            # If overwrite is False, we create preview images only for files that
            # don't have them yet.
            file_exists = check_existence(filename, preview_output_directory)

            if file_exists:
                logging.debug("\tJPG already exists for {}, skipping.".format(filename))
                existing_preview_counter += 1
                continue
        else:
            # If overwrite is set to True, then we always create a new image
            file_exists = False

        # Create the output directories if necessary
        if not os.path.exists(preview_output_directory):
            os.makedirs(preview_output_directory)
            permissions.set_permissions(preview_output_directory)
            logging.info('\tCreated directory {}'.format(preview_output_directory))
        if not os.path.exists(thumbnail_output_directory):
            os.makedirs(thumbnail_output_directory)
            permissions.set_permissions(thumbnail_output_directory)
            logging.info('\tCreated directory {}'.format(thumbnail_output_directory))

        # For level 3 files, add a key to the filename_parser results, describing
        # whether or not to create a thumbnail image
        if 'stage_3' in parsed['filename_type']:
            root = filename[0:filename.rfind('_')]
            if root in thumbs:
                if thumbs[root]:
                    parsed['create_thumbnail'] = False
                else:
                    parsed['create_thumbnail'] = True
            else:
                parsed['create_thumbnail'] = True

        # Create the nominal preview image and thumbnail
        try:
            prev_ims, thumb_ims = preview_img_from_file(filename, parsed, preview_output_directory, thumbnail_output_directory)
            if 'stage_3' in parsed['filename_type']:
                thumbs[root] = True

            if prev_ims is not None:
                new_preview_counter += 1
                thumbnail_files.extend(thumb_ims)
                preview_image_files.extend(prev_ims)

        except (ValueError, AttributeError, KeyError, FileNotFoundError) as error:
            logging.warning(f'For file {filename}: {error}')
        finally:
            # Make sure all figures are closed.
            plt.close('all')

    logging.info(f"Created {new_preview_counter} new preview images.")
    logging.info(f"Skipped {existing_preview_counter} previously-existing preview images.")

    return preview_image_files, thumbnail_files


@lock_module
def protected_code(overwrite, programs, level3_only):
    """Protected code ensures only 1 instance of module will run at any given time

    Parameters
    ----------
    overwrite : bool
        If True, any existing preview images and thumbnails are overwritten

    programs : list
        List of program numbers to run

    level3_only : bool
        Create preview images for level 3 files only
    """
    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)

    generate_preview_images(overwrite, programs=programs, level3_only=level3_only)
    update_monitor_table(module, start_time, log_file)


if __name__ == '__main__':
    parser = define_options()
    args = parser.parse_args()
    protected_code(args.overwrite, args.programs, args.level3_only)
