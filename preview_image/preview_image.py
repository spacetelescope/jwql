#! /usr/bin/env python

"""
Create a preview image from a fits file
containing an observation

Open questions:

Q: What if there is >1 integration? 
A: Currently the script makes a separate preview image
   for each

Q: Are there cases where we want to make an image of the data
as contained in the file, rather than a CDS image?
A: Maybe, but this isn't supported yet

Code summary:

1. Read in file
  a. grab data from input extension ('SCI' is default)
  b. grab pixeldq data if present, create map of non-science pixels
2. Create a difference image for each integration
3. Clip the brightest and darkest N% of the pixels (excluding 
   non-science pixels) to determine the min and max scaling values
4. Create image from each difference image using log (or linear) 
   scaling
5. Save using the input format 
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from astropy.io import fits
from jwst.datamodels import dqflags

class Image():
    def __init__(self, file, extension):
        self.file = file
        self.clip_percent = 0.01
        self.scaling = 'log'
        self.output_format = 'jpg'

        # Read in file
        self.data, self.scipix = self.get_data(self.file, extension)
        
    def find_limits(self, data, pixmap, clipperc):
        """
        Find the minimum and maximum signal levels after 
        clipping the top and bottom x% of the pixels. 

        Parameters:
        ----------
        data -- 2D ndarray of floats
        pixmap -- 2D boolean array of science pixel locations
                (True for science pixels, False for non-science pix)
        clipperc -- Float, Fraction of top and bottom signal
                    levels to clip (e.g. 0.01 means to clip brightest and
                    dimmest 1% of pixels)

        Returns:
        --------
        Tuple of minimum and maximum signal levels
        """
        nelem = np.sum(pixmap)
        numclip = np.int(clipperc * nelem)
        sorted = np.sort(data[pixmap], axis=None)
        minval = sorted[numclip]
        maxval = sorted[-numclip-1]
        return (minval, maxval)

    def diff_img(self, data):
        """
        Create a difference image from the data. Use last
        group minus first group in order to maximize signal
        to noise. If input is 4D, make a separate difference
        image for each integration.

        Parameters:
        ----------
        data -- 3D or 4D ndarray array

        Returns:
        --------
        Difference image(s)
        """
        ndim = len(data.shape)
        if ndim == 3:
            diff = data[-1, :, :] - data[0, :, :]
        elif ndim == 4:
            diff = data[0, -1, :, :] - data[:, 0, :, :]
        else:
            print(("Warning, difference imaging doesn't support"
                   "arrays with {} dimensions!".format(ndim)))
        return diff

    def get_data(self, filename, ext):
        """
        Read in the data from the given file and extension
        Also find how many rows/cols of reference pixels are
        present.

        Parameters:
        ----------
        filename -- string: Name of fits file containing data
        ext -- string: Extension name to be read in

        Returns:
        --------
        data -- science data from file. A 2-, 3-, or 4D ndarray
        dq -- 2D ndarray boolean map of reference pixels. Science
              pixels flagged as True and non-science pixels are False
        """
        if os.path.isfile(filename):
            extnames = []
            with fits.open(filename) as h:
                for e in h:
                    try:
                        extnames.append(e.header['EXTNAME'])
                    except:
                        pass
                if ext in extnames:
                    data = h[ext].data
                else:
                    raise ValueError(("WARNING: no {} extension in {}!"
                                      .format(ext, filename)))
                if 'PIXELDQ' in extnames:
                    dq = h['PIXELDQ'].data
                    dq = (dq & dqflags.pixel['NON_SCIENCE'] == 0)
                else:
                    yd, xd = data.shape[-2:]
                    dq = np.ones((yd, xd), dtype="bool")
        else:
            raise FileNotFoundError(("WARNING: {} does not exist!"
                                     .format(filename)))
        return data, dq
        
    def make_figure(self, image, intnum, minv, maxv, scale, maxsize = 8):
        """
        Create the matplotlib figure of the image

        Parameters:
        ----------
        image -- 2D ndarray of floats
        intum -- Integer. Integration number within exposure
        minv -- Float. Minimum value for display
        maxv -- Float. Maximum value for display
        scale -- Image scaling (log, linear)

        Returns:
        --------
        Matplotlib AxesImage
        """
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
            # Determine scaling
            mindata = np.min(image)
            maxdata = np.max(image)

            # Shift data so everything is positive
            shiftdata = image - mindata + 1
            shiftmin = 1
            shiftmax = maxdata - mindata + 1

            # Log normalize the colormap
            cax = ax.imshow(shiftdata,
                            norm=colors.LogNorm(vmin=shiftmin, vmax=shiftmax),
                            cmap='gray')#PuBu_r')
            
            # Add colorbar, with original data values
            tickvals = np.logspace(np.log10(shiftmin), np.log10(shiftmax), 5)
            tlabelflt = tickvals + mindata - 1
            tlabelstr = ["%.1f" % number for number in tlabelflt]
            cbar = fig.colorbar(cax, ticks=tickvals)
            cbar.ax.set_yticklabels(tlabelstr)
            ax.set_xlabel('Pixels')
            ax.set_ylabel('Pixels')
            plt.rcParams.update({'axes.titlesize': 'small'})

        elif scale == 'linear':
            cax = ax.imshow(image, clim=(minv, maxv), cmap='gray')
            cbar = fig.colorbar(cax)
            ax.set_xlabel('Pixels')
            ax.set_ylabel('Pixels')            

        ax.set_title(self.file + ' Int: {}'.format(np.int(intnum)))
        return fig

    def make_image(self):
        """
        MAIN FUNCTION
        """
        # Create difference image(s)
        diff_img = self.diff_img(self.data)

        # If there are multiple integrations in the file,
        # work on one integration at a time from here onwards
        ndim = len(diff_img.shape)
        if ndim == 2:
            diff_img = np.expand_dims(diff_img, axis=0)
        nint, ny, nx = diff_img.shape
        
        for i in range(nint):
            frame = diff_img[i, :, :]
            
            # Find signal limits for the display
            minval, maxval = self.find_limits(frame, self.scipix,
                                              self.clip_percent)

            # Create matplotlib object
            indir, infile = os.path.split(self.file)
            suffix = '_integ{}.{}'.format(i, self.output_format)
            outfile = os.path.join(indir, infile.split('.')[0] + suffix)
            fig = self.make_figure(frame, i, minval, maxval, self.scaling)
            self.save_image(fig, outfile)
  
    def save_image(self, image, fname):
        """
        Save an image in the requested output format

        Parameters:
        ----------
        image -- A matplotlib figure object
        fname -- Output filename

        Returns:
        --------
        Nothing
        """
        image.savefig(fname, bbox_inches='tight')
