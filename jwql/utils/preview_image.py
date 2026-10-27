#! /usr/bin/env python

"""
Create a preview image from a fits file containing an observation.

This module creates and saves a "preview image" from a fits file that
contains a JWST observation. Data from the user-supplied ``extension``
of the file are read in, along with the ``PIXELDQ`` extension if
present. For each integration in the exposure, the first group is
subtracted from the final group in order to create a difference image.
The lower and upper limits to be displayed are defined as the
``clip_percent`` and ``(1. - clip_percent)`` percentile signals.
``matplotlib`` is then used to display a linear- or log-stretched
version of the image, with accompanying colorbar. The image is then
saved.

Authors:
--------

    - Bryan Hilbert

Use:
----

    This module can be imported as such:

    ::

        from jwql.preview_image.preview_image import PreviewImage
        im = PreviewImage(my_file, "SCI")
        im.clip_percent = 0.01
        im.scaling = 'log'
        im.output_format = 'jpg'
        im.make_image()
"""

from glob import glob
import json
import logging
import math
import numbers
import os
from pathlib import Path
import re
import warnings

from astropy import constants as const
from astropy.io import fits
from astropy.stats import sigma_clip
from astropy.table import Table
from astropy.visualization import LinearStretch, LogStretch, MinMaxInterval, SqrtStretch
from astropy.visualization.mpl_normalize import ImageNormalize
import numpy as np
import pandas as pd
import pysiaf

from jwst import datamodels

from jwql.edb.utils import get_ta_centroids
from jwql.utils import permissions
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.multistripe_tools import soss_uncal_multistripe_check
from jwql.utils.utils import filesystem_path, get_config

# Use the 'Agg' backend to avoid invoking $DISPLAY
import matplotlib
matplotlib.use('Agg')
from matplotlib.patches import Circle, Rectangle  # noqa
import matplotlib.pyplot as plt  # noqa
import matplotlib.colors as colors  # noqa
from mpl_toolkits.axes_grid1 import make_axes_locatable  # no_qa

if not ON_READTHEDOCS:
    from jwst.datamodels import dqflags

if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    CONFIGS = get_config()


class PreviewImage():
    """An object for generating and saving preview images, used by
    ``generate_preview_images``.

    Attributes
    ----------
    clip_percent : float
        The amount to sigma clip the input data by when scaling the
        preview image.  Default is 0.01.
    cmap : str
        The colormap used by ``matplotlib`` in the preview image.
        Default value is ``viridis``.
    data : obj
        The data used to generate the preview image.
    dq : obj
        The DQ data used to generate the preview image.
    file : str
        The filename to generate the preview image from.
    output_format : str
        The format to which the preview image is saved.  Options are
        ``jpg`` and ``thumb``
    preview_output_directory : str or None
        The output directory to which the preview image is saved.
    scaling : str
        The scaling used in the preview image.  Default is ``log``.
    thumbnail_output_directory : str or None
        The output directory to which the thumbnail is saved.

    Methods
    -------
    difference_image(data)
        Create a difference image from the data
    find_limits(data, pixmap, clipperc)
        Find the min and max signal levels after clipping by
        ``clipperc``
    get_data(filename, ext)
        Read in data from the given ``filename`` and ``ext``
    make_figure(image, integration_number, min_value, max_value, scale, maxsize, thumbnail)
        Create the ``matplotlib`` figure
    make_image(max_img_size)
        Main function
    save_image(fname, thumbnail)
        Save the figure
    """

    def __init__(self, filename, extension):
        """Initialize the class.

        Parameters
        ----------
        filename : str
            Name of fits file containing data
        extension : str
            Extension name to be read in
        """
        self.clip_percent = 0.01
        self.cmap = 'viridis'
        self.file = filename
        self.output_format = 'jpg'
        self.preview_output_directory = None
        self.scaling = 'log'
        self.thumbnail_output_directory = None
        self.preview_images = []
        self.thumbnail_images = []

        # Read in file
        if "_x1d" in filename:
            self.model = self.get_spectra_data(self.file)
        else:
            self.data, self.dq = self.get_data(self.file, extension)

    def determine_map_file(self, header):
        """Determine which file contains the map of non-science pixels given a
        file header

        Parameters
        ----------
        header : astropy.io.fits.header
            Header object from an HDU object
        """
        if header['INSTRUME'] == 'MIRI':
            # MIRI imaging files use the external MIRI non-science map. Note that MIRI_CORONCAL and
            # MIRI_LYOT observations also have 'mirimage' in the filename. We deal with this in
            # crop_to_subarray()
            if 'CORONMSK' not in header:
                self.nonsci_map_file = (os.path.join(CONFIGS['outputs'], 'non_science_maps', 'mirimage_non_science_map.fits'))
            elif header['CORONMSK'] == '4QPM_1065':
                self.nonsci_map_file = (os.path.join(CONFIGS['outputs'], 'non_science_maps', 'miri4qpm_1065_non_science_map.fits'))
            elif header['CORONMSK'] == '4QPM_1140':
                self.nonsci_map_file = (os.path.join(CONFIGS['outputs'], 'non_science_maps', 'miri4qpm_1140_non_science_map.fits'))
            elif header['CORONMSK'] == '4QPM_1550':
                self.nonsci_map_file = (os.path.join(CONFIGS['outputs'], 'non_science_maps', 'miri4qpm_1550_non_science_map.fits'))
            elif header['CORONMSK'] in ['LYOT', 'LYOT_2300']:
                self.nonsci_map_file = (os.path.join(CONFIGS['outputs'], 'non_science_maps', 'mirilyot_non_science_map.fits'))

        elif header['INSTRUME'] == 'NIRSPEC':
            if 'NRSIRS2' in header['READPATT']:
                # IRS2 mode arrays are very different sizes between uncal and i2d files. For the uncal,
                # use the external non-science map. The i2d files we can treat like i2d files from the
                # other NIR detectors.
                if header['DETECTOR'] == 'NRS1':
                    self.nonsci_map_file = (os.path.join(CONFIGS['outputs'], 'non_science_maps', 'nrs1_irs2_non_science_map.fits'))
                elif header['DETECTOR'] == 'NRS2':
                    self.nonsci_map_file = (os.path.join(CONFIGS['outputs'], 'non_science_maps', 'nrs2_irs2_non_science_map.fits'))
            else:
                self.nonsci_map_file = None
        else:
            self.nonsci_map_file = None

    def difference_image(self, data):
        """
        Create a difference image from the data. Use last group minus
        first group in order to maximize signal to noise. With 4D
        input, make a separate difference image for each integration.

        Parameters
        ----------
        data : obj
            4D ``numpy`` ``ndarray`` array of floats

        Returns
        -------
        result : obj
            3D ``numpy`` ``ndarray`` containing the difference image(s)
            from the input exposure
        """
        return data[:, -1, :, :] - data[:, 0, :, :]

    def find_limits(self, data):
        """
        Find the minimum and maximum signal levels after clipping the
        top and bottom ``clipperc`` of the pixels.

        Parameters
        ----------
        data : obj
            2D numpy ndarray of floats

        Returns
        -------
        results : tuple
            Tuple of floats, minimum and maximum signal levels
        """
        # Ignore any pixels that are NaN
        finite = np.isfinite(data)

        # If all pixels are NaN then we're sunk. Scale
        # from 0 to 1.
        if not np.any(finite):
            logging.info('No pixels with finite signal. Scaling from 0 to 1')
            return (0., 1.)

        # Combine maps of science pixels and finite pixels
        # self.dq can have values of 1 (science pixel) or 0 (non-science pixel)
        pixmap = (self.dq & finite > 0)

        # If all non-science pixels are NaN then we're sunk. Scale
        # from 0 to 1.
        if not np.any(pixmap):
            logging.info('No good science pixels with finite signal. Scaling from 0 to 1')
            return (0., 1.)

        sorted_pix = np.sort(data[pixmap], axis=None)

        # Determine how many pixels to clip off of the high and low ends
        nelem = np.sum(pixmap)
        numclip = np.int32(self.clip_percent * nelem)

        # Determine min and max scaling levels
        minval = sorted_pix[numclip]
        maxval = sorted_pix[-numclip - 1]
        return (minval, maxval)

    def get_spectra_data(self, filename):
        """
        Read in one dimensional spectral data from level 2 pipeline products.

        Parameters
        ----------
        filename : str
            Name of fits file containing data

        Returns
        -------
        data : jwst.datamodel
            JWST Datamodel representation of fits file.
        """

        if os.path.isfile(filename):
            model = datamodels.open(filename)
        else:
            raise FileNotFoundError('WARNING: {} does not exist!'.format(filename))

        return model

    def get_data(self, filename, ext):
        """
        Read in the data from the given file and extension.  Also find
        how many rows/cols of reference pixels are present.

        Parameters
        ----------
        filename : str
            Name of fits file containing data
        ext : str
            Extension name to be read in

        Returns
        -------
        data : obj
            Science data from file. A 2-, 3-, or 4D numpy ndarray
        dq : obj
            2D ``ndarray`` boolean map of reference pixels. Science
            pixels flagged as ``True`` and non-science pixels are
            ``False``
        """
        if os.path.isfile(filename):
            extnames = []
            with fits.open(filename) as hdulist:
                if 'uncal' in filename:
                    hdulist = soss_uncal_multistripe_check(hdulist)
                for exten in hdulist:
                    try:
                        extnames.append(exten.header['EXTNAME'])
                    except KeyError:
                        pass
                if ext in extnames:
                    dimensions = len(hdulist[ext].data.shape)
                    if dimensions == 4:
                        if hdulist[ext].data.shape[1] > 1:
                            data = hdulist[ext].data[:, [0, -1], :, :].astype(float)
                        else:
                            # For ramps with a single group, remove that dimension so
                            # that we do not create a difference image
                            data = hdulist[ext].data[:, 0, :, :].astype(float)
                    else:
                        data = hdulist[ext].data.astype(float)
                    yd, xd = data.shape[-2:]
                    try:
                        self.units = f"{hdulist[ext].header['BUNIT']}  "
                    except KeyError:
                        self.units = ''
                else:
                    raise ValueError('WARNING: no {} extension in {}!'.format(ext, filename))

                # For files that have no DQ extension, we get a map of the non-science
                # pixels from a dedicated map file. Getting this info from the DQ extension
                # doesn't work for uncal and i2d files, nor MIRI rate files.
                self.determine_map_file(hdulist[0].header)

                if (('uncal' in filename) or ('i2d' in filename)):
                    # uncal files have no DQ extensions, so we can't get a map of non-science pixels from the
                    # data itself.
                    if 'miri' in filename:
                        if 'mirimage' in filename:
                            dq = self.nonsci_from_file()
                            dq = crop_to_subarray(dq, hdulist[0].header, xd, yd)
                            dq = expand_for_i2d(dq, xd, yd)
                        else:
                            # For MIRI MRS/LRS data, we don't worry about non-science pixels, so create a map where all
                            # pixels are good.
                            dq = np.ones((yd, xd), dtype="bool").astype(bool)
                    elif 'nrs' in filename:
                        if 'NRSIRS2' in hdulist[0].header['READPATT']:
                            # IRS2 mode arrays are very different sizes between uncal and i2d files. For the uncal,
                            # use the external non-science map. The i2d files we can treat like i2d files from the
                            # other NIR detectors.
                            if 'uncal' in filename:
                                dq = self.nonsci_from_file()
                                # ISR2 data are always full frame, so no need to crop to subarray
                                # and since we are guaranteed to have an uncal file, no need to expand for i2d
                            elif 'i2d' in filename:
                                dq = create_nir_nonsci_map()
                                dq = crop_to_subarray(dq, hdulist[0].header, xd, yd)
                                dq = expand_for_i2d(dq, xd, yd)
                        else:
                            # NIRSpec observations that do not use IRS2 use the "standard" NIR detector non-science map.
                            # i.e. 4 outer rows and columns are refernece pixels
                            dq = create_nir_nonsci_map()
                            dq = crop_to_subarray(dq, hdulist[0].header, xd, yd)
                            dq = expand_for_i2d(dq, xd, yd)
                    else:
                        # All NIRCam, NIRISS, and FGS observations also use the "standard" NIR detector non-science map.
                        dq = create_nir_nonsci_map()
                        dq = crop_to_subarray(dq, hdulist[0].header, xd, yd)
                        dq = expand_for_i2d(dq, xd, yd)
                elif 'rate' in filename:
                    # For rate/rateints images all we need to worry about is MIRI imaging files. For those we use
                    # the external non-science map, because the pipeline does not add the NON_SCIENCE flags
                    # to the MIRI DQ extensions until the data are flat fielded, which is after the rate
                    # files have been created.
                    if 'mirimage' in filename:
                        dq = self.nonsci_from_file()
                        dq = crop_to_subarray(dq, hdulist[0].header, xd, yd)
                        dq = expand_for_i2d(dq, xd, yd)
                    else:
                        # For everything other than MIRI imaging, we get the non-science map from the
                        # DQ array in the file.
                        dq = self.get_nonsci_map(hdulist, extnames, xd, yd)
                else:
                    # For all file suffixes other than uncal and rate/rateints, we get the non-science map
                    # from the DQ array in the file.
                    dq = self.get_nonsci_map(hdulist, extnames, xd, yd)

                # Collect information on aperture location within the
                # full detector. This is needed for mosaicking NIRCam
                # detectors later.
                try:
                    self.xstart = hdulist[0].header['SUBSTRT1']
                    self.ystart = hdulist[0].header['SUBSTRT2']
                    self.xlen = hdulist[0].header['SUBSIZE1']
                    self.ylen = hdulist[0].header['SUBSIZE2']
                except KeyError:
                    logging.warning('SUBSTR and SUBSIZE header keywords not found')

        else:
            raise FileNotFoundError('WARNING: {} does not exist!'.format(filename))

        if dq.shape != data.shape[-2:]:
            raise ValueError(f'DQ array does not have the same shape as the data in {filename}')

        # In some cases (e.g. MIRI suabrray TA files) all pixels will be flagged as non-science.
        # In cases where dq shows all non-science pixels, let's zero out the flags and use all
        # the pixels for image scaling.
        if np.sum(dq) == 0:
            dq = np.ones(dq.shape, dtype=int)

        return data, dq

    def get_nonsci_map(self, hdulist, extensions, xdim, ydim):
        """Create a map of non-science pixels for a given HDUList. If there is no DQ
        extension in the HDUList, assume all pixels are science pixels.

        Parameters
        ----------
        hdulist : astropy.io.fits.HDUList
            HDUList object from a fits file

        extensions : list
            List of extension names in the HDUList

        xdim : int
            Number of columns in data array. Only used if there is no DQ extension

        ydim : int
            Number of rows in the data array. Only used if there is no DQ extension

        Returns
        -------
        dq : numpy.ndarray
            2D boolean array giving locations of non-science pixels
        """
        if 'DQ' in extensions:
            dq = hdulist['DQ'].data

            # For files with multiple integrations (rateints, calints), chop down the
            # DQ array to a single frame, since the non-science pixels will be the same
            # in all integrations
            if len(dq.shape) == 3:
                dq = dq[0, :, :]
            elif len(dq.shape) == 4:
                dq = dq[0, 0, :, :]

            dq = (dq & (dqflags.pixel['NON_SCIENCE'] | dqflags.pixel['REFERENCE_PIXEL']) == 0)
        else:
            # If there is no DQ extension in the HDUList, then we create a dq map where we assume
            # that all of the pixels are science pixels
            dq = np.ones((ydim, xdim), dtype=bool)
        return dq

    def make_figure(self, image, integration_number, min_value, max_value,
                    scale, maxsize=8, thumbnail=False):
        """
        Create the matplotlib figure of the image

        Parameters
        ----------
        image : obj
            2D ``numpy`` ``ndarray`` of floats

        integration_number : int
            Integration number within exposure

        min_value : float
            Minimum value for display

        max_value : float
            Maximum value for display

        scale : str
            Image scaling (``log``, ``linear``)

        maxsize : int
            Size of the longest dimension of the output figure (inches)

        thumbnail : bool
            True to create a thumbnail image, False to create the full
            preview image

        Returns
        -------
        result : obj
            Matplotlib Figure object
        """

        # Check the input scaling
        if scale not in ['linear', 'log']:
            raise ValueError('WARNING: scaling option {} not supported.'.format(scale))

        # Set the figure size
        yd, xd = image.shape
        ratio = yd / xd
        if xd >= yd:
            xsize = maxsize
            ysize = maxsize * ratio
        else:
            ysize = maxsize
            xsize = maxsize / ratio

        # Create figure and axis object
        if thumbnail:
            self.fig, ax = plt.subplots(figsize=(3, 3))
        else:
            self.fig, ax = plt.subplots(figsize=(xsize, ysize))

        # Get color scale and tick values depending on the scaling
        if scale == 'log':
            # Shift data so everything is positive
            shiftdata = image - min_value + 1
            shiftmin = 1
            shiftmax = max_value - min_value + 1

            # Generate tick labels
            tickvals = np.logspace(np.log10(shiftmin), np.log10(shiftmax), 5)
            tlabelflt = tickvals + min_value - 1

            # Image object
            cax = ax.imshow(shiftdata,
                            norm=colors.LogNorm(vmin=shiftmin,
                                                vmax=shiftmax),
                            cmap=self.cmap)

        elif scale == 'linear':
            # Generate tick labels
            tickvals = np.linspace(min_value, max_value, 5)
            tlabelflt = tickvals
            cax = ax.imshow(image, clim=(min_value, max_value), cmap=self.cmap)

        # Invert y axis in all cases
        plt.gca().invert_yaxis()

        # For preview images, add colorbar, and create tick labels for it
        if not thumbnail:
            # Adjust the number of digits after the decimal point
            # in the colorbar labels based on the signal range
            delta = tlabelflt[-1] - tlabelflt[0]
            if delta >= 100:
                dig = 0
            elif ((delta < 100) & (delta >= 10)):
                dig = 1
            elif ((delta < 10) & (delta >= 1)):
                dig = 2
            elif delta < 1:
                dig = 3
            else:
                dig = 2
            format_string = "%.{}f".format(dig)
            tlabelstr = [format_string % number for number in tlabelflt]

            # Catch images where all pixel values are zero. e.g. trapsfilled files
            if delta == 0:
                delta = 0.01

            # For cases where the the distance between min_value and max_value is very small,
            # adjust the tick labels to avoid having the same number label for all ticks
            zeros = np.log10(np.abs(delta))
            if zeros < -3:
                # For cases where the signal range is only 1e-3, use scientific notation for
                # the tick labels
                tlabelstr = [f"{num:.3e}" for num in tlabelflt]

            xyratio = xsize / ysize
            if xyratio < 1.6:
                # For apertures that are taller than they are wide, square, or that are wider than
                # they are tall but still reasonably close to square, put the colorbar on the right
                # side of the image.

                # Some magic numbers arrived at through testing aspect ratios for all apertures
                if xyratio > 0.4:
                    cb_width = 0.05
                else:
                    cb_width = 0.05 * 0.4 / xyratio

                upper_x_anchor = 0.02
                if xyratio < 0.1:
                    upper_x_anchor = 0.12

                cbax = self.fig.add_axes([ax.get_position().x1 + upper_x_anchor,
                                          ax.get_position().y0,
                                          cb_width,
                                          ax.get_position().height
                                          ])
                cbar = self.fig.colorbar(cax, cax=cbax, orientation='vertical', ticks=tickvals)

                cbar.ax.yaxis.minorticks_off()
                cbar.ax.set_yticklabels(tlabelstr)
                cbar.ax.set_ylabel(self.units, labelpad=7, rotation=270)
            else:
                # For apertures that are significantly wider than they are tall, put the colorbar
                # under the image.

                # Adjustment to prevent negative colorbar width
                if xyratio < 2:
                    xyratio = 2.5

                # Again, some magic numbers controlling the positioning and height of the
                # colorbar, based on testing.
                lower_y_anchor = 0. - (xyratio / 14.5)
                cb_height = 0.07 * (np.log2(xyratio) - 1)

                cbax = self.fig.add_axes([ax.get_position().x0,
                                          ax.get_position().y0 + lower_y_anchor,
                                          ax.get_position().width,
                                          cb_height])
                cbar = self.fig.colorbar(cax, cax=cbax, ticks=tickvals, orientation='horizontal')

                cbar.ax.xaxis.minorticks_off()
                cbar.ax.set_xticklabels(tlabelstr)
                cbar.ax.set_xlabel(self.units, labelpad=7, rotation=0)

            # Set text sizes
            ax.set_xlabel('Pixels', fontsize=maxsize * 5. / 4)
            ax.set_ylabel('Pixels', fontsize=maxsize * 5. / 4)
            ax.tick_params(labelsize=maxsize)
            plt.rcParams.update({'axes.titlesize': 'small'})
            plt.rcParams.update({'font.size': maxsize * 5. / 4})
            plt.rcParams.update({'axes.labelsize': maxsize * 5. / 4})
            plt.rcParams.update({'ytick.labelsize': maxsize * 5. / 4})
            plt.rcParams.update({'xtick.labelsize': maxsize * 5. / 4})

        elif thumbnail:
            # If creating a thumbnail, make the axes invisible
            plt.axis('off')
            cax.axes.get_xaxis().set_visible(False)
            cax.axes.get_yaxis().set_visible(False)

        # If preview image, set a title
        if not thumbnail:
            filename = os.path.split(self.file)[-1]
            ax.set_title(filename + ' Int: {}'.format(int(integration_number)))

    def make_image(self, max_img_size=8.0, create_thumbnail=False):
        """The main function of the ``PreviewImage`` class.

        Parameters
        ----------
        max_img_size : float
            Image size in the largest dimension

        create_thumbnail : bool
            If True, a thumbnail image is created and saved.
        """

        shape = self.data.shape

        if len(shape) == 4:
            # Create difference image(s)
            diff_img = self.difference_image(self.data)
        elif len(shape) < 4:
            diff_img = self.data

        # If there are multiple integrations in the file,
        # work on one integration at a time from here onwards
        ndim = len(diff_img.shape)
        if ndim == 2:
            diff_img = np.expand_dims(diff_img, axis=0)
        nint, ny, nx = diff_img.shape

        # Create plots only for a subset of the integrations
        integration_range = self.get_integration_range(nint)

        for i in integration_range:
            frame = diff_img[i, :, :]

            # Find signal limits for the display
            minval, maxval = self.find_limits(frame)

            # Set NaN values to zero, so that those pixels
            # do not appear as big white splotches in the jpgs
            # after matplotlib downsamples/averages
            frame = nan_to_zero(frame)

            # Create preview image matplotlib object
            indir, infile = os.path.split(self.file)
            suffix = '_integ{}.{}'.format(i, self.output_format)
            if self.preview_output_directory is None:
                outdir = indir
            else:
                outdir = self.preview_output_directory
            outfile = os.path.join(outdir, infile.split('.')[0] + suffix)
            self.make_figure(frame, i, minval, maxval, self.scaling.lower(),
                             maxsize=max_img_size, thumbnail=False)
            self.save_image(outfile, thumbnail=False)
            plt.close(self.fig)
            self.preview_images.append(outfile)

            # Create thumbnail image matplotlib object, only for the
            # first integration
            if i == 0 and create_thumbnail:
                if self.thumbnail_output_directory is None:
                    outdir = indir
                else:
                    outdir = self.thumbnail_output_directory
                outfile = os.path.join(outdir, infile.split('.')[0] + suffix)
                self.make_figure(frame, i, minval, maxval, self.scaling.lower(),
                                 maxsize=max_img_size, thumbnail=True)
                self.save_image(outfile, thumbnail=True)
                plt.close(self.fig)
                self.thumbnail_images.append(self.thumbnail_filename)

    def get_integration_range(self, nint):
        """
        Determine integration range for integration files

        Parameters
        ----------
        nint : int
            Number of file integrations

        Returns
        -------
        intgration_range : range
            Range object of integration steps
        """
        max_preview_integrations = 10
        integration_range = np.linspace(0, nint-1, num=min(max_preview_integrations, nint), dtype=int)

        return integration_range

    def make_spectrum_image(self):
        """
        Make level 2 x1d quicklook spectrum images
        """

        indir, infile = os.path.split(self.file)

        if self.preview_output_directory is None:
            outdir = indir
        else:
            outdir = self.preview_output_directory

        exp_type = self.model.meta.exposure.type

        if "x1dints.fits" in infile:
            if exp_type == "NIS_SOSS":
                self.make_nis_soss_spectrum(outdir, infile)
            elif exp_type == "NRS_BRIGHTOBJ" or exp_type == "NRC_TSGRISM" or exp_type == "MIR_LRS-SLITLESS":
                targname = self.model.meta.target.proposer_name
                nint =  self.model.spec[0].spec_table.shape[0]
                integration_range = self.get_integration_range(nint)

                for i in integration_range:
                    wavelength = self.model.spec[0].spec_table[i]["wavelength"]
                    flux = self.model.spec[0].spec_table[i]["flux"]
                    suffix = '_integ{}.{}'.format(i, self.output_format)

                    outfile = os.path.join(outdir, infile.replace(".fits", suffix))
                    self.make_spectrum_figure(wavelength, flux, targname, integration_num=i)
                    self.save_image(outfile)

                    self.preview_images.append(outfile)
                    self.thumbnail_images.append(None)

                    plt.close(self.fig)
        else:
            if "WFSS" in exp_type:
                brightest_idx = find_brightest_wfss_sources(self.model, level=2)

                # As with the level 3 WFSS preview images, let's skip the brightest
                # source, which is often a saturated star, and use the second brightest
                if len(brightest_idx) > 1:
                    # If there is more than one source in the file, use the second brightest
                    flux = self.model.spec[0].spec_table.FLUX[1, :]
                    wavelength = self.model.spec[0].spec_table.WAVELENGTH[1, :]
                elif len(brightest_idx) == 1:
                    # If there is only one source in the file, use it
                    flux = self.model.spec[0].spec_table.FLUX[0, :]
                    wavelength = self.model.spec[0].spec_table.WAVELENGTH[0, :]
                elif len(brightest_idx) == 0:
                    # If there are no sources in the file, use dummy values
                    flux = [0., 0.]
                    wavelength = [0., 1.0]

            else:
                flux = self.model.spec[0].spec_table.FLUX
                wavelength = self.model.spec[0].spec_table.WAVELENGTH

            targname = self.model.meta.target.proposer_name

            suffix = '_integ0.{}'.format(self.output_format)
            outfile = os.path.join(outdir, infile.replace(".fits", suffix))

            self.make_spectrum_figure(wavelength, flux, targname)
            self.save_image(outfile)

            plt.close(self.fig)

            self.preview_images.append(outfile)
            self.thumbnail_images.append(None)

    def make_nis_soss_spectrum(self, outdir, infile, maxsize=8):
        """
        Make figure that contains level 2 x1dint NIRISS SOSS data
        """

        targname = self.model.meta.target.proposer_name
        nint_per_order = np.array([order.spec_table.shape[0] for order in self.model.spec])

        if nint_per_order.all():
            nint = int(np.unique(nint_per_order)[0])
            integration_range = self.get_integration_range(nint)
        else:
            raise ValueError("INTEGRATION NUMBERS ARE DIFFERENT PER ORDER")

        for i in integration_range:
            self.fig, ax = plt.subplots(ncols=1, nrows=len(nint_per_order), figsize=(maxsize, maxsize))
            self.fig.suptitle(f'{self.model.meta.filename} Int: {i}\n{targname}')
            for order, axis in zip(self.model.spec, ax):
                wavelength = order.spec_table["wavelength"][i]
                flux = order.spec_table["flux"][i]

                clipped = sigma_clip_ignore_nan(flux, sigma=9)
                vmax = np.nanmax(clipped) * 1.1
                vmin = np.nanmin(clipped)

                if vmin >= 0:
                    vmin = vmin * 0.9
                else:
                    vmin = vmin * 1.1

                try:
                    wavelength_units = order.spec_table.columns["wavelength"].unit
                    flux_units = order.spec_table.columns["flux"].unit
                except AttributeError:
                    wavelength_units = "um"
                    flux_units = None

                axis.plot(wavelength, flux, color='blue')
                axis.set_xlabel(f'Wavelength ({wavelength_units})')
                axis.set_ylabel(f'Flux ({flux_units})')
                axis.set_ylim(vmin, vmax)

                axis.set_title(f'SOSS Order: {order.spectral_order}')
                axis.grid(ls="--")


            suffix = '_integ{}.{}'.format(i, self.output_format)
            outfile = os.path.join(outdir, infile.replace(".fits", suffix))

            self.preview_images.append(outfile)
            self.thumbnail_images.append(None)

            plt.tight_layout()
            self.save_image(outfile)
            plt.close(self.fig)

    def make_spectrum_figure(self, wavelength, flux, targname, integration_num=None, maxsize=8):
        """
        Make figure that contains level 2 x1d data.
        """
        # Get the x1d data
        self.fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(maxsize, maxsize))

        # Determine plot range
        clipped = sigma_clip_ignore_nan(flux, sigma=9)
        vmax = np.nanmax(clipped) * 1.1
        vmin = np.nanmin(clipped)
        if vmin >= 0:
            vmin = vmin * 0.9
        else:
            vmin = vmin * 1.1

        try:
            wavelength_units = self.model.spec[0].spec_table.columns["wavelength"].unit
            flux_units = self.model.spec[0].spec_table.columns["flux"].unit
        except AttributeError:
            wavelength_units = None
            flux_units = None

        ax.plot(wavelength, flux, color='blue')
        ax.set_xlabel(f'Wavelength ({wavelength_units})')
        ax.set_ylabel(f'Flux ({flux_units})')
        ax.set_ylim(vmin, vmax)
        if isinstance(integration_num, numbers.Number):
            ax.set_title(f'{self.model.meta.filename} Int: {integration_num}\n{targname}')
        else:
            ax.set_title(f'{self.model.meta.filename}\n{targname}')
        ax.grid(ls="--")

    def nonsci_from_file(self):
        """Read in a map of non-science/reference pixels from a fits file

        Parameters
        ----------
        filename : str
            Name of fits file to be read in.

        Returns
        -------
        map : numpy.ndarray
            2D boolean array of pixel values
        """
        map = fits.getdata(self.nonsci_map_file)
        return map.astype(bool)

    def save_image(self, fname, thumbnail=False):
        """
        Save an image in the requested output format and sets the
        appropriate permissions

        Parameters
        ----------
        image : obj
            A ``matplotlib`` figure object

        fname : str
            Output filename

        thumbnail : bool
            True if saving a thumbnail image, false for the full
            preview image.
        """

        if "_x1d" in fname:
            plt.savefig(fname)
        else:
            plt.savefig(fname, bbox_inches='tight', pad_inches=0)

        permissions.set_permissions(fname)

        # If the image is a thumbnail, rename to '.thumb'
        if thumbnail:
            self.thumbnail_filename = fname.replace('.jpg', '.thumb')
            os.rename(fname, self.thumbnail_filename)
            logging.info('\tSaved image to {}'.format(self.thumbnail_filename))
        else:
            logging.info('\tSaved image to {}'.format(fname))
            self.thumbnail_filename = None

    def set_scaling(self):
        """Determine the scaling (e.g. log, linear) to use for the preview image.
        NIRSpec WATA TA images and non-full-frame MIRI target acq images are set to linear,
        while everything else is set to log.
        """
        header = fits.getheader(self.file)
        self.scaling = 'log'
        if ((header['EXP_TYPE'] == 'NRS_WATA') & (header['SUBSIZE1'] == 32) & (header['SUBSIZE2'] == 32)):
            self.scaling = 'linear'
        if ((header['EXP_TYPE'] == 'MIR_TACQ') & (header['SUBARRAY'] != 'FULL')):
            self.scaling = 'linear'


