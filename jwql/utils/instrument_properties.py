"""Collection of functions dealing with retrieving/calculating various
instrument properties

Authors
-------

    - Bryan Hilbert

Uses
----
stuff
"""


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
