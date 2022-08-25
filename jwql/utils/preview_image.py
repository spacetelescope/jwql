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

import logging
import os
import socket
import warnings

from astropy.io import fits
import numpy as np

from jwql.utils import permissions
from jwql.utils.utils import get_config

# Use the 'Agg' backend to avoid invoking $DISPLAY
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.ticker import AutoMinorLocator

# Only import jwst if not running from readthedocs
# Determine if the code is being run as part of a Readthedocs build
ON_READTHEDOCS = False
if 'READTHEDOCS' in os.environ:
    ON_READTHEDOCS = os.environ['READTHEDOCS']

#if 'build' and 'project' not in socket.gethostname():
#    ON_READTHEDOCS = False
if not ON_READTHEDOCS:
    from jwst.datamodels import dqflags

ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

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

        # Combine maps of science pixels and finite pixels
        pixmap = self.dq & finite

        # If all non-science pixels are NaN then we're sunk. Scale
        # from 0 to 1.
        if not np.any(pixmap):
            logging.info('No pixels with finite signal. Scaling from 0 to 1')
            return (0., 1.)

        sorted_pix = np.sort(data[pixmap], axis=None)

        # Determine how many pixels to clip off of the high and low ends
        nelem = np.sum(pixmap)
        numclip = np.int32(self.clip_percent * nelem)

        # Determine min and max scaling levels
        minval = sorted_pix[numclip]
        maxval = sorted_pix[-numclip - 1]
        return (minval, maxval)

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
                for exten in hdulist:
                    try:
                        extnames.append(exten.header['EXTNAME'])
                    except KeyError:
                        pass
                if ext in extnames:
                    dimensions = len(hdulist[ext].data.shape)
                    if dimensions == 4:
                        data = hdulist[ext].data[:, [0, -1], :, :].astype(np.float)
                    else:
                        data = hdulist[ext].data.astype(np.float)
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
                                #dq = crop_to_subarray(dq, hdulist[0].header, xd, yd)
                                #dq = expand_for_i2d(dq, xd, yd)
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

        if scale == 'log':

            # Shift data so everything is positive
            shiftdata = image - min_value + 1
            shiftmin = 1
            shiftmax = max_value - min_value + 1

            # If making a thumbnail, make a figure with no axes
            if thumbnail:
                self.fig, ax = plt.subplots(figsize=(3, 3))
                cax = ax.imshow(shiftdata,
                                norm=colors.LogNorm(vmin=shiftmin,
                                                    vmax=shiftmax),
                                cmap=self.cmap)
                # Invert y axis
                plt.gca().invert_yaxis()

                plt.axis('off')
                cax.axes.get_xaxis().set_visible(False)
                cax.axes.get_yaxis().set_visible(False)

            # If preview image, add axes and colorbars
            else:
                self.fig, ax = plt.subplots(figsize=(xsize, ysize))
                cax = ax.imshow(shiftdata,
                                norm=colors.LogNorm(vmin=shiftmin,
                                                    vmax=shiftmax),
                                cmap=self.cmap)
                # Invert y axis
                plt.gca().invert_yaxis()

                # Add colorbar, with original data values
                tickvals = np.logspace(np.log10(shiftmin), np.log10(shiftmax), 5)
                tlabelflt = tickvals + min_value - 1

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
                cbar = self.fig.colorbar(cax, ticks=tickvals)

                # This seems to correctly remove the ticks and labels we want to remove. It gives a warning that
                # it doesn't work on log scales, which we don't care about. So let's ignore that warning.
                warnings.filterwarnings("ignore", message="AutoMinorLocator does not work with logarithmic scale")
                cbar.ax.yaxis.set_minor_locator(AutoMinorLocator(n=0))

                cbar.ax.set_yticklabels(tlabelstr)
                cbar.ax.tick_params(labelsize=maxsize * 5. / 4)
                cbar.ax.set_ylabel(self.units, labelpad=10, rotation=270)
                ax.set_xlabel('Pixels', fontsize=maxsize * 5. / 4)
                ax.set_ylabel('Pixels', fontsize=maxsize * 5. / 4)
                ax.tick_params(labelsize=maxsize)
                plt.rcParams.update({'axes.titlesize': 'small'})
                plt.rcParams.update({'font.size': maxsize * 5. / 4})
                plt.rcParams.update({'axes.labelsize': maxsize * 5. / 4})
                plt.rcParams.update({'ytick.labelsize': maxsize * 5. / 4})
                plt.rcParams.update({'xtick.labelsize': maxsize * 5. / 4})

        elif scale == 'linear':
            self.fig, ax = plt.subplots(figsize=(xsize, ysize))
            cax = ax.imshow(image, clim=(min_value, max_value), cmap=self.cmap)

            # Invert y axis
            plt.gca().invert_yaxis()

            if not thumbnail:
                cbar = fig.colorbar(cax)
                ax.set_xlabel('Pixels')
                ax.set_ylabel('Pixels')

        # If preview image, set a title
        if not thumbnail:
            filename = os.path.split(self.file)[-1]
            ax.set_title(filename + ' Int: {}'.format(np.int(integration_number)))

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

        # If there are 10 integrations or less, make image for every integration
        # If there are more than 10 integrations, then make image for every 10th integration
        # If there are more than 100 integrations, then make image for every 100th integration
        if nint <= 10:
            integration_range = range(nint)
        elif 11 <= nint <= 100:
            integration_range = range(0, nint, 10)
        else:
            integration_range = range(0, nint, 100)

        for i in integration_range:
            frame = diff_img[i, :, :]

            # Find signal limits for the display
            minval, maxval = self.find_limits(frame)

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
    return arr[ystart : (ystart + ylen), xstart : (xstart + xlen)]


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
                new_array_y[y_offset : (y_offset + ydim_array), :] = array
            elif (ydim_array > ydim):
                new_array_y = array[y_offset : (y_offset + ydim), :]
        else:
            new_array_y = array
        if (xdim_array != xdim):
            new_array_x = np.zeros((ydim, xdim), dtype=bool)  # Added rows/cols will be all zeros
            x_offset = abs((xdim - xdim_array) // 2)
            if (xdim_array < xdim):
                new_array_x[:, x_offset : (x_offset + xdim_array)] = new_array_y
            elif (xdim_array > xdim):
                new_array_x = new_array_y[:, x_offset : (x_offset + xdim)]
        else:
            new_array_x = new_array_y
        return new_array_x
    else:
        return array