def create_nir_nonsci_map():
    """Create a map of non-science pixels for a near-IR detector

    Returns
    -------
    arr : numpy.ndarray
        2D boolean array. Science pixels have a value of 1 and non-science pixels
        (reference pixels) have a value of 0.
    """
    arr = np.ones((2048, 2048), dtype=int)
    arr[0:4, :] = 0
    arr[:, 0:4] = 0
    arr[2044:, :] = 0
    arr[:, 2044:] = 0
    return arr.astype(bool)


def crop_to_subarray(arr, header, xdim, ydim):
    """Given a full frame array, along with a fits HDU header containing subarray
    information, crop the array down to the indicated subarray.

    Parameters
    ----------
    arr : numpy.ndarray
        2D array of data. Assumed to be full frame (2048 x 2048)

    header : astropy.io.fits.header
        Header from a single extension of a fits file

    xdim : int
        Number of columns in the corresponding data (not dq) array, in pixels

    ydim : int
        Number of rows in the corresponding data (not dq) array, in pixels

    Returns
    -------
    arr : numpy.ndarray
        arr, cropped down to the size specified in the header
    """
    # Pixel coordinates in the headers are 1-indexed. Subtract 1 to get them into
    # python's 0-indexed system
    try:
        xstart = header['SUBSTRT1'] - 1
        xlen = header['SUBSIZE1']
        ystart = header['SUBSTRT2'] - 1
        ylen = header['SUBSIZE2']
    except KeyError:
        # If subarray info is missing from the header, then we don't know which
        # part of the dq array to extract. Rather than raising an exception, let's
        # extract a portion of the dq array that is centered on the full frame
        # array, so that we can still create a preview image later.
        logging.info(f"No subarray location information in {header['FILENAME']}. Extracting a portion of the DQ array centered on the full frame.")
        arr_ydim, arr_xdim = arr.shape
        ystart = (arr_ydim // 2) - (ydim // 2)
        xstart = (arr_xdim // 2) - (xdim // 2)
        xlen = xdim
        ylen = ydim
    return arr[ystart: (ystart + ylen), xstart: (xstart + xlen)]


def expand_for_i2d(array, xdim, ydim):
    """Some file types, like i2d files, contain arrays with sizes that are different than
    those specified in the SUBSIZE header keywords. In those cases, we need to expand the
    input array from the official size to the actual size.

    Parameters
    ----------
    array : numpy.ndarray
        2D DQ array of booleans

    xdim : int
        Number of columns in the data whose dimensions we want ``array`` to have.
        (e.g. the dimensions of the i2d file)

    ydim : int
        Number of rows in the data whose dimensions we want ``array`` to have.
        (e.g. the dimensions of the i2d file)

    Returns
    -------
    new_array : numpy.ndarray
        2D array with dimensions of (ydim x xdim)
    """
    ydim_array, xdim_array = array.shape
    if ((ydim_array != ydim) or (xdim_array != xdim)):
        if (ydim_array != ydim):
            new_array_y = np.zeros((ydim, xdim_array), dtype=bool)  # Added rows/cols will be all zeros
            y_offset = abs((ydim - ydim_array) // 2)
            if (ydim_array < ydim):
                new_array_y[y_offset: (y_offset + ydim_array), :] = array
            elif (ydim_array > ydim):
                new_array_y = array[y_offset: (y_offset + ydim), :]
        else:
            new_array_y = array
        if (xdim_array != xdim):
            new_array_x = np.zeros((ydim, xdim), dtype=bool)  # Added rows/cols will be all zeros
            x_offset = abs((xdim - xdim_array) // 2)
            if (xdim_array < xdim):
                new_array_x[:, x_offset: (x_offset + xdim_array)] = new_array_y
            elif (xdim_array > xdim):
                new_array_x = new_array_y[:, x_offset: (x_offset + xdim)]
        else:
            new_array_x = new_array_y
        return new_array_x
    else:
        return array


def nan_to_zero(image):
    """Set any pixels with a value of NaN to zero

    Parameters
    ----------
    image : numpy.ndarray
        Array from which NaNs will be removed

    Returns
    -------
    image : numpy.ndarray
        Input array with NaNs changed to zero
    """
    nan = np.isnan(image)
    image[nan] = 0
    return image


class Level3PreviewImage():
    """An object for generating and saving a preview image from level 3 files.
    Used by``generate_preview_images``.
    """
    def __init__(self, filename, maxsize=8, preview_output_directory=None,
                 create_thumbnail=False, thumbnail_output_directory=None, min_range_for_logscale=1.,
                 wfss_nbrightest_sources=2):
        """Instantiate Level3PreviewImage object

        Parameters
        ----------
        filename : str
            Name of fits or ecsv file to create preview image for
        maxsize : float
            Size of the maximum dimension (inches) of the output preview image
        preview_output_directory : str
            Path to the base directory where preview images are saved
        create_thumbnail : bool
            Whether or not to create a thumbnail image as well as a preview image
        thumbnail_output_directory : str
            Path to the base directory where the thumbnail images are saved
        min_range_for_logscale : float
            max minus min value of data must be at least this much in order to use log scaling. If the
            difference is less, linear scaling is used.
        wfss_nbrightest_sources : int
            The number of sources to create preview images for in WFSS x1d or c1d files. Sources are
            organized by brightness, so the `wfss_nbrightest_sources` brightest sources will have
            preview images created.
        """
        self.filename = filename
        self.maxsize = maxsize
        self.output_format = 'jpg'
        self.preview_output_directory = preview_output_directory
        self.thumbnail_output_directory = thumbnail_output_directory
        self.create_thumbnail = create_thumbnail
        self.preview_images = []
        self.thumbnail_images = []
        self.threshold_for_nonsquare_pix = 0.15
        self.figures = []
        self.wfss_source_ids = []
        self.min_range_for_logscale = min_range_for_logscale
        self.wfss_nbrightest_sources = wfss_nbrightest_sources
        self.figures_created = True

        # Define colormap that shows NaNs as black
        self.cmap = plt.cm.viridis.copy()
        self.cmap.set_bad(color='black')

        # Read in the data
        self.get_data()

        # Fall back to the standard preview image and thumbnail output directory if a
        # directory is not given
        if preview_output_directory is None:
            try:
                self.preview_output_directory = os.path.join(CONFIGS["preview_image_filesystem"],
                                                             self.model.meta.filename[0:7])
            except AttributeError:
                self.preview_output_directory = os.path.join(CONFIGS["preview_image_filesystem"],
                                                             'jw' + self.metadata["program_id"])
        if thumbnail_output_directory is None:
            try:
                self.thumbnail_output_directory = os.path.join(CONFIGS["thumbnail_filesystem"],
                                                               self.model.meta.filename[0:7])
            except AttributeError:
                self.thumbnail_output_directory = os.path.join(CONFIGS["thumbnail_filesystem"],
                                                               'jw' + self.metadata["program_id"])

        if 'x1dints' in self.filename:
            # Time Series data from NIRCAM
            if self.exp_type == 'NRC_TSGRISM':
                self.tso_x1dints_plot()
            elif self.exp_type == 'MIR_LRS-SLITLESS':
                self.miri_lrs_slitless_x1dints_plot()
            elif self.exp_type == 'NIS_SOSS':
                self.niriss_soss_plot()
            elif self.exp_type == 'NRS_BRIGHTOBJ':
                self.miri_lrs_slitless_x1dints_plot()
        elif self.exp_type == 'NIS_AMI':
            if 'amilg' in self.filename:
                self.amilg_preview()
            elif 'ami-oi' in self.filename or 'aminorm-oi' in self.filename:
                self.ami_preview()
        elif 'whtlt.ecsv' in self.filename or 'phot.ecsv' in filename:
            self.tso_whitelight_curve()
        elif self.exp_type in ['NRS_MSASPEC', 'NRS_FIXEDSLIT', 'MIR_LRS-FIXEDSLIT'] and ('cal' in self.filename or
                                                                          'crf' in self.filename or
                                                                          's2d' in self.filename):
            self.fixed_slit_cal_crf_s2d()
        elif 'x1d' in self.filename and self.exp_type in ['NRS_MSASPEC',
                                                          'NRS_FIXEDSLIT',
                                                          'NRS_IFU',
                                                          'MIR_LRS-FIXEDSLIT'
                                                          ]:
            self.miri_lrs_fixed_slit_nirspec_ifu_x1d()
        elif 'x1d' in self.filename and self.exp_type == 'MIR_MRS':
            self.miri_mrs_x1d()
        elif ('x1d' in self.filename or 'c1d' in self.filename) and self.exp_type in ['NRC_WFSS', 'NIS_WFSS', 'MIRI_WFSS']:
            self.wfss_x1d()
        elif 's3d' in self.filename and self.exp_type in ['NRS_IFU', 'MIR_MRS']:
            self.nirspec_miri_ifu_s3d()
        elif (('i2d' in self.filename) and ('mask' in self.filename)):
            self.coron_i2d()
        elif (('i2d' in self.filename) or ('segm' in self.filename)):
            self.i2d_file()
        elif ('psfstack' in self.filename or 'psfalign' in self.filename or 'psfsub' in self.filename):
            self.psfstack_file()
        else:
            self.figures_created = False

        self.save_figures()

    def ami_preview(self):
        """Given a AmiOIModel datamodel instance, create a preview image. This function was
        taken from the jwst-pipeline notebooks repo
        """
        # Read the observables from the datamodel
        # Squared visibilities and uncertainties
        vis2 = self.model.vis2["VIS2DATA"]
        vis2_err = self.model.vis2["VIS2ERR"]

        # Closure phases and uncertainties
        t3phi = self.model.t3["T3PHI"]
        t3phi_err = self.model.t3["T3PHIERR"]

        # Construct baselines between the U and V coordinates of sub-apertures
        baselines = (self.model.vis2['UCOORD']**2 + self.model.vis2['VCOORD']**2)**0.5

        # Construct baselines between combinations of three sub-apertures
        u1 = self.model.t3['U1COORD']
        u2 = self.model.t3['U2COORD']
        v1 = self.model.t3['V1COORD']
        v2 = self.model.t3['V2COORD']
        u3 = -(u1 + u2)
        v3 = -(v1 + v2)
        baselines_t3 = []
        for k in range(len(u1)):
            B1 = np.sqrt(u1[k]**2 + v1[k]**2)
            B2 = np.sqrt(u2[k]**2 + v2[k]**2)
            B3 = np.sqrt(u3[k]**2 + v3[k]**2)

            # Use longest baseline of the three for plotting
            baselines_t3.append(np.max([B1, B2, B3]))
        baselines_t3 = np.array(baselines_t3)

        # Plot closure phases, squared visibilities against their baselines
        self.fig, (ax1, ax2) = plt.subplots(ncols=1, nrows=2, figsize=(8, 16))
        ax1.errorbar(baselines_t3, t3phi, yerr=t3phi_err, fmt="go")
        ax2.errorbar(baselines, vis2, yerr=vis2_err, fmt="go")
        ax1.set_xlabel(r"$B_{max}$ [m]", size=12)
        ax1.set_ylabel("Closure phase [deg]", size=12)
        ax1.set_title("Closure Phase", size=14)
        ax2.set_title("Squared Visibility", size=14)
        ax2.set_xlabel(r"$B_{max}$ [m]", size=12)
        ax2.set_ylabel("Squared Visibility", size=12)
        plt.suptitle(self.model.meta.filename, fontsize=16)
        ax1.set_ylim([-3.5, 3.5])
        ax2.set_ylim([0.5, 1.1])
        self.figures.append(self.fig)

    def amilg_preview(self):
        """Plot data, model, and residual from amilg.fits file
        """
        # Plot the data, model, residual
        norm = ImageNormalize(self.model.norm_centered_image[0],
                              interval=MinMaxInterval(),
                              stretch=SqrtStretch())
        fig, axs = plt.subplots(1, 3, figsize=(12, 5))
        axs[0].set_title('Normalized Data')
        im1 = axs[0].imshow(self.model.norm_centered_image[0], norm=norm, cmap=self.cmap)
        axs[1].set_title('Normalized Model')
        im2 = axs[1].imshow(self.model.norm_fit_image[0], norm=norm, cmap=self.cmap)
        axs[2].set_title('Normalized Residual (Data-Model)')
        im3 = axs[2].imshow(self.model.norm_resid_image[0], cmap=self.cmap)

        for im in [im1, im2, im3]:
            plt.colorbar(im, shrink=.95, location='bottom', pad=.05)
        for ax in axs:
            ax.axis('off')

        plt.suptitle(os.path.basename(firstfile))
        plt.tight_layout()
        self.figures.append(self.fig)

    def coron_i2d(self):
        """Create a preview image for coronagraphic i2d files. Show the coron image, and next to it, show the
        associated TA image, with an optional region of interest outlined. Also add text giving the calculated
        centroid value.
        """
        vmin = np.nanpercentile(self.model.data, 1)
        vmax = np.nanpercentile(self.model.data, 99)

        # If the percentile values above end up being identical, fall back to use the full range of the data
        if vmin == vmax:
            vmin = np.nanmin(self.model.data)
            vmax = np.nanmax(self.model.data)

        # Get basic figure properties
        yd, xd = self.model.data.shape
        aspect, colorbar_orient, figsize = \
            determine_figure_properties(xd, yd, threshold=self.threshold_for_nonsquare_pix,
                                        maxsize=self.maxsize)

        # In order to determine how many axes to include in the figure, we need to identify all
        # of the TA images associated with the i2d file. The TA filenames are listed in the
        # association file. So we first locate and read that in
        self.get_ta_filenames()
        num_ta = len(self.ta_files)

        # Arrange the images
        n_files = num_ta + 1
        ncols = 2
        nrows = math.ceil(n_files / ncols)

        figsize = (self.maxsize * 2, self.maxsize * nrows)
        self.fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize)

        if nrows == 1:
            axes = axes.reshape(1, -1)
        axes = axes.flatten()

        # Show the i2d file in the top left
        ax_i2d = axes[0]
        self.show_image_in_axis(ax_i2d, self.model.data, vmin, vmax, aspect, colorbar_orient, num_ticks=5)
        ax_i2d.set_title(self.model.meta.filename)

        # Get the TA centroid coordinates for each TA image. The function operates on one visit
        # at a time, so get a list of visit IDs associated with the TA images, and set up a
        # dictionary to hold mulitple centroid values per visit
        ta_visit_ids = [fits.getheader(ta_file)['VISIT_ID'] for ta_file in self.ta_files]
        ta_visit_ids = sorted(list(set(ta_visit_ids)))
        ta_centroids = {}

        # Keep track of how many TA files we have worked with per visit ID
        visit_id_counter = {}

        # Show each of the TA images, along with the ROI, if present
        for i, ta_file in enumerate(self.ta_files):
            index = i + 1

            ta_data = fits.getdata(ta_file)
            ta_vmin = np.nanpercentile(ta_data, 1)
            ta_vmax = np.nanpercentile(ta_data, 99)
            ta_yd, ta_xd = ta_data.shape
            ta_aspect, ta_colorbar_orient, _ = \
            determine_figure_properties(ta_xd, ta_yd, threshold=self.threshold_for_nonsquare_pix,
                                        maxsize=self.maxsize)
            self.show_image_in_axis(axes[index], ta_data, ta_vmin, ta_vmax, ta_aspect, ta_colorbar_orient, num_ticks=5)

            # Use pysiaf to get information about the subarray and/or ROI
            inst_siaf = pysiaf.Siaf(self.model.meta.instrument.name)
            ta_apername = fits.getval(ta_file, 'APERNAME', 0)
            roi_aper = inst_siaf[ta_apername]

            if self.model.meta.instrument.name.lower() == 'miri':
                # Use the header information to get the right pySIAF aperture objects
                readout_name = fits.getval(ta_file, 'SUBARRAY', 0)
                readout_aper = inst_siaf["MIRIM_" + readout_name]

                # Convert the corners and reference position to SCI coordinates and subtract 1 for
                # the pixel indexing convention
                ref_pt = readout_aper.det_to_sci(*roi_aper.reference_point("det"))
                corners = readout_aper.det_to_sci(*roi_aper.corners("det"))
                ref_pt = np.array(ref_pt) - 0.5
                corners = np.array(corners) - 0.5

            # Overplot the ROI for NIRCam. This will be the entire subarray, but the advantage here
            # is that the reference location is also shown
            elif self.model.meta.instrument.name.lower() == 'nircam':
                corners = roi_aper.corners("sci")
                corners = np.array(corners) - 0.5
                ref_pt = roi_aper.reference_point("sci")
                ref_pt = np.array(ref_pt) - 0.5

            # Plot the ROI as a Rectangular patch
            roi_box = Rectangle((corners[0][0], corners[1][0]), roi_aper.XSciSize, roi_aper.YSciSize,
                                lw=2, edgecolor='red', facecolor='none', alpha=0.75)
            axes[index].add_patch(roi_box)

            # Show the reference location as a +
            axes[index].scatter(ref_pt[0], ref_pt[1], color='red', marker='+', alpha=0.75, label='Ref pt')

            # Get information on the TA centroid from the EDB
            visit_id = fits.getheader(ta_file)['VISIT_ID']

            # If we don't have TA centroids from this Visit yet, then get them via MAST
            if visit_id not in ta_centroids:
                ta_centroids[visit_id] = get_ta_centroids(ta_file)

            # Determine which number TA file this is within the given visit, and use the
            # matching centroid values
            if visit_id not in visit_id_counter:
                visit_id_counter[visit_id] = 0

            centroid_x, centroid_y = ta_centroids[visit_id][visit_id_counter[visit_id]]
            visit_id_counter[visit_id] += 1

            # Now print the centroid values on the preview image
            # Centroid values are given relative to...ROI, I think? need to add the lower left corner coords to them
            x_det_cent = corners[0][0] + centroid_x
            y_det_cent = corners[1][0] + centroid_y
            axes[index].scatter([x_det_cent], [y_det_cent], color='orange', marker='+', label='centroid')
            title_str = f"{os.path.basename(ta_file)}: Centroid: ({x_det_cent:.2f}, {y_det_cent:.2f})"
            axes[index].set_title(title_str)
            axes[index].legend()

        # Hide unused subplots if odd number of images
        for i in range(n_files, len(axes)):
            axes[i].axis('off')

        # Set text sizes
        maxsize = self.maxsize
        ax_i2d.set_xlabel('Pixels', fontsize=maxsize * 5. / 4)
        ax_i2d.set_ylabel('Pixels', fontsize=maxsize * 5. / 4)
        ax_i2d.tick_params(labelsize=maxsize)
        #plt.rcParams.update({'axes.titlesize': 'small'})
        plt.rcParams.update({'font.size': maxsize * 5. / 4})
        plt.rcParams.update({'axes.labelsize': maxsize * 5. / 4})
        plt.rcParams.update({'ytick.labelsize': maxsize * 5. / 4})
        plt.rcParams.update({'xtick.labelsize': maxsize * 5. / 4})
        plt.tight_layout()
        self.figures.append(self.fig)

    def create_plot(self):
        """Create the 1D plot"""
        self.get_limits()

        # Create figure and axis object
        if self.thumbnail:
            self.fig, ax = plt.subplots(figsize=(3, 3))
        else:
            self.fig, ax = plt.subplots(figsize=(self.maxsize, self.maxsize))

        ax.plot(self.wavelength, self.signal, color='black')
        ax.set_xlabel(f'Wavelength ({self.wave_units})')
        ax.set_ylabel(f'Signal ({self.signal_units})')
        ax.set_xlim(self.min_wave, self.max_wave)
        ax.set_ylim(self.min_yval, self.max_yval)
        ax.set_title(os.path.filename(self.filename))
        plt.rcParams.update({'axes.titlesize': 'small'})
        plt.rcParams.update({'font.size': self.maxsize * 5. / 4})
        plt.rcParams.update({'axes.labelsize': self.maxsize * 5. / 4})
        plt.rcParams.update({'ytick.labelsize': self.maxsize * 5. / 4})
        plt.rcParams.update({'xtick.labelsize': self.maxsize * 5. / 4})


    def filter_coron_ta_files(self):
        """For NIRCam coron observations, there will be files listed as "target_acquisition"
        for all detectors. But the TA source is actually only in one detector. Filter out the
        files for the other detectors, so that we can ignore them.
        """
        # Keep only the ALONG files
        if self.model.meta.instrument.name.lower() == 'nircam':
            self.ta_files = [element for element in self.ta_files if 'nrcalong' in element]

            # Now throw out the TA_CONFIRM files, and keep only the first of the three
            # dithers in the TA files.
            ta_only = []
            for file in self.ta_files:
                header = fits.getheader(file)
                if ((header['EXP_TYPE'] == 'NRC_TACQ') and (header['EXPOSURE'] == '1')):
                    ta_only.append(file)
            self.ta_files = ta_only

    def find_wfss_source_ext(self, cal_hdu, source_id):
        """Given a source ID number, find the extension in the cal file where the source is located

        Parameters
        ----------
        cal_hdu : astropy.io.fits.HDUList
            *_cal.fits file HDUList

        source_id : int
            Source ID number

        Returns
        -------
        cal_ex_orders : dict
            Keys are the order numbers, values are the extension of the file that
            holds the data for that order number
        """
        # Get a list of SOURCE_IDs for all extensions. Set all non-SCI extension values to -999
        cal_source_ids = np.array([cal_hdu[ext].header['SOURCEID'] if cal_hdu[ext].header['EXTNAME'] == 'SCI'
                                  else -999 for ext in range(1, len(cal_hdu))])
        cal_orders = np.array([cal_hdu[ext].header['SPORDER'] if cal_hdu[ext].header['EXTNAME'] == 'SCI'
                                  else -999 for ext in range(1, len(cal_hdu))])

        # Get extension numbers for each order. Support arbitrary order numbers
        cal_ex_orders = {}
        source_idxs = np.where(cal_source_ids == source_id)[0]

        for source_idx in source_idxs:
            order = cal_orders[source_idx]
            cal_ex_orders[order] = source_idx + 1  # Add 1 to account for the primary header

        return cal_ex_orders

    def fixed_slit_cal_crf_s2d(self):
        """Create preview image for NIRSpec or MIRI fixed slit cal, crf, and s2d files
        """
        # MIRI slits are presented vertically in the data, while NIRSpec slits are
        # presented horizontally. If we have a MIRI file, we need to essentially swap
        # x and y figure size, orientation, etc
        inst = self.model.meta.instrument.name.lower()

        if 'cal' in self.model.meta.filename or 'crf' in self.model.meta.filename:
            num_nods = len(self.model.exposures)
            #figsize = figure_size[str(num_nods)]
            figsize = (12, 4 + (num_nods*2))
            aspect = "auto"
            colorbar_orient = "horizontal"

            if inst == 'miri':
                figsize = (figsize[::-1])
                colorbar_orient = "vertical"

            arrs = [self.model.exposures[i].data for i in range(num_nods)]
            titles = [f'{self.model.exposures[i].meta.instrument.detector}: Nod {self.model.exposures[i].meta.dither.position_number}' for i in range(num_nods)]

            # Clip brightest and dimmest 1% of pixels to find min and max values
            vmin = np.nanpercentile(self.model.exposures[0].data, 1)
            vmax = np.nanpercentile(self.model.exposures[0].data, 99)

            # If the data array is all NaNs, which we've seen in some msaspec files,
            # then set the vmin and vmax based on all data extensions
            if not np.isfinite(vmin):
                vmin, vmax = self.get_plot_range_mult_exposures()

            # For NIRSpec data, group the plots by detector
            if self.model.meta.instrument.name.lower() == 'nirspec':
                srt = np.argsort(np.array(titles))
                titles = list(np.array(titles)[srt])
                arrs = [arrs[i] for i in srt]

            # Add the filename to the title of the top-most plot
            titles[0] = f'{self.model.meta.filename}\n{titles[0]}'

        elif 's2d' in self.model.meta.filename:
            num_nods = 1
            #figsize = figure_size[str(num_nods)]
            figsize = (12, 4 + (num_nods*2))
            aspect = "auto"
            colorbar_orient = "horizontal"

            if inst == 'miri':
                figsize = (figsize[::-1])
                colorbar_orient = "vertical"

            arrs = [self.model.data]
            titles = [self.model.meta.filename]

            # Clip brightest and dimmest 1% of pixels to find min and max values
            vmin = np.nanpercentile(self.model.data, 1)
            vmax = np.nanpercentile(self.model.data, 99)

            if not np.isfinite(vmin):
                vmin = 0
                vmax = 1

        # Create figure
        self.fig, axes = plt.subplots(nrows=num_nods, ncols=1, figsize=figsize)#, constrained_layout=True)
        plt.tight_layout(pad=4.0)

        if inst == 'miri':
            self.fig, axes = plt.subplots(nrows=1, ncols=num_nods, figsize=figsize)#, constrained_layout=True)

        # For s2d files, there will be only one set of axes. We need to put this into
        # a numpy array so that we can iterate over it below.
        if not isinstance(axes, np.ndarray):
            axes = np.array([axes])

        # Looks like the units don't always make it into the datamodel (e.g. NIRSpec fixedslit crf)
        try:
            units = self.model.meta.bunit_data
        except AttributeError:
            #units = fits.getheader(self.filename, 1)['BUNIT']
            self.model.meta.bunit_data = fits.getheader(self.filename, 1)['BUNIT']

        for ax, arr, title in zip(axes, arrs, titles):
            colorbar_labelpad={'vertical': 15, 'horizontal': 3}

            # Show an image in each axis
            self.show_image_in_axis(ax, arr, vmin, vmax, aspect, colorbar_orient, num_ticks=5, colorbar_pad=0.5, colorbar_labelpad=colorbar_labelpad)
            ax.set_title(title)
            ax.set_xlabel("Pixels")
            ax.set_ylabel("Pixels")

        self.figures.append(self.fig)

    def get_data(self):
        """Read in self.filename
        """
        if '.fits' in self.filename:
            self.model = datamodels.open(self.filename)
            self.exp_type = self.model.meta.exposure.type

            try:
                self.wavelength_units = self.model.spec[0].spec_table.columns["wavelength"].unit
                self.flux_units = self.model.spec[0].spec_table.columns["flux"].unit
            except AttributeError:
                self.wavelength_units = None
                self.flux_units = None

            # I think everything in JWST is in Microns
            if self.wavelength_units is None:
                self.wavelength_units = 'Microns'

        elif 'whtlt.ecsv' in self.filename or 'phot.ecsv' in self.filename:
            # Top (usually) 15 lines contain metadata
            self.metadata = {'exp_type': 'None', 'filter': None, 'pupil': None,
                             'subarray': None, 'number_of_integrations': None,
                             'target_name': None}
            data_start_line = 0
            with open(self.filename, 'r') as f:
                for i, line in enumerate(f):
                    if line.strip().startswith('#'):
                        for key in self.metadata:
                            if key in line:
                                try:
                                    colon_loc = line.rindex(':')
                                    brace_loc = line.rindex('}')
                                    self.metadata[key] = line[colon_loc+2:brace_loc]
                                except ValueError:
                                    pass
                        # phot.ecsv files have units in the metadata
                        if 'net_aperture_sum' in line:
                            strt = line.rfind('unit: ')
                            ending = line.rfind(', datatype')
                            self.flux_units = line[strt+6: ending]
                    else:
                        data_start_line = i
                        break
            self.model = pd.read_csv(self.filename, header=data_start_line, delimiter=' ')
            self.num_ext = 1
            self.exp_type = self.metadata['exp_type']
            self.metadata['program_id'] = self.filename[2:7]

    def get_level2_contributing_files(self):
        """Get a list of the full paths to the level 2 files that are listed in the
        association file
        """
        self.contributing_files = {}
        for element in self.asn['products'][0]['members']:
            try:
                full_path = filesystem_path(element['expname'], check_existence=True)
            except FileNotFoundError:
                continue
            if element['exptype'] in self.contributing_files:
                self.contributing_files[element['exptype']].append(full_path)
            else:
                self.contributing_files[element['exptype']] = [full_path]

    def get_limits(self):
        """Determine the plot limits based on characteristics of the data.
        Let's just ignore the shortest and longest X% wavelengths and use
        the max and min of the rest? Would be nice to be able to ignore band
        edge effects, where the signal often jumps up.
        """
        ignore = 0.10  # 10%
        finite = np.where(np.isfinite(self.signal))[0]
        self.min_wave = np.min(finite)
        self.max_wave = np.max(finite)
        num_ignore = int((self.max_wave - self.min_wave) * ignore)
        min_idx = min_wave + num_ignore
        max_idx = max_wave - num_ignore

        self.max_yval = np.nanmax(self.signal[min_idx: max_idx])
        self.min_yval = np.nanmin(self.signal[min_idx: max_idx])

    def get_plot_range_mult_exposures(self):
        """For data with multiple exposures, get the vmin and vmax to use for
        plot scaling while looking across all exposures

        Returns
        -------
        minval : float
            Minimum value

        maxval : float
            Maximum value
        """
        all_data = np.array([])
        for exp in self.model.exposures:
            all_data = np.concatenate((all_data, np.ravel(exp.data)))
        minval = np.nanpercentile(all_data, 1)
        maxval = np.nanpercentile(all_data, 99)

        # If all data are NaN then revert to simple default values
        if not np.isfinite(minval):
            minval = 0
            maxval = 1

        return minval, maxval

    def get_ta_filenames(self):
        """Get the name of the TA file associated with the level 3 file
        """
        asn_base = self.model.meta.asn.table_name
        self.asn_file = filesystem_path(asn_base, check_existence=True)

        # Read in association file
        self.read_association_file()

        # Get a list of contributing filenames and file types
        self.get_level2_contributing_files()

        # Get TA files
        try:
            self.ta_files = self.contributing_files['target_acquisition']
        except KeyError:
            self.ta_files = []

        # Filter TA files. For NIRCam, keep only those for the detector where
        # the TA is actually done.
        self.filter_coron_ta_files()

    def get_wfss_cal_data(self, hdulists, source_num):
        """Find and extract the 2D spectrum from the WFSS cal file for a given source ID

        Parameters
        ----------
        hdulists : list
            List of HDULists of the cal files

        source_num : int
            Source ID number

        Returns
        -------
        cal_data : numpy.ndarray
            2D extracted spectrum corresponding to source_num
        """
        cal_info = {}

        # For the give source, loop over hdulists, and determine the extension within each
        # that contains the source. Do this for all orders.
        for ii, hdulist in enumerate(hdulists):

            # Output of find_wfss_source_ext is dict where key is order number, value is the extension containing the source
            source_exts = self.find_wfss_source_ext(hdulist, source_num)

            # Now go through the identified extensions for the source, and figure out
            # which one to use to display the data.
            # For each order, find the hdulist/extension with the longest 2D cutout,
            # indicating that the trace is not being cut off by the detector edges, and
            # show that. This means we may show traces from different files for different
            # orders.
            for order, ext in source_exts.items():
                if ext != -999:
                    if order not in cal_info:
                        cal_info[order] = {'data': None, 'width': 0, 'name': '', 'ext': -999, 'units': '', 'source_id': -999}

                    data = hdulist[ext].data

                    # Check the size of the 2D cutout. In order to avoid showing a
                    # dither where the source is close to the edge and the data quality
                    # isn't good, look through all cal files and keep the longest spectrum.
                    width = data.shape[-1]
                    dispersion_direction = hdulist[ext].header['DISPAXIS']
                    if dispersion_direction == 2:
                        width = data.shape[-2]

                    # If the 2D array is longer than the previous longest, keep it.
                    if width > cal_info[order]['width']:
                        # If the dispersion direction is along columns, transpose in
                        # order to make plotting easier.
                        if dispersion_direction == 2:
                            data = np.fliplr(np.transpose(data))

                        # NIRISS data are dispersed in the -x direction, so flip the
                        # 2D cutout horizontally so that the wavelength direction will
                        # match that in the 1D figure
                        #if hdulist[0].header['INSTRUME'] == 'NIRISS':
                        data = np.fliplr(data)

                        name = hdulist[0].header['FILENAME']
                        units = hdulist[ext].header['BUNIT']

                        cal_info[order]['data'] = data
                        cal_info[order]['width'] = width
                        cal_info[order]['name'] = name
                        cal_info[order]['ext'] = ext
                        cal_info[order]['units'] = units
                        cal_info[order]['source_id'] = hdulist[ext].header['SOURCEID']

        return cal_info

    def i2d_file(self):
        """Create a preview image from an i2d file.
        """
        vmin = np.nanpercentile(self.model.data, 1)
        vmax = np.nanpercentile(self.model.data, 99)

        # For segm files, very few pixels will have non-zero values. So if the percentile
        # values above end up being identical, fall back to use the full range of the data
        if vmin == vmax:
            vmin = np.nanmin(self.model.data)
            vmax = np.nanmax(self.model.data)
            logging.info(f'vmin and vmax are identical. Falling back to use full range of the data. {vmin} to {vmax}')

        # Get basic figure properties
        yd, xd = self.model.data.shape
        aspect, colorbar_orient, figsize = \
            determine_figure_properties(xd, yd, threshold=self.threshold_for_nonsquare_pix,
                                        maxsize=self.maxsize)

        self.fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize)
        ax.set_title(self.model.meta.filename)

        self.show_image_in_axis(ax, self.model.data, vmin, vmax, aspect, colorbar_orient, num_ticks=5)

        # Set text sizes
        maxsize = self.maxsize
        ax.set_xlabel('Pixels', fontsize=maxsize * 5. / 4)
        ax.set_ylabel('Pixels', fontsize=maxsize * 5. / 4)
        ax.tick_params(labelsize=maxsize)
        plt.rcParams.update({'axes.titlesize': 'small'})
        plt.rcParams.update({'font.size': maxsize * 5. / 4})
        plt.rcParams.update({'axes.labelsize': maxsize * 5. / 4})
        plt.rcParams.update({'ytick.labelsize': maxsize * 5. / 4})
        plt.rcParams.update({'xtick.labelsize': maxsize * 5. / 4})
        self.figures.append(self.fig)

    def locate_other_mrs_x1ds(self):
        """Find other MRS x1d files associated with the given file. The other files will
        cover the other channels and wavelength bands. The assumption is that the other files
        are in the same directory as the input file.
        """
        dirname, fname  = os.path.split(self.filename)
        x1dfiles = sorted(glob(os.path.join(dirname, f'{fname[0:18]}*x1d.fits')))

        # Sort each channel to be in short, medium, long order, to
        # make the plot more readable
        sorted_files = sorted(x1dfiles, key=lambda f: (
            int(re.search(r"ch(\d+)", f).group(1)),
            -ord(re.search(r"-(short|medium|long)", f).group(1)[0])  # crude way
        ))
        return sorted_files

    def miri_lrs_fixed_slit_nirspec_ifu_x1d_only(self):
        """Plot spectrum from x1d file from NIRSpec fixed slit or IFU file,
        or MIRI LRS fixed slit or IFU (MRS) mode. In these cases, there is only
        one self.model.spec extension, and the flux and wavelength data within
        that extension is 1-dimensional.
        """
        self.fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(self.maxsize, self.maxsize))

        flux = self.model.spec[0].spec_table.FLUX
        waves = self.model.spec[0].spec_table.WAVELENGTH
        targname = self.model.meta.target.proposer_name

        # Determine plot range
        clipped = sigma_clip_ignore_nan(flux, sigma=9)
        vmax = np.nanmax(clipped) * 1.1
        vmin = np.nanmin(clipped)
        if vmin >= 0:
            vmin = vmin * 0.9
        else:
            vmin = vmin * 1.1

        ax.plot(waves, flux, color='blue')
        ax.set_xlabel(f'Wavelength ({self.wavelength_units})')
        ax.set_ylabel(f'Flux ({self.flux_units})')
        ax.set_ylim(vmin, vmax)
        ax.set_title(f'{self.model.meta.filename}\n{targname}')

        self.figures.append(self.fig)

    def miri_lrs_fixed_slit_nirspec_ifu_x1d(self):
        """For MIRI LRS, as well as NIRSpec IFU and NIRSpec fixed slit x1d files, show a
        plot of the 1D spectrum. Next to that plot, show the s3d image where the spectrum
        came from. Overlay a circle indicating the aperture over which the flux is summed
        in order to create the 1D spectrum.
        """
        # Get the x1d data
        flux = self.model.spec[0].spec_table.FLUX
        waves = self.model.spec[0].spec_table.WAVELENGTH
        targname = self.model.meta.target.proposer_name

        # Determine plot range
        clipped = sigma_clip_ignore_nan(flux, sigma=9)
        vmax = np.nanmax(clipped) * 1.1
        vmin = np.nanmin(clipped)
        if vmin >= 0:
            vmin = vmin * 0.9
        else:
            vmin = vmin * 1.1

        # Find s3d file
        s3d_file = self.filename.replace('x1d', 's3d')
        if os.path.isfile(s3d_file):
            s3d_model = datamodels.open(s3d_file)

            # Find the index of the brightest point in the 1D spectrum. We'll display
            # that frame from the s3d file
            brightest_idx = np.where(self.model.spec[0].spec_table['FLUX'] == np.nanmax(self.model.spec[0].spec_table['FLUX']))[0]
            if len(brightest_idx) >= 1:
                brightest_idx = brightest_idx[0]
            else:
                # Somehow there's no index matching the brightest value
                brightest_idx = len(self.model.spec[0].spec_table['FLUX']) // 2

            s3d_frame = s3d_model.data[brightest_idx, :, :]
            yd, xd = s3d_frame.shape

            # Create figure
            figsize = (self.maxsize * 2, self.maxsize)
            self.fig = plt.figure(figsize=figsize)
            ax_x1d = plt.subplot2grid((1, 3), (0, 0), colspan=2)
            ax_s3d = plt.subplot2grid((1, 3), (0, 2), colspan=1)

            # Populate the s3d axes
            # Make sure the aspect and colorbar orient are correct
            aspect_s3d, colorbar_orient_s3d, figsize = \
                determine_figure_properties(xd, yd, threshold=self.threshold_for_nonsquare_pix,
                                            maxsize=self.maxsize)

            # Get the vmin and vmax for the s3d image
            vmin_s3d = np.nanpercentile(s3d_frame, 1)
            vmax_s3d = np.nanpercentile(s3d_frame, 99)

            # Show the image in the s3d axes
            self.show_image_in_axis(ax_s3d, s3d_frame, vmin_s3d, vmax_s3d, aspect_s3d,
                                    colorbar_orient_s3d, num_ticks=5, override_unit=s3d_model.meta.bunit_data)
            ax_s3d.set_xlabel('Pixel')
            ax_s3d.set_ylabel('Pixel')
            ax_s3d.set_title(f's3d: slice {brightest_idx}\n{waves[brightest_idx]:.5f} microns')

            # Get the coordinates of the center of the aperture summed over to create the 1D spectrum
            # This info does not make it into the datamodel metadata, so we retrieve it via astropy.io.fits
            x1dheader = fits.getheader(self.filename, 1)
            centerx = x1dheader['EXTR_X']
            centery = x1dheader['EXTR_Y']
            source_type = x1dheader['SRCTYPE']

            if source_type == 'POINT':
                # Find the median number of pixels in the aperture, using the table
                median_numpix = np.nanmedian(self.model.spec[0].spec_table["NPIXELS"])

                # Calculate circular aperture radius
                aperture_radius = np.sqrt(median_numpix / np.pi)

                # Add a circle to the s3d image, showing the summation aperture
                circle = Circle((centerx, centery), aperture_radius,
                                fill=False, edgecolor='red', linewidth=2)
                ax_s3d.add_patch(circle)

            else:
                # For extended sources, the entire aperture is extracted to create the 1D spectrum,
                # so we use a square marker and set it to the width of the array
                rect = Rectangle((0, 0), s3d_model.data.shape[2] - 1, s3d_model.data.shape[1] - 1,
                                 linewidth=2, edgecolor='red', facecolor='none')
                ax_s3d.add_patch(rect)

            # Say what the circle or rectangle represents
            ax_s3d.annotate('Summed aperture', (1, 1), fontsize=12, color='red')

        else:
            # In this case the s3d file is not present, so just show the 1D spectral plot
            self.fig, ax_x1d = plt.subplots(ncols=1, nrows=1, figsize=(self.maxsize, self.maxsize))

        # Populate the x1d axes whether the s3d data exist or not
        ax_x1d.plot(waves, flux, color='blue')
        ax_x1d.set_xlabel(f'Wavelength ({self.wavelength_units})')
        ax_x1d.set_ylabel(f'Flux ({self.flux_units})')
        ax_x1d.set_ylim(vmin, vmax)
        ax_x1d.set_title(f'{self.model.meta.filename}\n{targname}')
        self.figures.append(self.fig)

    def miri_lrs_slitless_x1dints_plot(self):
        """Create preview image for MIRI LRS-SLITLESS x1dints data
        """
        nspec = len(self.model.spec)

        baseline_integ = 1
        baseline_flux = self.model.spec[0].spec_table.FLUX[baseline_integ, :]
        baseline_waves = self.model.spec[0].spec_table.WAVELENGTH[baseline_integ, :]

        # Find extension with the lowest mean flux
        low_spec = 0
        low_med = 999999
        low_total_integ = 0
        total_prev_integ = 0

        for s_idx in range(nspec):
            nints = self.model.spec[s_idx].spec_table.WAVELENGTH.shape[0]

            for integ in range(2, nints, 5):
                med = np.nanmedian(self.model.spec[s_idx].spec_table.FLUX[integ, :])
                if med < low_med:
                    low_med = med
                    low_integ = integ
                    low_spec = s_idx
                    low_total_integ = total_prev_integ + integ

            # Running total of the number of integrations prior to the current spec
            total_prev_integ += nints

        low_flux = self.model.spec[low_spec].spec_table.FLUX[low_integ, :]
        low_waves = self.model.spec[low_spec].spec_table.WAVELENGTH[low_integ, :]

        self.fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(self.maxsize, self.maxsize))
        ax[0].plot(baseline_waves, baseline_flux, alpha=0.75, label=f'Integ {baseline_integ}')
        ax[0].plot(low_waves, low_flux, alpha=0.75, label=f'Integ {low_total_integ}')
        ax[0].set_xlabel(f'Wavelength ({self.wavelength_units})')
        ax[0].set_ylabel(f'Flux ({self.flux_units})')
        ax[0].legend()
        ax[0].set_title(self.model.meta.filename)

        # Pick several wavelengths and plot the corresponding fluxes over time
        fin = np.where(np.isfinite(baseline_flux))[0]
        minfin = np.min(fin)
        numfin = len(fin)
        wavelength = self.model.spec[0].spec_table.WAVELENGTH[0]
        wave_idxs = [int(minfin + 0.25*i*numfin) for i in [1,2,3]]
        int_times = self.model.int_times['int_mid_MJD_UTC']
        time_units = self.model.int_times.columns['int_mid_MJD_UTC'].unit
        if time_units is None:
            time_units = 'd'

        for wave_idx in wave_idxs:

            all_flux = np.array([])
            for s_idx in range(nspec):
                all_flux = np.concatenate([all_flux, self.model.spec[s_idx].spec_table.FLUX[:, wave_idx]])

            ax[1].plot(int_times, all_flux, alpha=0.5, label="{:.3f} um".format(wavelength[wave_idx]))

        ax[1].set_xlabel(f'MJD_UTC ({time_units})')
        ax[1].set_ylabel(f'Flux ({self.flux_units})')
        ax[1].legend()

        self.figures.append(self.fig)

    def miri_lrs_slitless_x1dints_plot_old_format(self):
        """Create preview image for MIRI LRS-SLITLESS x1dints data that uses the old data
        format, pre-jwst-1.19.0
        """
        nints = len(self.model.spec)

        baseline_integ = 1
        baseline_flux = self.model.spec[baseline_integ].spec_table.FLUX
        baseline_waves = self.model.spec[baseline_integ].spec_table.WAVELENGTH

        # Find extension with the lowest mean flux
        low_med = 999999
        for integ in range(2, nints, 5):
            med = np.nanmedian(self.model.spec[integ].spec_table.FLUX)
            if med < low_med:
                low_med = med
                low_integ = integ
        low_flux = self.model.spec[low_integ].spec_table.FLUX
        low_waves = self.model.spec[low_integ].spec_table.WAVELENGTH

        self.fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(self.maxsize, self.maxsize))
        ax[0].plot(baseline_waves, baseline_flux, alpha=0.5, label=f'Int {baseline_integ}')
        ax[0].plot(low_waves, low_flux, alpha=0.5, label=f'Int {low_integ}')
        ax[0].set_xlabel(f'Wavelength ({self.wavelength_units})')
        ax[0].set_ylabel(f'Flux ({self.flux_units})')
        ax[0].legend()
        ax[0].set_title(self.model.meta.filename)

        # Pick several wavelengths and plot the corresponding fluxes over time
        fin = np.where(np.isfinite(baseline_flux))[0]
        minfin = np.min(fin)
        numfin = len(fin)
        wavelength = self.model.spec[0].spec_table.WAVELENGTH
        wave_idxs = [int(minfin + 0.25*i*numfin) for i in [1,2,3]]
        int_times = self.model.int_times['int_mid_MJD_UTC']
        time_units = self.model.int_times.columns['int_mid_MJD_UTC'].unit
        if time_units is None:
            time_units = 'd'

        for wave_idx in wave_idxs:
            fluxes = [self.model.spec[i].spec_table.FLUX[wave_idx] for i in range(nints)]
            ax[1].plot(int_times, fluxes, label="{:.3f} um".format(wavelength[wave_idx]))
        ax[1].set_xlabel(f'MJD_UTC ({time_units})')
        ax[1].set_ylabel(f'Flux ({self.flux_units})')
        ax[1].legend()

        self.figures.append(self.fig)

    def miri_mrs_x1d(self):
        """Plot spectrum from a MIRI MRS x1d file. In these cases, there is only
        one self.model.spec extension, and the flux and wavelength data within
        that extension is 1-dimensional.
        """
        self.fig, ax = plt.subplots(ncols=1, nrows=2, figsize=(self.maxsize, self.maxsize * 1.5))

        use_flux = 'RF_FLUX'
        flux = self.model.spec[0].spec_table.RF_FLUX

        # MRS x1d files have both regular ('flux') and residual-fringe (RF) corrected ('rf_flux') spectra.
        # The RF-corrected spectra will have NaN values if RF correction was disabled or failed to converge.
        # Plot the RF corrected spectrum if available, otherwise plot the regular spectrum.
        if (np.nansum(flux == 0) or np.all(np.isnan(flux))):
            logging.debug(f'{self.model.meta.filename} RF_FLUX is all NaN, using FLUX column instead')
            use_flux = 'FLUX'
            flux = self.model.spec[0].spec_table.FLUX

        waves = self.model.spec[0].spec_table.WAVELENGTH
        targname = self.model.meta.target.proposer_name
        channel_band = f'{self.model.meta.instrument.channel} {self.model.meta.instrument.band}'

        # Determine plot range
        clipped = sigma_clip_ignore_nan(flux, sigma=9)

        if np.all(np.isnan(clipped)):
            vmin = 0
            vmax = 1
        else:
            vmax = np.nanmax(clipped) * 1.1
            vmin = np.nanmin(clipped)
            if vmin >= 0:
                vmin = vmin * 0.9
            else:
                vmin = vmin * 1.1

        ax[0].plot(waves, flux, color='blue', label=channel_band)
        ax[0].set_xlabel(f'Wavelength ({self.wavelength_units})')
        ax[0].set_ylabel(f'Flux ({self.flux_units})')
        ax[0].legend()
        ax[0].set_ylim(vmin, vmax)
        ax[0].set_title(f'{self.model.meta.filename}\n{targname}')

        # Locate any other related x1d files that are related. If others are found, plot
        # all the x1d files together. If no other files are found, then create only the
        # single plot above
        x1dfiles = self.locate_other_mrs_x1ds()

        if len(x1dfiles) > 1:
            vmin, vmax = np.nan, np.nan
            for x1dfile in x1dfiles:

                mod = datamodels.open(x1dfile)
                flux = mod.spec[0].spec_table[use_flux]
                waves = mod.spec[0].spec_table.WAVELENGTH
                channel_band = f'{mod.meta.instrument.channel} {mod.meta.instrument.band}'

                # Determine plot range
                clipped = sigma_clip_ignore_nan(flux, sigma=9)

                if np.all(np.isnan(clipped)):
                    vfilemin = np.nan
                    vfilemax = np.nan
                else:
                    vfilemax = np.nanmax(clipped) * 1.1
                    vfilemin = np.nanmin(clipped)

                    # Add some padding to the top and bottom of the range
                    if vfilemin >= 0:
                        vfilemin = vfilemin * 0.9
                    else:
                        vfilemin = vfilemin * 1.1
                    if vfilemax >= 0:
                        vfilemax *= 1.1
                    else:
                        vfilemax *= 0.9

                vmin = np.nanmin([vmin, vfilemin])
                vmax = np.nanmax([vmax, vfilemax])

                ax[1].plot(waves, flux, label=channel_band)
                ax[1].set_xlabel(f'Wavelength ({self.wavelength_units})')
                ax[1].set_ylabel(f'Flux ({self.flux_units})')
                ax[1].set_ylim(vmin, vmax)
                ax[1].legend()
                ax[1].set_title(self.model.meta.target.catalog_name)
        else:
            # In this case, no other x1d files are present
            ax[1].remove()
        self.figures.append(self.fig)

    def niriss_soss_plot(self):
        """Create preview image for NIRISS SOSS x1dints data

        NOTE: This function works for both level 3 and level 2 x1dints files.
        """
        nints = len(self.model.int_times['int_start_MJD_UTC'])

        # Find which orders are captured in which extensions
        orders = {}
        int_info = {}
        for ext in range(len(self.model.spec)):
            order = str(self.model.spec[ext].spectral_order)
            if order in orders:
                orders[order].append(ext)
            else:
                orders[order] = [ext]

        self.fig, ax = plt.subplots(ncols=2, nrows=len(orders), figsize=(self.maxsize*2, 6 + 3*(len(orders) - 1)))

        # Integration times for all integrations
        int_times = self.model.int_times['int_mid_MJD_UTC']
        time_axis = (int_times - np.nanmean(int_times)) * 24.0
        time_units = 'hr'

        # Minor tweak to axis label if we have a level 2 seg x1dints file
        x_ax_str = 'exposure'
        if '-seg' in self.model.meta.filename:
            x_ax_str = 'segment'

        # Integration number we'll consider "baseline", and plot
        baseline_integ = 1

        # Find integration with lowest mean value in 1st order
        low_integ = 2
        low_spec_idx = orders['1'][0]
        low_med = 999999
        spec_ints = []
        for spec_idx in orders['1']:
            n_spec_ints = self.model.spec[spec_idx].spec_table.WAVELENGTH.shape[0]
            spec_ints.append(n_spec_ints)

            # Define which integration to start with. In the initial spec
            # object, start with the integration after the baseline
            min_int = 0
            if spec_idx == orders['1'][0]:
                min_int = baseline_integ + 1

            for integ in range(min_int, n_spec_ints):
                data = self.model.spec[spec_idx].spec_table['FLUX'][integ, :]
                med = np.nanmedian(data)
                if med < low_med:
                    low_integ = integ
                    low_spec_idx = spec_idx
                    low_med = med

        # Find the spec extension that contains the low data
        match = np.where(low_spec_idx == np.array(orders['1']))[0][0]

        # Calculate the integration number corresponding to the low data
        low_total_integ = np.sum(np.array(spec_ints)[0:match]) + low_integ

        # For each order, get the flux and wavelength values corresponding to the baseline
        for i, order in enumerate(orders):

            # Get the baseline data, assumed to be an integration prior to the start of
            # any eclipse/variation in signal.
            baseline_data = self.model.spec[orders[order][0]].spec_table['FLUX'][baseline_integ, :]
            baseline_waves = self.model.spec[orders[order][0]].spec_table['WAVELENGTH'][baseline_integ, :]

            # Get the data from the integration with the lowest median signal. We assume this
            # is during the exlipse.
            low_data = self.model.spec[orders[order][match]].spec_table['FLUX'][low_integ, :]
            low_waves = self.model.spec[orders[order][match]].spec_table['WAVELENGTH'][low_integ, :]

            ax[i, 0].plot(baseline_waves, baseline_data, alpha=0.5, label=f'Integ {baseline_integ}')
            ax[i, 0].plot(low_waves, low_data, alpha=0.5, linestyle='dashed', label=f'Integ {low_total_integ}')
            if i == 0:
                ax[i, 0].set_title(f'{self.model.meta.filename}, Order {order}')
            else:
                ax[i, 0].set_title(f'Order {order}')
            ax[i, 0].set_xlabel(f'Wavelength ({self.wavelength_units})')
            ax[i, 0].set_ylabel(f'Flux ({self.flux_units})')
            ax[i, 0].legend()

            # Select three different wavelengths from each order, and get the signal through
            # time at those wavelengths
            fin = np.where(np.isfinite(baseline_data))[0]
            minfin = np.min(fin)
            numfin = len(fin)
            #wavelength = self.model.spec[orders[order][0]].spec_table.WAVELENGTH[baseline_integ, 0]
            wave_idxs = [int(minfin + 0.25*i*numfin) for i in [1,2,3]]

            waves = []
            for i_wave, wave_idx in enumerate(wave_idxs):

                # Create a list of wavelengths, for plot labeling
                waves.append(baseline_waves[wave_idx])

                fluxes_v_time = []
                for i_spec, spec_idx in enumerate(orders[order]):

                        # Get the data for the expected wavelength
                        fluxes_v_time.extend(self.model.spec[spec_idx].spec_table['FLUX'][:, wave_idx])

                ax[i, 1].plot(time_axis, fluxes_v_time, alpha=0.5, label="{:.3f} um".format(waves[i_wave]))
            ax[i, 1].set_xlabel(f'Time since mid-time of {x_ax_str} ({time_units})')
            ax[i, 1].set_ylabel(f'Flux ({self.flux_units})')
            ax[i, 1].set_title(f'Order {order}')
            ax[i, 1].legend()

        plt.tight_layout()
        self.figures.append(self.fig)

    def niriss_soss_plot_old_format(self):
        """Create preview image for NIRISS SOSS x1dints data
        """
        nints = len(self.model.int_times['int_start_MJD_UTC'])

        # Find which orders are captured in which extensions
        orders = {}
        int_info = {}
        for ext in range(len(self.model.spec)):
            order = self.model.spec[ext].spectral_order
            if order in orders:
                orders[str(order)].append(ext)
            else:
                orders[str(order)] = [ext]

            integ = self.model.spec[ext].int_num
            if str(integ) in int_info:
                int_info[str(integ)].append(ext)
            else:
                int_info[str(integ)] = [ext]

        baseline_integ = '1'
        baseline_order_idx = int_info[baseline_integ]
        baseline_data = [self.model.spec[e].spec_table.FLUX for e in baseline_order_idx]
        baseline_waves = [self.model.spec[e].spec_table.WAVELENGTH for e in baseline_order_idx]
        baseline_orders = [self.model.spec[e].spectral_order for e in baseline_order_idx]

        # Find integration with lowest mean value
        low_integ = '2'
        low_med = 999999
        for integ in range(2, nints):
            idx = int_info[str(integ)][0]
            med = np.nanmedian(self.model.spec[idx].spec_table.FLUX)
            if med < low_med:
                low_integ = str(integ)

        low_order_idx = int_info[low_integ]
        low_data = [self.model.spec[e].spec_table.FLUX for e in low_order_idx]
        low_waves = [self.model.spec[e].spec_table.WAVELENGTH for e in low_order_idx]
        low_orders = [self.model.spec[e].spectral_order for e in low_order_idx]

        self.fig, ax = plt.subplots(figsize=(self.maxsize, self.maxsize))
        for wave, data, order in zip(baseline_waves, baseline_data, baseline_orders):
            ax.plot(wave, data, alpha=0.5, label=f'Int {baseline_integ}, order {order}')
        for wave, data, order in zip(low_waves, low_data, low_orders):
            ax.plot(wave, data, alpha=0.5, linestyle='dashed', label=f'Int {low_integ}, order {order}')
        ax.set_xlabel(self.wavelength_units)
        ax.set_ylabel(self.flux_units)
        ax.legend()

        self.figures.append(self.fig)

    def nirspec_miri_ifu_s3d(self):
        """Create a preview image for NIRSpec and MIRI IFU s3d files.
        """
        nframes, yd, xd = self.model.data.shape
        frames_to_view = [nframes // 2]  # Create image only for middle frame

        # Get basic figure properties
        aspect, colorbar_orient, figsize = \
            determine_figure_properties(xd, yd, threshold=self.threshold_for_nonsquare_pix,
                                        maxsize=self.maxsize)

        # Determine the vmin and vmax values for scaling based on a mean frame
        # To save time, take the mean over only a subset of frames. Focus on the
        # shorter wavelngths where the signals are most likely higher
        strt_frame = nframes // 9
        end_frame = strt_frame + 100
        if end_frame > nframes:
            end_frame = nframes

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Mean of empty slice')
            slice_mean = np.nanmean(self.model.data[strt_frame:end_frame, :, :], axis=0)
        vmin = np.nanpercentile(slice_mean, 1)
        vmax = np.nanpercentile(slice_mean, 99)

        for frame in frames_to_view:
            self.fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
            self.show_image_in_axis(ax, self.model.data[frame, :, :], vmin, vmax, aspect, colorbar_orient, num_ticks=5)

            ax.set_xlabel('Pixel')
            ax.set_ylabel('Pixel')
            ax.set_title(f'{self.model.meta.filename}: slice {frame}')

            self.figures.append(self.fig)

    def plot_i2d_plus_source(self, i2dname, source_id, ax, box_hw=10):
        """Open the i2d & catalog files, and show an annotated image of the source associated
        with the source number.

        Parameters
        ----------
        i2dname : str
            Name of source i2d file

        source_id : int
            Source ID number

        ax : matplotlib.axes._axes.Axes
            Figure axis that will be used to show the image

        box_hw : int
            Half-width of the box to show containing the source

        Returns
        -------
        ax : matplotlib.axes._axes.Axes
            Figure axis with annotated image added
        """
        catname = i2dname.replace('i2d.fits', 'cat.ecsv')

        # Get source location from the source catalog
        cat = Table.read(catname)
        cat_line = cat[cat['label'] == source_id]
        xcentroid = cat_line['xcentroid'][0]
        ycentroid = cat_line['ycentroid'][0]
        xstart = int(xcentroid - box_hw)
        ystart = int(ycentroid - box_hw)
        xstop = int(xcentroid + box_hw)
        ystop = int(ycentroid + box_hw)

        # Plot the image
        with fits.open(i2dname) as i2d:
            if ystart < 0:
                ystart = 0
            if xstart < 0:
                xstart = 0
            if xstop > i2d['SCI'].data.shape[-1]:
                xstop = i2d['SCI'].data.shape[-1]
            if ystop > i2d['SCI'].data.shape[-2]:
                ystop = i2d['SCI'].data.shape[-2]

            cutout = i2d[1].data[ystart: ystop, xstart: xstop]
            colorbar_units = i2d[1].header['BUNIT']

        # Clip brightest and dimmest 1% of pixels to find min and max values
        vmin = np.nanpercentile(cutout, 1)
        vmax = np.nanpercentile(cutout, 99)

        if np.isnan(vmin):
            vmin = np.nanmin(cutout)
            if np.isnan(vmin):
                vmin = 0.
        if np.isnan(vmax):
            vmax = np.nanmax(cutout)
            if np.isnan(vmax):
                vmax = vmin + 1.

        # Similar to what's done for the i2d files, shfit the data to be positive, use a log stretch,
        # and adjust colorbar tick values to show the unshifted data values.
        shiftdata, shiftmin, shiftmax, tickvals, tlabelflt = shift_data_get_ticks(cutout, vmin, vmax, num_ticks=5)
        tlabelstr = formatted_tick_labels(tlabelflt)

        # Image object
        imi2d = ax.imshow(shiftdata,
                          norm=colors.LogNorm(vmin=shiftmin,
                                              vmax=shiftmax),
                          cmap=self.cmap,
                          aspect='auto',
                          origin='lower')

        # Shift the tick values to the full frame coordinate system
        ax.set_xticks(np.arange(0, 2*box_hw+1, 5))
        ax.set_yticks(np.arange(0, 2*box_hw+1, 5))
        new_xticks = ax.get_xticks() + xstart
        new_yticks = ax.get_yticks() + ystart
        ax.set_xticklabels(new_xticks)
        ax.set_yticklabels(new_yticks)
        ax.set_xlabel('Pixel')
        ax.set_ylabel('Pixel')

        # Add annotation showing location and source ID
        ax.scatter(xcentroid - xstart, ycentroid - ystart, s=20, facecolors='None', edgecolors='magenta', alpha=0.9)
        ax.annotate(source_id,
                    (xcentroid-xstart+0.5, ycentroid-ystart+0.5),
                    fontsize=10,
                    color='magenta')
        ax.set_title(os.path.basename(i2dname), fontsize=10)

        # Add colorbar, and create tick labels for it
        # Create a separate axes for the colorbar, right next to the image
        divider = make_axes_locatable(ax)

        # Colorbar will always be on the right side of the cutout
        cax_colorbar = divider.append_axes("right", size="5%", pad=0.05)

        cbar = self.fig.colorbar(imi2d, cax=cax_colorbar, label=colorbar_units, ticks=tickvals, orientation='vertical', pad=0.01)

        cbar.ax.yaxis.minorticks_off()
        cbar.ax.set_yticklabels(tlabelstr)

        return ax, imi2d

    def psfstack_file(self):
        """Create preview image for the psfstack files associated with coronaraphic observations
        """
        nframes, yd, xd = self.model.data.shape

        # Discussions with coronagraph folks suggest that showing just one frame from the
        # psfstack should be fine in terms of preview images. JDAViz/other tools can be
        # used to look for shifts in the PSF location after examining the PSF-subtracted
        # i2d image.
        frames_to_view = [0]

        vmin = np.nanpercentile(self.model.data[0, :, :], 1)
        vmax = np.nanpercentile(self.model.data[0, :, :], 99)

        # Get basic figure properties
        aspect, colorbar_orient, figsize = \
            determine_figure_properties(xd, yd, threshold=self.threshold_for_nonsquare_pix,
                                        maxsize=self.maxsize)

        for frame in frames_to_view:
            # Create figure
            self.fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize,
                                        constrained_layout=True)

            self.show_image_in_axis(ax, self.model.data[frame, :, :], vmin, vmax, aspect, colorbar_orient, num_ticks=5)
            ax.set_title(f'{self.model.meta.filename}, Frame: {frame}')
            ax.set_xlabel("Pixels")
            ax.set_ylabel("Pixels")
            self.figures.append(self.fig)

    def read_association_file(self):
        """Read in the association file
        """
        with open(self.asn_file) as obj:
            self.asn = json.load(obj)

    def remove_wfss_nan_data(self, data):
        """Look through wfss data included in a dictionary, and remove instances where the fluxes
        are all nan. This will most commonly happen where the 1st order data are present, but then it
        turns out the 2nd order data are empty.

        Parameters
        ----------
        data : dict
            Dictionary containing WFSS data, in "order", "flux", and "wavelength" keys

        Returns
        -------
        new_dict : dict
            Keys in the dictionary are: order, flux, and wavelength.
            The dictionary contains data only for a single source, but multiple exposures/dithers/orders
        """
        new_dict = {'order': [], 'flux': [], 'wavelength': []}
        for index in range(len(data['order'])):
            # If there are any finite flux values, keep the array
            if ~np.all(~np.isfinite(np.array(data['flux'][index]))):
                new_dict['order'].append(data['order'][index])
                new_dict['flux'].append(data['flux'][index])
                new_dict['wavelength'].append(data['wavelength'][index])
        return new_dict

    def save_figures(self):
        """
        Save matplotlib figures as preview images and possibly thumbnail images,
        and set the appropriate permissions
        """
        if len(self.figures) == 0:
            logging.error(f'No figure produced for file: {self.filename}')
            return

        for i, figure in enumerate(self.figures):

            # Preview image filename is the name of the input file with jpg at the end
            #fname = os.path.join(self.preview_output_directory, self.model.meta.filename.split('.')[0] + '.jpg')
            fname = os.path.basename(self.filename).split('.')[0] + '.jpg'

            # Save preview image
            self.preview_images.append(fname)
            img_type = 'preview'
            outname = os.path.join(self.preview_output_directory, fname)
            figure.savefig(outname, bbox_inches='tight', pad_inches=0.05)
            permissions.set_permissions(outname)
            logging.info(f'\tSaved {img_type} image to {outname}')

        # If we're saving a thumbnail, change the output file name and make the
        # figure smaller. Make axes and labels invisible. In cases where there are
        # mulitple preview images, and thumbnails are to be made, only create a
        # thumbnail for the first one.
        if self.create_thumbnail:
            figure = self.figures[0]
            figure = hide_axes(figure)
            orig_width, orig_height = figure.get_size_inches()
            figure.set_size_inches(3, 3, forward=True)
            img_type = 'thumbnail'

            outname = os.path.join(self.thumbnail_output_directory, self.preview_images[0])
            figure.savefig(outname, bbox_inches='tight', pad_inches=0)
            permissions.set_permissions(outname)

            thumb_outname = outname.replace('.jpg', '.thumb')
            os.rename(outname, thumb_outname)
            self.thumbnail_images.append(os.path.basename(thumb_outname))
            logging.info(f'\tSaved {img_type} image to {thumb_outname}')

        # Close the figures
        for figure in self.figures:
            plt.close(figure)

    def show_image_in_axis(self, axis, image, disp_min, disp_max, aspect, colorbar_orient, num_ticks=5, colorbar_pad=0.5,
        colorbar_labelpad={'vertical': 15, 'horizontal': 7}, add_colorbar=True, override_unit=None, extent_shift=[0, 0]):
        """Add a 2D image to a given figure axis. Add a colorbar with appropriate tick marks and values. To get
        around the issue of using log scaling with data that may have negative values, shift the data such that
        all data are positive, and then shift the colorbar tick labels back to the original values of the data.
        """
        shiftdata, shiftmin, shiftmax, tickvals, tlabelflt = shift_data_get_ticks(image, disp_min, disp_max, num_ticks=num_ticks,
                                                                                  min_range_for_logscale=self.min_range_for_logscale)
        tlabelstr = formatted_tick_labels(tlabelflt)

        if shiftmax - shiftmin > 1:
            norm = colors.LogNorm(vmin=shiftmin, vmax=shiftmax)
        else:
            norm = colors.Normalize(vmin=shiftmin, vmax=shiftmax)

        # Image object
        height, width = image.shape
        cax = axis.imshow(shiftdata,
                          norm=norm,
                          cmap=self.cmap,
                          aspect=aspect,
                          origin='lower',
                          extent=[extent_shift[0], extent_shift[0] + width, extent_shift[1], extent_shift[1] + height])

        # If the data are all NaN, then add some text specifying that
        if np.all(np.isnan(image)):
            axis.text(extent_shift[0] + width / 2, extent_shift[1] + height / 2, 'All NaN data', color='white', fontsize=12)

        # If no colorbar is to be added, then we're done
        if not add_colorbar:
            return cax

        # For preview images, add colorbar, and create tick labels for it
        ysize, xsize = image.shape

        xyratio = xsize / ysize
        divider = make_axes_locatable(axis)

        # If the figure is particularly narrow, bump up the width of the colorbar in order
        # to make it more visible
        colorbar_size = "5%"
        figure_size = self.fig.get_size_inches()
        if np.min(figure_size) < 2:
            colorbar_size = "15%"

        # If the datamodel does not include information on the data units, then set that to
        # an empty string, unless the user overrides with a specific value.
        try:
            units = self.model.meta.bunit_data
        except AttributeError:
            units = ''
        if override_unit is not None:
            units = override_unit

        if colorbar_orient == 'vertical':
            # For apertures that are taller than they are wide, square, or that are wider than
            # they are tall but still reasonably close to square, put the colorbar on the right
            # side of the image.
            cax_colorbar = divider.append_axes("right", size=colorbar_size, pad=colorbar_pad)
            cbar = self.fig.colorbar(cax, cax=cax_colorbar, ticks=tickvals, orientation='vertical')
            cbar.ax.yaxis.minorticks_off()
            cbar.ax.set_yticklabels(tlabelstr)
            cbar.ax.set_ylabel(units, labelpad=colorbar_labelpad[colorbar_orient], rotation=270)

        elif colorbar_orient == 'horizontal':
            # For apertures that are significantly wider than they are tall, put the colorbar
            # under the image.
            cax_colorbar = divider.append_axes("bottom", size=colorbar_size, pad=colorbar_pad)
            cbar = self.fig.colorbar(cax, cax=cax_colorbar, ticks=tickvals, orientation='horizontal')
            cbar.ax.xaxis.minorticks_off()
            cbar.ax.set_xticklabels(tlabelstr)
            cbar.ax.set_xlabel(units, labelpad=colorbar_labelpad[colorbar_orient], rotation=0)

        else:
            logging.debug(f"No colorbar requested")

    def tso_whitelight_curve_prev_version(self):
        """Plot the whitelight curve. This function covers NRC_TSGRISM, MIR_LRS-SLITLESS and NIS_SOSS,
        as well as the phot.ecsv files from NRC_TSGRISM. This function works on white light files from
        older versions of the jwst pipeline.
        """
        # There are two options for the column name that contains the MJD dates
        # of the data
        time_key = 'MJD'
        if 'NRC' in self.metadata['exp_type']:
            time_key = 'MJD_UTC'

        flux_key = 'whitelight_flux'
        if 'phot.ecsv' in self.filename:
            flux_key = 'net_aperture_sum'

        self.fig, ax = plt.subplots(figsize=(self.maxsize*1.375, self.maxsize))
        ax.plot(self.model[time_key], self.model[flux_key], color='black')
        ax.set_xlabel('Time (MJD)')
        ax.set_ylabel(flux_key)
        ax.set_title(f'{os.path.basename(self.filename)}: {self.metadata["target_name"]}, {self.metadata["number_of_integrations"]} ints')
        self.figures.append(self.fig)

    def tso_whitelight_curve(self):
        """
        Create and display white light curve. This function covers NRC_TSGRISM, MIR_LRS-SLITLESS and NIS_SOSS,
        as well as the phot.ecsv files from NRC_TSGRISM.
        """
        # There are two options for the column name that contains the MJD dates
        # of the data
        time_key = ''
        for colname in self.model.columns:
            if 'MJD' in colname:
                time_key = colname
        if time_key == '':
            raise ValueError(f"Unable to find time-related column in {self.filename}")

        # NIS_SOSS will have a separate whitelight column for each spectral order
        # NRC_TSGRISM will have a single whitelight_flux column
        flux_keys = [c for c in self.model.columns if 'whitelight' in c]
        flux_keys.sort()

        if 'phot.ecsv' in self.filename:
            flux_keys = ['net_aperture_sum']

        # --------------------------Set up figures--------------------------
        xfigsize = 12
        yfigsize = 8 + (len(flux_keys) - 1) * 4.2
        self.fig, axes = plt.subplots(ncols=1, nrows=len(flux_keys), figsize=(xfigsize, yfigsize))

        n_spec = len(self.model[time_key])  # Number of spectra (integrations).
        all_times = self.model[time_key]
        time_axis = (all_times - np.nanmean(all_times)) * 24.0

        # Calculate tick labels for the secondary x-axis
        integration_indices = np.arange(n_spec)
        tick_positions = np.linspace(time_axis.min(),
                                     time_axis.max(),
                                     len(integration_indices))
        count = min(10, len(tick_positions))
        indices = np.linspace(0, len(tick_positions) - 1, count, dtype=int)


        for i, flux_key in enumerate(flux_keys):
            if 'order' in flux_key:
                order_str = ', order ' + flux_key.split('_')[-1]
            else:
                order_str = ''

            # ---------------------Obtain white light curve---------------------
            wlc_flux = self.model[flux_key]

            # Calculate light curve scatter
            wlc_flux_scatter = sigma_clip(wlc_flux, sigma=2, maxiters=2, masked=False)
            wlc_flux_median = np.nanmedian(wlc_flux_scatter[2:100])

            # Normalize the flux by the median in the early integrations
            wlc_flux /= wlc_flux_median

            # Calculate the noise
            sigma_wlc = np.sqrt(np.nanvar(wlc_flux_scatter[2:100] / wlc_flux_median))
            sigma_wlc_ppm = round(sigma_wlc * 1e6, 0)

            # Try to get a good y-range for the plot. Use the standard deviation across the
            # entire white light curve, in case there is a large difference between beginning and
            # ending signals
            full_median = np.median(wlc_flux)
            full_sigma = np.std(wlc_flux)

            # Plot white light curve
            if 'whitelight' in flux_key:
                title_str = f"White light curve{order_str}"
                label = f"(r.m.s.={round(sigma_wlc * 1e6, 0)} ppm)"
            elif flux_key == 'net_aperture_sum':
                title_str = f"Photometry curve"
                label = f"(r.m.s.={round(sigma_wlc * 1e6, 0)} ppm)"

            # If there is a single white light column then axes will be an axis object.
            # If there are mulitple columns, then axes will be a subscriptable list.
            if len(flux_keys) == 1:
                tmp_axis = axes
            elif len(flux_keys) > 1:
                tmp_axis = axes[i]
            else:
                raise ValueError(f'Unsupported number of flux columns: {len(flux_keys)}')

            tmp_axis.plot(time_axis, wlc_flux, marker='o', markersize=2,
                          label=label)
            tmp_axis.legend(loc="lower right")
            tmp_axis.set_xlabel("Time since mid-exposure, (hr)", fontsize=15)
            tmp_axis.set_ylabel("Normalized flux", fontsize=15)
            tmp_axis.set_ylim(full_median - 3.* full_sigma, full_median + 3.*full_sigma)

            if i == 0:
                tmp_axis.set_title(f"{os.path.basename(self.filename)}: {title_str}", fontsize=12, pad=10)
            else:
                tmp_axis.set_title(f"{title_str}", pad=10)

            # Add secondary x-axis for integration indices
            axes_secondary = tmp_axis.secondary_xaxis('top')
            axes_secondary.set_xlabel("Integration Index", fontsize=12)

            axes_secondary.set_xticks(tick_positions[indices])
            axes_secondary.set_xticklabels([f"{int(idx)}" for idx in
                                            integration_indices[indices]])
            plt.tight_layout()

        self.figures.append(self.fig)

    def tso_x1dints_plot(self):
        """For TSO x1dints files, we plot the spectrum prior to any eclipse, on top
        of the spectrum during the eclipse. We assume that the first integraion occurs
        outside of any eclipse. Then find the spectrum with the overall minimum average,
        and assume that this is during the eclipse.
        """
        baseline = self.model.spec[0].spec_table.FLUX[1, :]
        baseline_waves = self.model.spec[0].spec_table.WAVELENGTH[1, :]
        minidx = 1
        minext = 0
        minmean = np.nanmean(baseline)

        n_extensions = len(self.model.spec)

        # Loop over spec extensions
        for ext in range(n_extensions):
            nints, npts = self.model.spec[ext].spec_table.FLUX.shape

            # Loop over integrations
            for i in range(nints):
                newmean = np.nanmean(self.model.spec[ext].spec_table.FLUX[i, :])
                if newmean < minmean:
                    minmean = newmean
                    minidx = i
                    minext = ext

        eclipse = self.model.spec[minext].spec_table.FLUX[minidx, :]
        eclipse_waves = self.model.spec[minext].spec_table.WAVELENGTH[minidx, :]

        # Will we ever need to make a thumnbail from these data?
        self.fig, ax = plt.subplots(figsize=(self.maxsize, self.maxsize))
        ax.plot(baseline_waves, baseline, color='blue', label='Baseline', alpha=0.5)
        ax.plot(eclipse_waves, eclipse, color='red', label='Lowest mean', alpha=0.5)
        ax.set_xlabel(f'Wavelength ({self.wavelength_units})')
        ax.set_ylabel(f'Flux ({self.flux_units})')
        ax.set_title(f'{self.model.meta.filename}: {self.model.meta.target.catalog_name}', fontsize=12)
        ax.legend(loc='upper right')
        self.figures.append(self.fig)

    def wfss_calc_yrange(self, spec, ignore_frac=0.1, padding=0.1):
        """Try to do something sort of intelligent to come up with a plot range
        for the 1d spectral plots. Often the flux values go unrealistically high
        at the red and blue ends. Would be nice to not let that drive the plot range.

        Parameters
        ----------
        spec : numpy.ndarray
            1D spectrum

        ignore_frac : float
            Fraction of pixels to ignore on each of the red and blue ends of
            the spectum. The max and min of the remaining values are used to
            determine the plot max and min

        padding : float
            Padding to add to the top and bottom of the plot so that the max and min
            points don't fall exactly at the plot edges. Units are fraction of
            the min/max values.

        Returns
        -------
        ylower : float
            Lower bound of the plot

        yupper : float
            Upper bound of the plot
        """
        fin = np.isfinite(spec)
        finite_flux = spec[fin]

        if len(finite_flux) > 0:
            # Ignore the bluest and reddest points
            n_ignore = int(len(finite_flux) * ignore_frac)
            chopped = finite_flux[n_ignore: len(finite_flux)-n_ignore]
            ylower = np.nanmin(chopped) - np.abs(np.nanmin(chopped) * padding)
            yupper = np.nanmax(chopped) * (1. + padding)
        else:
            ylower = 0
            yupper = 1
        return ylower, yupper

    def wfss_exclude_2d_edges(self, array):
        """Determine how many rows and columns of the WFSS 2D image to exclude for the purposes of determinig
        the scaling for the image. Often the edges of the 2D image have significantly increased or decreased
        background values, which can throw off the scaling

        Parameters
        ----------
        array : numpy.ndarray
            2D array

        Returns
        -------
        exclude_cols : int
            Number of columns to exclude from each of the left and right sides

        exclude_rows : int
            Number of rows to exclude from each of the top and bottom
        """
        # Default
        exclude_cols = 4
        exclude_rows = 4

        cal_ydim, cal_xdim = array.shape

        # For most 2d arrays, we can be aggressive in ignoring rows/cols towards the ends
        if cal_xdim > cal_ydim:
            exclude_cols = cal_xdim // 3
        else:
            exclude_row = cal_ydim // 3

        # If the array is very short or very narrow, include all but the outermost row or column
        if cal_ydim < 10:
            exclude_rows = 1
        if cal_xdim < 10:
            exclude_cols = 1
        return exclude_cols, exclude_rows

    def wfss_x1d(self):
        """Create a compound preview image for a source in WFSS data that shows:

           1. A cutout of the object in the direct (i2d) file
           2. Image of the 2D extracted spectrum from one of the cal files
           3. Plot of the 1D extracted spectrum (1st and 2nd order if present)
        """
        n_ext = len(self.model.spec)
        bright_idx = find_brightest_wfss_sources(self.model, level=3)

        # Often the brightest source is a saturated star. Let's try skipping over the brightest
        # source and creating a preview image for the 2nd brightest source.
        # Keep bright_idx as a list in case we want to create preview images for multiple wfss
        # sources in the future. Note that if there is only a single source (i.e. bright_idx) is
        # a single element list) or no objects (i.e. bright_idx is an empty list), then we keep
        # the list as-is. An empty list will not create any figures.
        if len(bright_idx) > 2:
            bright_idx = bright_idx[1:2]

        self.wfss_source_ids = []

        logging.debug(f'Brightest source index nums: {bright_idx}')
        logging.debug(f'This corresponds to source numbers: {[self.model.spec[0].spec_table.SOURCE_ID[idx] for idx in bright_idx]}')

        # Get the corresponding cal file data
        if '-' in self.model.meta.filename:

            # Get the list of contributing cal files from the association file
            file_path = Path(filesystem_path(self.model.meta.filename))
            asn_dir = file_path.parents[3] / "asn"
            spec3_asns = sorted(asn_dir.glob("jw*spec3*asn.json"))
            search_string = self.model.meta.filename.rsplit("_", 1)[0]
            matching_files = []
            for spec3_asn in spec3_asns:
                if search_string in spec3_asn.read_text(encoding="utf-8"):
                    matching_files.append(spec3_asn)

            spec3_asn = matching_files[-1]
            with(open(spec3_asn, "r", encoding="utf-8")) as asn_file:
                asn = json.load(asn_file)

            cal_files = []
            for member in asn['products'][0]['members']:
                if member['exptype'] == 'science':
                    cal_files.append(member['expname'])
            cal_files = sorted(cal_files)

            logging.debug(f'Found cal files: {cal_files}')

            # cal files are located in a different directory from the level 3 files
            cal_files = [filesystem_path(filename, check_existence=True) for filename in cal_files]
        else:  # Stage 2 x1d file
            suffix = self.filename.split('_')[-1].split('.fits')[0]
            cal_files = [self.filename.replace(suffix, 'cal')]

        cal_hdus = [fits.open(cal_file) for cal_file in cal_files]

        for idx in bright_idx:
            # Dictionary to hold all the 1D spectra
            spec1d = {}

            source_id = self.model.spec[0].spec_table.SOURCE_ID[idx]

            # Find the cal file extension where the 2D spectrum is located.
            # Get the cal data if the source is present
            cal_info = self.get_wfss_cal_data(cal_hdus, source_id)

            # Determine the source type and which flux units to use
            source_type = self.model.spec[0].spec_table.SOURCE_TYPE[idx]

            if source_type == 'EXTENDED':
                flux_col = 'SURF_BRIGHT'
            elif source_type == 'POINT':
                flux_col = 'FLUX'
            else:
                raise ValueError(f'Unrecognized source_type: {source_type}')

            # Get 1D spectrum from 0th extension and populate the dictionary
            spec1d['order'] = [self.model.spec[0].spectral_order]
            spec1d['flux'] = [np.array(self.model.spec[0].spec_table[flux_col][idx, :])]
            spec1d['wavelength'] = [np.array(self.model.spec[0].spec_table['WAVELENGTH'][idx, :])]

            # Get the units for later plotting
            flux_units = self.model.spec[0].spec_table.columns[flux_col].unit
            wavelength_units = self.model.spec[0].spec_table.columns['WAVELENGTH'].unit

            # If we're looking at flux, then convert Jy to Flambda
            if flux_col == 'FLUX':
                spec1d['flux'] = [Fnu_to_Flam(spec1d['wavelength'][0], spec1d['flux'][0])]
                flux_units = r'$F_\lambda$ ($erg/cm^2/s/\AA$)'

            # Loop over other extensions and look for the same source_id.
            for exten in range(1, n_ext):
                if source_id in self.model.spec[exten].spec_table['SOURCE_ID']:
                    row = self.model.spec[exten].spec_table[self.model.spec[exten].spec_table['SOURCE_ID'] == source_id][0]

                    fluxes = np.array(row[flux_col])
                    if flux_col == 'FLUX':
                        fluxes = Fnu_to_Flam(np.array(row['WAVELENGTH']), np.array(row[flux_col]))

                    spec1d['order'].append(self.model.spec[exten].spectral_order)
                    spec1d['flux'].append(fluxes)
                    spec1d['wavelength'].append(np.array(row['WAVELENGTH']))

            # Double check to be sure the wavelength and flux arrays are the same size
            for ordernum, flu, wav in zip(spec1d["order"], spec1d["flux"], spec1d["wavelength"]):
                if len(flu) != len(wav):
                    logging.error((f"MISMATCH IN LENGTHS OF WAVELENGTH AND FLUX ARRAYS: index {idx} "
                                   f"in extension {exten} of datamodel of {self.model.meta.filename}"))
                    continue

            # Remove any entries where e.g. the 2nd order data are all NaN
            spec1d = self.remove_wfss_nan_data(spec1d)

            # Get a list of all orders present for this source
            orders = sorted(list(set(spec1d['order'])))

            if len(orders) > 2:
                raise ValueError((f'Extracted {len(orders)} orders: {orders}. '
                                  'Plotting only supported for up to 2 orders.'))

            # Create the figure. At the moment, we support plotting only order 1,
            # or orders 1 and 2.
            figsize = (12, 8 + (len(orders) - 1) * 8)
            nrows = 2 + (len(orders) - 1) * 2
            self.fig = plt.figure(figsize=figsize)
            ax_i2d = plt.subplot2grid((nrows, 3), (0, 0))
            ax_2d_a = plt.subplot2grid((nrows, 3), (0, 1), colspan=2)
            ax_1d_a = plt.subplot2grid((nrows, 3), (1, 0), colspan=3)

            # If both order 1 and 2 are present, add plots for order 2,
            # and set the plot limits
            if len(orders) == 2:
                ax_2d_b = plt.subplot2grid((nrows, 3), (2, 0), colspan=3)
                ax_1d_b = plt.subplot2grid((nrows, 3), (3, 0), colspan=3)
                second = np.where(np.array(spec1d['order']) == orders[1])[0][0]
                ylower_b, yupper_b = self.wfss_calc_yrange(spec1d['flux'][second])

            # Overplot all 1d spectra for both orders
            order_a = orders[0]
            num_a = len(np.where(np.array(spec1d['order']) == order_a)[0])

            order_b = -999  # Will be ignored unless it changes to 2 below.
            if len(orders) == 2:
                order_b = orders[1]
                num_b = len(np.where(np.array(spec1d['order']) == order_b)[0])

            for i in range(len(spec1d['order'])):
                if spec1d['order'][i] == order_a:
                    ax_tmp = ax_1d_a
                elif spec1d['order'][i] == order_b:
                    ax_tmp = ax_1d_b
                else:
                    raise ValueError(f'Encountered unsupported spectral order {spec1d["order"][i]}')

                # If overplotting mulitple spectra, lower the alpha so that all will be visible
                alpha = 1.
                if num_a > 1:
                    alpha = 0.5

                # Plot the 1D spectrum
                ax_tmp.plot(spec1d['wavelength'][i], spec1d['flux'][i], alpha=alpha, ds='steps-mid')

            first = np.where(np.array(spec1d['order']) == order_a)[0][0]
            ylower_a, yupper_a = self.wfss_calc_yrange(spec1d['flux'][first])

            # Set 1st order 1D plot title and labels
            ax_1d_a.set_title(f'{self.model.meta.filename}, Source {source_id}, Order {order_a}')
            ax_1d_a.set_xlabel(f'Wavelength ({wavelength_units})')
            ax_1d_a.set_ylabel(f'{flux_units}')
            ax_1d_a.set_ylim(ylower_a, yupper_a)

            # Customize the area used to determine scaling based on instrument, filter, etc.
            exclude_cols, exclude_rows = self.wfss_exclude_2d_edges(cal_info[order_a]['data'])

            # Determine the min and max values for scaling the image
            cal_vmin_a = np.nanpercentile(cal_info[order_a]['data'][exclude_rows:-exclude_rows, exclude_cols:-exclude_cols], 1)
            cal_vmax_a = np.nanpercentile(cal_info[order_a]['data'][exclude_rows:-exclude_rows, exclude_cols:-exclude_cols], 99)

            if np.all(np.isnan(cal_info[order_a]['data'][exclude_rows:-exclude_rows, exclude_cols:-exclude_cols])):
                cal_vmin_a = np.nanmin(cal_info[order_a]['data'])
                cal_vmax_a = np.nanmax(cal_info[order_a]['data'])

            # Get basic figure properties
            yd, xd = cal_info[order_a]['data'].shape
            aspect, colorbar_orient, figsize = \
               determine_figure_properties(xd, yd, threshold=self.threshold_for_nonsquare_pix,
                                           maxsize=self.maxsize)

            # Show image
            self.show_image_in_axis(ax_2d_a, cal_info[order_a]['data'], cal_vmin_a, cal_vmax_a, aspect, colorbar_orient, num_ticks=5)
            ax_2d_a.set_xlabel('Pixel')
            ax_2d_a.set_ylabel('Pixel')
            ax_2d_a.set_title(f"{cal_info[order_a]['name']}, Source {cal_info[order_a]['source_id']}, Ext {cal_info[order_a]['ext']}, Order {order_a}")

            if len(orders) == 2:
                first = np.where(np.array(spec1d['order']) == order_b)[0][0]
                ylower_b, yupper_b = self.wfss_calc_yrange(spec1d['flux'][first])

                # Set 1st order 1D plot title and labels
                ax_1d_b.set_title(f'{self.model.meta.filename}, Source {source_id}, Order {order_b}')
                ax_1d_b.set_xlabel(f'Wavelength ({wavelength_units})')
                ax_1d_b.set_ylabel(f'{flux_units}')
                ax_1d_b.set_ylim(ylower_b, yupper_b)

                # Customize the area used to determine scaling based on instrument, filter, etc.
                exclude_cols, exclude_rows = self.wfss_exclude_2d_edges(cal_info[order_b]['data'])

                # Determine the min and max values for scaling the image
                cal_vmin_b = np.nanpercentile(cal_info[order_b]['data'][exclude_rows:-exclude_rows, exclude_cols:-exclude_cols], 1)
                cal_vmax_b = np.nanpercentile(cal_info[order_b]['data'][exclude_rows:-exclude_rows, exclude_cols:-exclude_cols], 99)

                # Get basic figure properties
                yd, xd = cal_info[order_b]['data'].shape
                aspect, colorbar_orient, figsize = \
                    determine_figure_properties(xd, yd, threshold=self.threshold_for_nonsquare_pix,
                                                maxsize=self.maxsize)

                # Show image
                self.show_image_in_axis(ax_2d_b, cal_info[order_b]['data'], cal_vmin_b, cal_vmax_b, aspect, colorbar_orient, num_ticks=5)
                ax_2d_b.set_xlabel('Pixel')
                ax_2d_b.set_ylabel('Pixel')
                ax_2d_b.set_title(f"{cal_info[order_b]['name']}, Source {cal_info[order_b]['source_id']}, Ext {cal_info[order_b]['ext']}, Order {order_b}")

            # Show the i2d cutout
            i2d_filename = os.path.join(os.path.dirname(self.filename), self.model.meta.direct_image)
            ax_i2d, im_i2d = self.plot_i2d_plus_source(i2d_filename, source_id, ax_i2d)

            self.fig.tight_layout(pad=2.0)
            self.figures.append(self.fig)
            self.wfss_source_ids.append(source_id)


