#! /usr/bin/env python

"""Create files for dark monitor testing"""

from astropy.io import fits
import numpy as np
from jwst.datamodels import dqflags

im1 = np.zeros((10, 10)) + 5.
im2 = np.zeros((10, 10)) + 10.
im3 = np.zeros((10, 10)) + 15.

pixeldq = np.zeros((10, 10)).astype(np.int)

header = fits.getheader('base_input.fits')
header['INSTRUME'] = 'NIRCAM'
header['DETECTOR'] = 'NRCA1'
header['SUBARRAY'] = 'NRCA1_CUSTOM'
header['SUBSTRT1'] = 0
header['SUBSTRT2'] = 0
header['SUBSIZE1'] = 10
header['SUBSIZE2'] = 10
header['TSAMPLE'] = 10
header['TFRAME'] = 10.5
header['EFFINTTM'] = 10.5
header['NINTS'] = 1

for i, im in enumerate([im1, im2, im3]):
    hdu0 = fits.PrimaryHDU(data=None, header=header)
    hdu1 = fits.ImageHDU(im)
    hdu2 = fits.ImageHDU(pixeldq, name='PIXELDQ')
    hdulist = fits.HDUList([hdu0, hdu1, hdu2])
    hdulist.writeto('test_image_{}.fits'.format(i+1), overwrite=True)

# Full frame file - need to include dq array
header['INSTRUME'] = 'NIRCAM'
header['DETECTOR'] = 'NRCA1'
header['SUBARRAY'] = 'NRCA1_FULL'
header['SUBSTRT1'] = 0
header['SUBSTRT2'] = 0
header['SUBSIZE1'] = 2048
header['SUBSIZE2'] = 2048
header['TSAMPLE'] = 10
header['TFRAME'] = 10.5

data = np.zeros((2048, 2048))
dq = np.zeros((2048, 2048)).astype(np.int)
dq[0:4, :] = dqflags.pixel['REFERENCE_PIXEL']
dq[2044:, :] = dqflags.pixel['REFERENCE_PIXEL']
dq[:, 0:4] = dqflags.pixel['REFERENCE_PIXEL']
dq[:, 2044:] = dqflags.pixel['REFERENCE_PIXEL']

hdu0= fits.PrimaryHDU(data=None, header=header)
hdu1 = fits.ImageHDU(data, name='SCI')
hdu2 = fits.ImageHDU(dq, name='PIXELDQ')
hdulist = fits.HDUList([hdu0, hdu1, hdu2])
hdulist.writeto('test_image_ff.fits', overwrite=True)

# Subarray that can be read out with 1 or 4 subarrays
header['INSTRUME'] = 'NIRCAM'
header['DETECTOR'] = 'NRCALONG'
header['SUBARRAY'] = 'SUBGRISMSTRIPE64'
header['SUBSTRT1'] = 0
header['SUBSTRT2'] = 0
header['SUBSIZE1'] = 2048
header['SUBSIZE2'] = 64
header['TSAMPLE'] = 10
header['TFRAME'] = 1.3596

data = np.zeros((64, 2048))
dq = np.zeros((64, 2048)).astype(np.int)
dq[0:4, :] = dqflags.pixel['REFERENCE_PIXEL']
dq[:, 0:4] = dqflags.pixel['REFERENCE_PIXEL']
dq[:, 2044:] = dqflags.pixel['REFERENCE_PIXEL']

hdu0 = fits.PrimaryHDU(data=None, header=header)
hdu1 = fits.ImageHDU(data, name='SCI')
hdu2 = fits.ImageHDU(dq, name='PIXELDQ')
hdulist = fits.HDUList([hdu0, hdu1, hdu2])
hdulist.writeto('test_image_grismstripe_one_amp.fits', overwrite=True)

header['TFRAME'] = 0.3406
hdu0 = fits.PrimaryHDU(data=None, header=header)
hdu1 = fits.ImageHDU(data, name='SCI')
hdu2 = fits.ImageHDU(dq, name='PIXELDQ')
hdulist = fits.HDUList([hdu0, hdu1, hdu2])
hdulist.writeto('test_image_grismstripe_four_amp.fits', overwrite=True)


