#! /usr/bin/env python

"""Create files for dark monitor testing"""

from astropy.io import fits
import numpy as np

im1 = np.zeros((10, 10)) + 5.
im2 = np.zeros((10, 10)) + 10.
im3 = np.zeros((10, 10)) + 15.

header = fits.getheader('base_input.fits')
header['INSTRUME'] = 'NIRCAM'
header['SUBSTRT1'] = 0
header['SUBSTRT2'] = 0
header['SUBSIZE1'] = 10
header['SUBSIZE2'] = 10
header['TSAMPLE'] = 10
header['TFRAME'] = 10.5

for i, im in enumerate([im1, im2, im3]):
    hdu0 = fits.PrimaryHDU(data=None, header=header)
    hdu1 = fits.ImageHDU(im)
    hdulist = fits.HDUList([hdu0, hdu1])
    hdulist.writeto('test_image_{}.fits'.format(i+1), overwrite=True)