def compile_segments(data_products):
    """
    Compiles extracted 1D spectra, corresponding timestamps,
    and wavelengths from a list of X1D data products output from
    the stage 2 pipeline. (Designed for NIRSpec BOTS data)

    Parameters
    ----------
    data_products : list of str
        A list of data products (X1DINT files).

    Returns
    -------
    all_spec_1D : numpy.ndarray
        A 2D array where each row corresponds to a spectrum from a single
        integration, and columns represent flux values at each wavelength.
    all_times : numpy.ndarray
        A 1D array containing the mid-integration times (e.g., BJD_TDB) for
        each spectrum in `all_spec_1D`.
    """

    data_products = [data_products] if isinstance(data_products, str) else data_products

    # Return empty arrays if the input list is empty.
    if not data_products:
        return None, None

    for i, product in enumerate(data_products):

        x1d = datamodels.open(product)

        n_spec, n_pix = x1d.spec[0].spec_table.WAVELENGTH.shape
        seg_spec_1D = np.zeros([n_spec, n_pix])
        wave_um = x1d.spec[0].spec_table.WAVELENGTH[0, :]

        for j in range(n_spec):
            seg_spec_1D[j, :] = x1d.spec[0].spec_table.FLUX[j, :]

        if i == 0:
            all_spec_1D = seg_spec_1D
            all_times = x1d.int_times.int_mid_BJD_TDB
        if i > 0:
            all_spec_1D = np.concatenate((all_spec_1D, seg_spec_1D), axis=0)
            all_times = np.concatenate((all_times,
                                        x1d.int_times.int_mid_BJD_TDB),
                                       axis=0)

    # We also trim several columns at the start and end of the spectra.
    # These belong to the reference pixels and are marked 'nan'.
    all_spec_1D = all_spec_1D[:, 5:-5]
    wave_um = wave_um[5:-5]

    return all_spec_1D, all_times, wave_um


