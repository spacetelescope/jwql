"""Collection of functions dealing with retrieving/calculating various
instrument properties

Authors
-------

    - Bryan Hilbert

Uses
----
stuff
"""
from astropy.io import fits
import numpy as np

from jwst.datamodels import dqflags

from jwql.utils.utils import AMPLIFIER_BOUNDARIES


def amplifier_info(filename, omit_reference_pixels=True):
    """Calculate the number of amplifiers used to collect the data in a
    given file using the array size and exposure time of a single frame
    (This is needed because there is no header keyword specifying
    how many amps were used.)
    """
    # First get necessary metadata
    header = fits.getheader(filename)
    instrument = header['INSTRUME'].lower()
    detector = header['DETECTOR']
    x0 = header['SUBSTRT1']
    y0 = header['SUBSTRT2']
    x_dim = header['SUBSIZE1']
    y_dim = header['SUBSIZE2']
    sample_time = header['TSAMPLE']
    frame_time = header['TFRAME']
    subarray_name = header['SUBARRAY']
    aperture = "{}_{}".format(detector, subarray_name)

    # Special cases: subarrays taken using all 4 amps
    four_amp_subarrays = ['WFSS128R', 'WFSS64R']

    # Full frame data will be 2048x2048 for all instruments
    if ((x_dim == 2048) and (y_dim == 2048)) or subarray_name in four_amp_subarrays:
        num_amps = 4
        amp_bounds = AMPLIFIER_BOUNDARIES[instrument]
    else:
        if subarray_name not in ['SUBGRISMSTRIPE64', 'SUBGRISMSTRIPE128', 'SUBGRISMSTRIPE256']:
            num_amps = 1
            amp_bounds = {'1': [(0, 0), (x_dim, y_dim)]}
        else:
            # These are the tougher cases. Subarrays that can be
            # used with multiple amp combinations

            # Compare the given frametime with the calculated frametimes
            # using 4 amps or 1 amp.

            # Right now this is used only for the NIRCam grism stripe
            # subarrays, so we don't need this to be a general case that
            # can handle any subarray orientation relative to any amp
            # orientation
            amp4_time = calc_frame_time(instrument, aperture, x_dim, y_dim,
                                        4, sample_time=sample_time)
            amp1_time = calc_frame_time(instrument, aperture, x_dim, y_dim,
                                        1, sample_time=sample_time)
            if amp4_time == frame_time:
                num_amps = 4
                # In this case, keep the full frame amp boundaries in
                # the x direction, and set  the boundaries in the y
                # direction equal to the hight of the subarray
                amp_bounds = AMPLIFIER_BOUNDARIES[instrument]
                for amp_num in ['1', '2', '3', '4']:
                    amp_bounds[amp_num][0][1] = y_dim
                    amp_bounds[amp_num][1][1] = y_dim
            elif amp1_time == frame_time:
                num_amps = 1
                amp_bounds = {'1': [(0, 0), (x_dim, y_dim)]}
            else:
                raise ValueError(("Unable to determine number of amps used for exposure. 4-amp frametime"
                                  "is {}. 1-amp frametime is {}. Reported frametime is {}.")
                                 .format(amp4_time, amp1_time, frame_time))

    if omit_reference_pixels:
        # If requested, ignore reference pixels by adjusting the indexes of
        # the amp boundaries.
        with fits.open(filename) as hdu:
            data_quality = hdu['DQ'].data

        # Reference pixels should be flagged in the DQ array with the
        # REFERENCE_PIXEL flag. Find the science pixels by looping for
        # pixels that don't have that bit set.
        scipix = np.where(data_quality & dqflags.pixel['REFERENCE_PIXEL'] == 0)
        xmin = np.min(scipix[0])
        ymin = np.min(scipix[1])
        xmax = np.max(scipix[0]) + 1
        ymax = np.max(scipix[1]) + 1

        # Adjust the minimum and maximum x and y values if they are within
        # the reference pixels
        print('BEFORE: ', amp_bounds)
        for key in amp_bounds:
            bounds = amp_bounds[key]
            prev_xmin, prev_ymin = bounds[0]
            prev_xmax, prev_ymax = bounds[1]
            print(prev_xmin, xmin)
            if prev_xmin < xmin:
                new_xmin = xmin
            else:
                new_xmin = prev_xmin
            if prev_ymin < ymin:
                new_ymin = ymin
            else:
                new_ymin = prev_ymin
            if prev_xmax > xmax:
                new_xmax = xmax
            else:
                new_xmax = prev_xmax
            if prev_ymax > ymax:
                new_ymax = ymax
            else:
                new_ymax = prev_ymax
            amp_bounds[key] = [(new_xmin, new_ymin), (new_xmax, new_ymax)]

        print("AFTER: ", amp_bounds)
    return num_amps, amp_bounds


def calc_frame_time(instrument, aperture, xdim, ydim, amps, sample_time=1.e-5):
    """Calculate the readout time for a single frame
    of a given size and number of amplifiers. Note that for
    NIRISS and FGS, the fast readout direction is opposite to
    that in NIRCam, so we switch xdim and ydim so that we can
    keep a single equation.

    Parameters:
    -----------
    instrument : str
        Name of the instrument being simulated

    aperture : str
        Name of aperture being simulated (e.g "NRCA1_FULL")
        Currently this is only used to check for the FGS
        ACQ1 aperture, which uses a unique value of colpad
        below.

    xdim : int
        Number of columns in the frame

    ydim : int
        Number of rows in the frame

    amps : int
        Number of amplifiers used to read out the frame

    sample_time : float
        Time to sample a pixel, in seconds. For NIRCam/NIRISS/FGS
        this is 10 microseconds = 1e-5 seconds

    Returns:
    --------
    frametime : float
        Readout time in seconds for the frame
    """
    instrument = instrument.lower()
    if instrument == "nircam":
        xs = xdim
        ys = ydim
        colpad = 12

        # Fullframe
        if amps == 4:
            rowpad = 1
            fullpad = 1
        else:
            # All subarrays
            rowpad = 2
            fullpad = 0
            if ((xdim <= 8) & (ydim <= 8)):
                # The smallest subarray
                rowpad = 3

    elif instrument == "niriss":
        xs = ydim
        ys = xdim
        colpad = 12

        # Fullframe
        if amps == 4:
            rowpad = 1
            fullpad = 1
        else:
            rowpad = 2
            fullpad = 0

    elif instrument == 'fgs':
        xs = ydim
        ys = xdim
        colpad = 6
        if 'acq1' in aperture.lower():
            colpad = 12
        rowpad = 1
        if amps == 4:
            fullpad = 1
        else:
            fullpad = 0

    return ((1.0 * xs / amps + colpad) * (ys + rowpad) + fullpad) * sample_time
