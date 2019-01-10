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

from jwql.utils.utils import AMPLIFIER_BOUNDARIES


def amplifier_info(filename):
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
                                        sample_time, 4)
            amp1_time = calc_frame_time(instrument, aperture, x_dim, y_dim,
                                        sample_time, 1)
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
    return num_amps, amp_bounds


def calc_frame_time(instrument, aperture, xdim, ydim, sample_time, amps):
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

    sample_time : float
        Time to sample a pixel, in seconds. For NIRCam/NIRISS/FGS
        this is 10 microseconds = 1e-5 seconds

    amps : int
        Number of amplifiers used to read out the frame

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