def determine_aspect(xdim, ydim, threshold=0.15):
    """Based on the dimensions of the 2D data, determine which aspect
    to use for plt.imshow. Arrays that are far from square will use "auto",
    in which pixels are allowed to be non-square, and the array is manipulated
    to fill the figure. Arrays that are close to square will use "equal", which
    enforces square pixels. Default colorbar orientation is vertical, to the right
    of the array. But if the array is wider than it is tall, then the colorbar
    moves to the horizontal orentation, below the array.

    Parameters
    ----------
    xdim : int
        Number of columns in the data array

    ydim : int
        Number of rows in the data array

    threshold : float
        Threshold value for the ratio of xdim/ydim. Ratio values below
        this value, or above the inverse of this value, will cause the
        aspect value to be 'auto'

    Returns
    -------
    aspect : str
        Aspect type for the array
    """
    dim_ratio = xdim / ydim
    if dim_ratio < threshold or dim_ratio > (1 / threshold):
        aspect = 'auto'
    else:
        aspect = 'equal'
    return aspect


def determine_cbar_orient(xdim, ydim):
    """Determine whether the colorbar should be beneath the array or to the right. Default
    value is to the right. Let's keep it there unless the array starts to become significantly
    non-square (although with a lower threshold than the aspect function uses.)

    Parameters
    ----------
    xdim : int
        Number of columns in the data array

    ydim : int
        Number of rows in the data array

    Returns
    -------
    orient : str
        Orientation
    """
    dim_ratio = xdim / ydim
    if dim_ratio <= 1.15:
        # X-dimension is smaller
        orient = "vertical"
    else:
        orient = "horizontal"
    return orient


