#! /usr/bin/env python

"""
Create a preview image from a fits file containing an observation.

This module creates and saves a "preview image" from a fits file
that contains a JWST observation. Data from the user-supplied 
`extension` of the file are read in, along with the `PIXELDQ`
extension if present. For each integration in the exposure, the
first group is subtracted from the final group in order to create
a difference image. The lower and upper limits to be displayed are
defined as the `clip_percent` and (1. - `clip_percent') percentile
signals. Matplotlib is then used to display a linear- or log-stretched
version of the image, with accompanying colorbar. The image is then 
saved.

Authors:
--------

    Bryan Hilbert

Use:
----

    This module can be imported as such:

    >>> from preview_image import Image
    im = Image(my_file, "SCI")
    im.clip_percent = 0.01
    im.scaling = 'log'
    im.output_format = 'jpg'
    im.make_image()
"""

import os
import sys

from astropy.io import fits
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np

from jwst.datamodels import dqflags

class Image():
    
    def __init__(self, filename, extension):
        """Initialize the class.
        
        Parameters
        ----------
        filename : str
            Name of fits file containing data
        extension : str
            Extension name to be read in
        """
        self.file = filename
        self.clip_percent = 0.01
        self.scaling = 'log'
        self.output_format = 'jpg'

        # Read in file
        self.data, self.dq = self.get_data(self.file, extension)
        
    def difference_image(self, data):
        """
        Create a difference image from the data. Use last
        group minus first group in order to maximize signal
        to noise. With 4D input, make a separate difference
        image for each integration.

        Parameters:
        ----------
        data : obj
            4D numpy ndarray array of floats

        Returns:
        --------
        result : obj
            3D numpy ndarray containing the difference
            image(s) from the input exposure
        """
        return data[:, -1, :, :] - data[:, 0, :, :]

    def find_limits(self, data, pixmap, clipperc):
        """
        Find the minimum and maximum signal levels after 
        clipping the top and bottom x% of the pixels. 

        Parameters:
        ----------
        data : obj
            2D numpy ndarray of floats
        pixmap : obj
            2D numpy ndarray boolean array of science pixel locations
            (True for science pixels, False for non-science pix)
        clipperc : float 
            Fraction of top and bottom signal levels to clip 
            (e.g. 0.01 means to clip brightest and dimmest 1% 
            of pixels)

        Returns:
        --------
        results : tuple
            Tuple of floats, minimum and maximum signal levels
        """
        nelem = np.sum(pixmap)
        numclip = np.int(clipperc * nelem)
        sorted = np.sort(data[pixmap], axis=None)
        minval = sorted[numclip]
        maxval = sorted[-numclip-1]
        return (minval, maxval)

    def get_data(self, filename, ext):
        """
        Read in the data from the given file and extension
        Also find how many rows/cols of reference pixels are
        present.

        Parameters:
        ----------
        filename : str
            Name of fits file containing data
        ext : str
            Extension name to be read in

        Returns:
        --------
        data : obj
            Science data from file. A 2-, 3-, or 4D numpy ndarray
        dq : obj
            2D ndarray boolean map of reference pixels. Science
            pixels flagged as True and non-science pixels are False
        """
        if os.path.isfile(filename):
            extnames = []
            with fits.open(filename) as hdulist:
                for exten in hdulist:
                    try:
                        extnames.append(exten.header['EXTNAME'])
                    except:
                        pass
                if ext in extnames:
                    data = hdulist[ext].data
                else:
                    raise ValueError(("WARNING: no {} extension in {}!"
                                      .format(ext, filename)))
                if 'PIXELDQ' in extnames:
                    dq = hdulist['PIXELDQ'].data
                    dq = (dq & dqflags.pixel['NON_SCIENCE'] == 0)
                else:
                    yd, xd = data.shape[-2:]
                    dq = np.ones((yd, xd), dtype="bool")
        else:
            raise FileNotFoundError(("WARNING: {} does not exist!"
                                     .format(filename)))
        return data, dq
        
    def make_figure(self, image, integration_number, min_value, max_value,
                    scale, maxsize = 8):
        """
        Create the matplotlib figure of the image

        Parameters:
        ----------
        image : obj
            2D numpy ndarray of floats
        integration_number : int 
            Integration number within exposure
        min_value : float
            Minimum value for display
        max_value : float
            Maximum value for display
        scale : str
            Image scaling ('log', 'linear')

        Returns:
        --------
        result : obj
            Matplotlib Figure object
        """
        # Check the input scaling
        if scale not in ['linear','log']:
            raise ValueError(("WARNING: scaling option {} not supported."
                              .format(scale)))
        
        # Set the figure size
        yd, xd = image.shape
        ratio = yd / xd
        if xd >= yd:
            xsize = maxsize
            ysize = maxsize * ratio
        else:
            ysize = maxsize
            xsize = maxsize / ratio
        fig, ax = plt.subplots(figsize=(xsize, ysize))
        
        if scale == 'log':
            # Shift data so everything is positive
            shiftdata = image - min_value + 1
            shiftmin = 1
            shiftmax = max_value - min_value + 1

            # Log normalize the colormap
            cax = ax.imshow(shiftdata,
                            norm=colors.LogNorm(vmin=shiftmin, vmax=shiftmax),
                            cmap='gray')
            
            # Add colorbar, with original data values
            tickvals = np.logspace(np.log10(shiftmin), np.log10(shiftmax), 5)
            tlabelflt = tickvals + min_value - 1
            tlabelstr = ["%.1f" % number for number in tlabelflt]
            cbar = fig.colorbar(cax, ticks=tickvals)
            cbar.ax.set_yticklabels(tlabelstr)
            ax.set_xlabel('Pixels')
            ax.set_ylabel('Pixels')
            plt.rcParams.update({'axes.titlesize': 'small'})

        elif scale == 'linear':
            cax = ax.imshow(image, clim=(min_value, max_value), cmap='gray')
            cbar = fig.colorbar(cax)
            ax.set_xlabel('Pixels')
            ax.set_ylabel('Pixels')            

        ax.set_title(self.file + ' Int: {}'.format(np.int(integration_number)))
        return fig

    def make_image(self):
        """
        MAIN FUNCTION
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
        
        for i in range(nint):
            frame = diff_img[i, :, :]
            
            # Find signal limits for the display
            minval, maxval = self.find_limits(frame, self.dq,
                                              self.clip_percent)

            # Create matplotlib object
            indir, infile = os.path.split(self.file)
            suffix = '_integ{}.{}'.format(i, self.output_format)
            outfile = os.path.join(indir, infile.split('.')[0] + suffix)
            fig = self.make_figure(frame, i, minval, maxval, self.scaling.lower())
            self.save_image(fig, outfile)
            plt.close()

    @staticmethod
    def save_image(image, fname):
        """
        Save an image in the requested output format

        Parameters:
        ----------
        image : obj
            A matplotlib figure object
        fname : str
            Output filename
        """
        image.savefig(fname, bbox_inches='tight')