def determine_default_figsize(xdim, ydim, maxsize=8, aspect=None, ratio_limit=5):
    """Determine the default figure size (NOT axes size within a figure), given the array dimensions.

    Parameters
    ----------
    xdim : int
        Number of columns in the data array

    ydim : int
        Number of rows in the data array

    maxsize : float
        Length of the largest dimension, in units accepted by plt.subplots

    aspect : str
        Description of the aspect ratio matplotlib will use. 'auto' means
        pixels are not required to be square. This is good for figures that
        are much wider than they are long. 'equal' will keep the pixels square.

    ratio_limit : float
        Threshold value for xsize/ysize ratio. If the aspect is "auto" and the
        x/y ratio is over ratio_limit or under 1/ratio_limit, then reshape the
        figure to have a ratio of ratio_limit.

    Returns
    -------
    figsize : tup
        (xsize, ysize)
    """
    if xdim == 0:
        logging.warning(f'xdim number of figure columns is 0 for {self.filename}. Setting to 1.')
        xdim = 1

    if ydim == 0:
        logging.warning(f'ydim number of figure rows is 0 for {self.filename}. Setting to 1.')
        ydim = 1

    if xdim >= ydim:
        figsize = (maxsize, maxsize * ydim / xdim)
    else:
        figsize = (maxsize * xdim / ydim, maxsize)

    # If the aspect is "auto" and the x/y ratio is over N or under 1/N,
    # then reshape the figure to have a ratio of N.
    if aspect == 'auto':
        ratio = xdim / ydim
        if ratio > ratio_limit:
            ratio = ratio_limit
        if ratio < (1. / ratio_limit):
            ratio = (1. / ratio_limit)

        if xdim >= ydim:
            figsize = (maxsize, maxsize / ratio)
        else:
            figsize = (maxsize * ratio, maxsize)

    return figsize


def determine_figure_properties(xdim, ydim, threshold=0.15, maxsize=8):
    """Based on the dimensions of the 2D data, determine which aspect
    to use for plt.imshow. Arrays that are far from square will use "auto",
    in which pixels are allowed to be non-square, and the array is manipulated
    to fill the figure. Arrays that are close to square will use "equal", which
    enforces square pixels.

    Default colorbar orientation is vertical, to the right
    of the array. But if the array is wider than it is tall, then the colorbar
    moves to the horizontal orentation, below the array.

    Also provide a default figure size. This may be overridden later, especially
    depending on the aspect value.

    Parameters
    ----------
    xdim : int
        Number of columns in the data array

    ydim : int
        Number of rows in the data array

    threshold : float
        Threshold value for the ratio of xdim/ydim. Ratio values below
        this value, or above the inverse of this value, will cause the
        aspect value to be 'auto'

    maxsize : float
        Length of the largest dimension, in units accepted by plt.subplots

    Returns
    -------
    aspect : str
        Aspect type for the array
    """
    aspect_value = determine_aspect(xdim, ydim, threshold=threshold)
    cbar_orient = determine_cbar_orient(xdim, ydim)
    figsize_value = determine_default_figsize(xdim, ydim, maxsize=maxsize, aspect=aspect_value)
    return aspect_value, cbar_orient, figsize_value


def find_brightest_wfss_sources(model, level=3):
    """Determine the `nsources` brightest sources in the WFSS file. Do this using the
    mean value. Work on only the model.spec[0].spec_table. Note that if there are dithers,
    the source may not be present in all extensions.

    Parameters
    ----------
    model : stdatamodels.datamodel
        Datamodel instance

    level : int
        Calibration level of the data. e.g. 2 or 3.

    Returns
    -------
    brightest : numpy.ndarray
        1D array of index numbers corresponding to the sources in order from brightest
        to dimmest.
    """
    num_sources = model.spec[0].spec_table.shape[0]

    medians = []
    sources = []
    for source in range(num_sources):

        # Level 2 x1d files do not have SOURCE_TYPE columns, while level 3 x1d files do.
        if level == 3:
            # Ignore sources where the source_id is empty, which indicates a larger problem.
            if model.spec[0].spec_table['SOURCE_TYPE'][source] != '':
                medians.append(np.nansum(model.spec[0].spec_table['SURF_BRIGHT'][source, :]))
                sources.append(source)
        elif level == 2:
            surf_bright = model.spec[0].spec_table['SURF_BRIGHT'][source]
            if np.isfinite(surf_bright):
                medians.append(surf_bright)
                sources.append(source)
        else:
            raise ValueError(f'The level param in find_brightest_wfss_sources must be either 2 or 3. Got {level}.')

    idxs = np.argsort(medians)[::-1]
    brightest = np.array(sources)[idxs]

    return brightest


def Fnu_to_Flam(wave_micron, flux_jansky):
    """Convert Jansky flux units to erg/s/cm^2/Angstrom with an input wavelength in microns

    Parameters
    ----------
    wave_micron : numpy.ndarray
        Array of wavelengths in microns

    flux_jansky : numpy.ndarray
        Array of fluxes in Jansky

    Returns
    -------
    f_lambda : numpy.ndarray
        Array of f_lambda values
    """
    f_lambda = 1E-21 * flux_jansky * (const.c.value) / (wave_micron**2) # erg/s/cm^2/Angstom
    return f_lambda


def formatted_tick_labels(tick_vals):
    """Given an array of tick values, create formatted tick labels based on the value of
    the numbers.

    Parameters
    ----------
    tick_vals : numpy.ndarray
        Array of tick values (floats)

    Returns
    -------
    tick_str : list
        List of string tick labels
    """
    delta = tick_vals[-1] - tick_vals[0]
    if delta >= 100:
        dig = 0
    elif ((delta < 100) & (delta >= 10)):
        dig = 1
    elif ((delta < 10) & (delta >= 1)):
        dig = 2
    elif delta < 1:
        dig = 3
    else:
        dig = 2
    format_string = "%.{}f".format(dig)
    tick_str = [format_string % number for number in tick_vals]

    # For cases with very small ranges in the signal, use scientific notation
    zeros = np.log10(np.abs(delta))
    if zeros < -3:
        tick_str = [f"{num:.3e}" for num in tick_vals]
    return tick_str


def get_screen_points_per_image_pixel(figure, axis):
    """When using matplotlib.pyplot.scatter, the marker size is specified in points
    squared (where a point is 1/72 of an inch), while we often want to overlay a
    circle with a radius in units of pixels in the image data coordinates. This
    function will calculate the number of screen points per image pixel

    Parameters
    ----------
    figure : matplotlib.pyplot.figure.Figure
        Figure where the plotting will be done

    axis : matplotlib.pyplot.axis.Axis
        Axis from the figure where the plotting will be done

    Returns
    -------
    points_per_pixel : float
        The number of screen points per pixel for the given figure and axis
    """
    # Convert radius from data coordinates (pixels) to points
    # Get the axis size in pixels
    bbox = axis.get_window_extent().transformed(figure.dpi_scale_trans.inverted())
    axis_width_inches = bbox.width
    axis_height_inches = bbox.height

    # Get data limits
    xlim = axis.get_xlim()
    ylim = axis.get_ylim()
    data_width = xlim[1] - xlim[0]
    data_height = ylim[1] - ylim[0]

    # Calculate points per data unit (average of x and y)
    points_per_pixel_x = (axis_width_inches * 72) / data_width
    points_per_pixel_y = (axis_height_inches * 72) / data_height
    points_per_pixel = (points_per_pixel_x + points_per_pixel_y) / 2
    return points_per_pixel


def hide_axes(fig):
    """Hide all axes and labels for the given figure. This helps when making a thumbnail
    image.

    Parameters
    ----------
    fig : matplotlib.pyplot.figure
        Matplotlib figure instance

    Returns
    -------
    fig : matplotlib.pyplot.figure
        Modified figure instance
    """
    for ax in fig.get_axes():
        ax.set_axis_off()              # hides everything (ticks, labels, spines)
        ax.set_title("")               # clears title if any
    return fig


def shift_data_get_ticks(image, minval, maxval, num_ticks=5, min_range_for_logscale=1):
    """Given a multi-dimensional array along with the minimum and maximum values for the colorbar in imshow(),
    along with the desired number of ticks to add to the colorbar, shift the data in the image such that the
    minimum pixel value is 1. Then calculate values for the number of tick marks. Note that the tick mark values
    here will be in the shifted data space. Then calculate the corresponding tick values in the unshifted data space.

    Parameters
    ----------
    image : numpy.ndarray
        Multidimensional array

    minval : float
        Minimum value for the colormap to use in imshow

    maxval : float
        Maximum value for the colormap to use in imshow

    num_ticks : int
        Number of tick values to create

    min_range_for_logscale : float
        maxval - minval must be at least this much in order to use log scaling. If the
        difference is less, linear scaling is used.

    Returns
    -------
    shifted_image : numpy.ndarray
        ``image``, shifted such that the minimum pixel value is 1.0. Primarily intended
        for log scaling in imshow

    shifted_min : float
        Minimum pixel value in the shifted data

    shifted_max : float
        Maximum pixel value in the shifted data

    shifted_tickvals : numpy.ndarray
        Array of tick values in the shifted data space

    unshifted_tickvals : numpy.ndarray
        Array of tick values in the original data (``image``) data space
    """
    shifted_image = image - minval + 1
    shifted_min = 1
    shifted_max = maxval - minval + 1

    # Generate tick labels
    if shifted_max - shifted_min > min_range_for_logscale:
        shifted_tickvals = np.logspace(np.log10(shifted_min), np.log10(shifted_max), num_ticks)
    else:
        shifted_tickvals = np.linspace(shifted_min, shifted_max, num_ticks)

    unshifted_tickvals =  shifted_tickvals + minval - 1

    return shifted_image, shifted_min, shifted_max, shifted_tickvals, unshifted_tickvals


def sigma_clip_ignore_nan(data, sigma=3):
    """Perform sigma clipping on input data, while ignoring warnings about there being
    invalid values in the data

    Parameters
    ----------
    data : numpy.ndarray
        Array to be clipped

    sigma : float
        Sigma value to use for clipping

    Returns
    -------
    clp : numpy.ndarray
        Sigma-clipped array
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning, append=True)
        # Filter the warning specifically for astropy.stats.sigma_clipping
        warnings.filterwarnings("ignore", message="Input data contains invalid values", module="astropy.stats.sigma_clipping")
        clp = sigma_clip(data, sigma=sigma)
    return clp
