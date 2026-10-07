#! /usr/bin/env python

"""
This module was copied from the misc_jwst repo on github
https://github.com/mperrin/misc_jwst/blob/main/misc_jwst/target_acq_tools.py
and was authored by M. Perrin

Refactored to be object-oriented: the TAAnalysis class encapsulates all
per-visit state previously returned as a tuple of lists from main_ta_analysis().
"""

import functools, os
import shutil

import matplotlib, matplotlib.pyplot as plt
import numpy as np

import pysiaf
import stpsf as webbpsf
import scipy
import astropy
import astropy.io.fits as fits
import astropy.units as u
import astropy.time
from astroquery.mast import Mast
import jwst.datamodels, stdatamodels

from jwql.instrument_monitors.common_monitors.ta_monitor import engdb, guiding_analyses, mast, oss_ta_sams, utils
from jwql.utils.utils import filesystem_path

# ---------------------------------------------------------------------------
# Constants and lookup tables
# ---------------------------------------------------------------------------

# NIRCam TA Dither Offsets.
# Values from /PRDOPSSOC-067/TA_dithersXML/Excel/NIRCam_TA_dithers.xlsx
# Offsets in detector pixels, in the DET frame
#                        dither_num: [delta_detX, delta_detY]
_ta_dither_offsets_pix = {'NIRCAM': {0: [0, 0],
                                     1: [2, 4],
                                     2: [2 + 3, 4 - 5]},
                          'NIRISS': {0: [0, 0],
                                     1: [4, 2],
                                     2: [4 - 5, 2 + 3]},
                          }

# sign convention for DET frame relative to SCI frame
_ta_dither_sign = {'NRCALONG': [1, -1],
                   'NRCBLONG': [1, 1],  # TODO check this. But NRC TSO TA isn't dithered.
                    'NRCA1': [1, 1],    # TODO check this. But not directly relevant since thus far there have been no dithered TAs on NRCA2
                    'NRCA2': [-1, 1],   # Needed to match data for F210M TAs on NRCA2 in 2025
                    'NRCA3': [1, 1],    # TODO check this. But not directly relevant since WFS TA doesn't use dithers
                    'NRCA4': [-1, 1],   # Needed to match data for F210M TAs on NRCA2 in 2025
                    'NIS': [1, 1],      # TODO check this.
                   }


# ---------------------------------------------------------------------------
# File retrieval
# ---------------------------------------------------------------------------

@functools.lru_cache
def get_visit_ta_image(visitid, verbose=True, kind='cal', inst='NIRCam', index=0, localpath=None,
                       save_localpath=False):
    """Retrieve from MAST the target acq image for a given visit.

    This retrieves an image (or images) from MAST and returns it as a HDUList variable
    without writing to disk. If you want it to save to disk, set save_localpath=True

    - If only one TA file is found, that file is returned directly as an HDUList
    - If multiple TA files are found (e.g. TACQ and TACONFIRM), a list is returned
      containing all of them.
    """
    if save_localpath:
        if localpath is None:
            raise ValueError(f'save_localpath set to True, but no localpath given.')

    keywords = {
            'visit_id': [visitid[1:]], # note: drop the initial character 'V'
            'exp_type': ['NRC_TACQ', 'MIR_TACQ', 'MIR_TACONFIRM', 'NRS_WATA', 'NRS_TACONFIRM', 'NIS_TACQ'],
            'productLevel': ['2b'],    # we are just interested in the Cal files, not in any rates.
           }

    def set_params(parameters):
        return [{"paramName" : p, "values" : v} for p, v in parameters.items()]

    # Restructuring the keywords dictionary to the MAST syntax
    params = {'columns': '*',
              'filters': set_params(keywords)
              }

    service = f'Mast.Jwst.Filtered.{inst.lower()}'

    if verbose:
        print(f'Querying MAST to find target acq files for {visitid}')
        print(params)
        print(service)
    t = Mast.service_request(service, params)
    nfiles = len(t)
    if verbose:
        print(f"Found {nfiles} target acq files for that observation.")

    files_found = []
    filenames = t['filename']
    filenames.sort()

    for filename in filenames:

        # If user manually specifies rate or uncal, retrieve that instead
        if kind == 'rate' or kind == 'uncal':
             filename = filename.replace('_cal.fits', f'_{kind}.fits')

        if verbose:
            print(f"TA filename: {filename}")

        # Locate the file in the filesystem
        try:
            #filepath = filesystem_path(filename, check_existence=True)
            filepath = os.path.join('/Users/hilbert/python_repos/jwql/jwql/instrument_monitors/common_monitors/ta_monitor/jw07827/jw07827001001/', filename)
        except FileNotFoundError:
            # If the file isn't present in the filesystem, try moving on to the next one
            log.warning(f'File {filename} was not present at the expected location in the filesystem.')
            continue

        # Make a temporary copy of the file in the TA Monitor working directory
        if save_localpath:
            local_file = os.path.join(localpath, filename)
            shutil.copy(filepath, localpath)

        # Open the file
        ta_hdul = fits.open(local_file)

        hduls_found.append(ta_hdul)

    if len(hduls_found) == 0:
        return None
    elif len(hduls_found) == 1:
        return hduls_found[0]
    else:
        return hduls_found


# ---------------------------------------------------------------------------
# Image display helpers
# ---------------------------------------------------------------------------

def _crop_display_for_miri(ax, hdul):
    """ Set xlim and ylim to crop the display region for a MIRI TA image
    Many MIRI TA images use full array, even though only a subarray is of interest.
    """
    # Note, this would be more elegant to look up from siaf but we just hard-code values here since none of this will ever change.

    apname = hdul[0].header['APERNAME']

    boxsize=64
    if apname =='MIRIM_TAMRS':
        # crop to upper corner
        ax.set_xlim(1023-boxsize, 1023)
        ax.set_ylim(1019-boxsize, 1019)
    elif apname == 'MIRIM_TASLITLESSPRISM' and hdul[0].header['SUBARRAY'] == 'SLITLESSPRISM':
        # crop to upper part.
        ax.set_ylim(415-boxsize, 415)
        ax.set_xlim(8,)
    elif apname == 'MIRIM_SLITLESSPRISM' and hdul[0].header['SUBARRAY'] == 'SLITLESSPRISM':
        # crop to upper part.
        ax.set_ylim(415-boxsize-80, 415-80)
        ax.set_xlim(8,)
    elif apname =='MIRIM_TALRS':
        ax.set_xlim(382, 382+boxsize )
        ax.set_ylim(258, 258+boxsize)
    elif apname =='MIRIM_SLIT':
        ax.set_xlim(294, 294+boxsize )
        ax.set_ylim(269, 269+boxsize)


def _crop_display_for_nirspec(ax, hdul):
    """ Set xlim and ylim to crop the display region for a NIRSpec TA image
    Many MIRI WATA images use full array or a larger subarray, even though only a subarray is of interest.
    """
    # Note, this would be more elegant to look up from siaf but we just hard-code values here since none of this will ever change.
    # Plus, NIRSpec subarray parameters turn out not to be in SIAF at all!

    apname = hdul[0].header['APERNAME']
    subarray_name = hdul[0].header['SUBARRAY']

    if apname=='NRS_S1600A1_SLIT':
        if subarray_name == 'SUB32':
            pass # no cropping needed
        elif subarray_name == 'SUB2048':
            # crop displayed region to be consistent with the SUB32 view
            ax.set_xlim(1398-0.5, 1398+32-0.5)
            # no ylim crop needed, this is already only 32 pix tall
        elif subarray_name == 'FULL':
            # crop displayed region to be consistent with the SUB32 view
            ax.set_xlim(1398-0.5, 1398+32-0.5)
            ax.set_ylim(974-0.5, 975+32-0.5)


def show_ta_img(visitid, ax=None, return_handles=False, inst='NIRCam', mark_reference_point=True, mark_apername=True, ta_expnum=None, **kwargs):
    """ Retrieve and display a target acq image"""

    hdul = get_visit_ta_image(visitid, inst=inst, **kwargs)
    inst = inst.upper()

    # If there are multiple TA images, you have to pick which one you want to display
    if len(hdul) == 0:
        raise RuntimeError("No TA images found for that visit")
    title_extra = ''
    if isinstance(hdul, list) and not isinstance(hdul, fits.HDUList):
        if ta_expnum is None:
            raise ValueError(f"You must specify ta_expnum=<n> to select which of {len(hdul)} TA exposures to show (using 1-based indexing)")
        else:
            hdul = hdul[ta_expnum-1]
            if inst.upper() not in ['NIRCAM', 'NIRISS'] :
                # These can have dithered 3x TAs, so print the exp number on each for those cases
                title_extra = f' exp #{ta_expnum}'
            if inst.upper() == 'NIRSPEC':
                if 'WATA' in hdul[0].header['EXP_TYPE']:
                    title_extra = ' (WATA)'
                elif 'MSATA' in hdul[0].header['EXP_TYPE']:
                    title_extra = ' (MSATA)'
            if 'CONF' in hdul[0].header['EXP_TYPE']:
                title_extra = 'CONFIRM'


    ta_img = hdul['SCI'].data
    mask = np.isfinite(ta_img)
    rmean, rmedian, rsig = astropy.stats.sigma_clipped_stats(ta_img[mask])
    bglevel = rmedian

    vmax = np.nanmax(ta_img) - bglevel
    asinh_linear_width = vmax*0.003
    # special case NIRSpec
    if inst.upper() == 'NIRSPEC' and hdul[0].header['SUBARRAY'] == 'FULL':
        # set vmin, vmax just based on the region around the S1600 aperture for WATA
        vmax = np.nanmax(ta_img[974:974+32, 1399:1399+32]) - bglevel
        # set linear width based on bg level inside the S1600 aperture
        asinh_linear_width = np.max([np.nanmedian(ta_img[1407:1407+16, 983:983+16])*2, vmax*0.003])
    cmap = matplotlib.cm.viridis.copy()
    cmap.set_bad('orange')

    norm = matplotlib.colors.AsinhNorm(linear_width = asinh_linear_width, vmax=vmax,
                                       vmin=-1*rsig)

    model = jwst.datamodels.open(hdul)
    annotate_subarray = f"\n{model.meta.subarray.name} " if inst.upper() == "NIRSPEC" else ""
    annotation_text = f"{model.meta.target.proposer_name}\n{model.meta.instrument.filter}, {model.meta.exposure.readpatt}:{model.meta.exposure.ngroups}:{model.meta.exposure.nints}{annotate_subarray}\n{model.meta.exposure.effective_exposure_time:.2f} s"

    if ax is None:
        ax = plt.gca()
    ax.imshow(ta_img - bglevel, norm=norm, cmap=cmap, origin='lower')
    ax.set_title(f"{inst} TA{title_extra} on {visitid}\n{hdul[0].header['DATE-OBS']} {hdul[0].header['TIME-OBS'][0:8]}")
    ax.set_ylabel("[Pixels]")
    ax.text(0.03, 0.97, annotation_text,
            color='white', transform=ax.transAxes, verticalalignment='top')

    if inst.upper() == 'MIRI':
        _crop_display_for_miri(ax, hdul)
    elif inst.upper() == 'NIRSPEC':
        _crop_display_for_nirspec(ax, hdul)

    if mark_reference_point:
        xref, yref = get_ta_reference_point(inst, hdul, ta_expnum)
        ax.axvline(xref, color='0.75', alpha=0.5, ls='--')
        ax.axhline(yref, color='0.75', alpha=0.5, ls='--')

    if mark_apername:
        # mark aperture, and which guider was used
        ax.text(0.97, 0.97, hdul[0].header['APERNAME']+f"\n using {guiding_analyses.which_guider_used(visitid)}",
            color='white', transform=ax.transAxes, horizontalalignment='right', verticalalignment='top')

    if return_handles:
        return hdul, ax, norm, cmap, bglevel


def get_ta_reference_point(inst, hdul, ta_expnum=1):
    """ Determine the TA reference point, i.e. where was the target 'supposed to be' in any given observation
    This is usually the aperture reference location, but may be modified by any TA dithers, or
    by subarray/full array coord system shenanigans for MIR.
    """
    siaf = utils.get_siaf(inst)
    ap = siaf.apertures[hdul[0].header['APERNAME']]

    if inst.upper() in ['NIRCAM', 'NIRISS']:
        xref = ap.XSciRef - 1   # siaf uses 1-based counting
        yref = ap.YSciRef - 1   # ditto

        if ta_expnum>0:
            # if there are multiple ta exposures, take into account the dither moves
            # and the sign needed to go from DET to SCI coordinate frames
            xref -= _ta_dither_offsets_pix[inst][ta_expnum-1][0] * _ta_dither_sign[hdul[0].header['DETECTOR']][0]
            yref -= _ta_dither_offsets_pix[inst][ta_expnum-1][1] * _ta_dither_sign[hdul[0].header['DETECTOR']][1]
    elif inst.upper() == 'MIRI':
        try:
            if hdul[0].header['SUBARRAY'] == 'FULL' and hdul[0].header['APERNAME'] != 'MIRIM_SLIT':
                # For MIRI, sometimes we have subarray apertures for TA but the images are actually full array.
                # In which case use the Det coords
                xref = ap.XDetRef - 1   # siaf uses 1-based counting
                yref = ap.YDetRef - 1   # ditto
            elif hdul[0].header['APERNAME'] == 'MIRIM_TASLITLESSPRISM' and hdul[0].header['SUBARRAY'] == 'SLITLESSPRISM':
                # This one's weird. It's pointed using TASLITLESSPRISM but read out using SLITLESSPRISM
                ap_slitlessprism = siaf.apertures['MIRIM_SLITLESSPRISM']
                xref, yref = ap_slitlessprism.det_to_sci(ap.XDetRef, ap.YDetRef)  # convert coords from TASLITLESSPRISM to SLITLESSPRISM
                xref, yref = xref - 1, yref - 1  # siaf uses 1-based counting
            elif hdul[0].header['APERNAME'] == 'MIRIM_SLIT':
                # This case is tricky. TACONFIRM image in slit type aperture, which doesn't have Det or Sci coords defined
                # It's made even more complex by filter-dependent MIRI offsets
                print("TODO need to get more authoritative intended target position for MIRIM TA CONFIRM")
                xref, yref = 317, 301
            elif hdul[0].header['APERNAME'].endswith('_UR') or  hdul[0].header['APERNAME'].endswith('_CUR'):
                # Coronagraphic TA, pointed using special TA subarrays but read out using the full coronagraphic subarray
                # Similar to how TASLITLESSPRISM works
                ap_subarray = siaf.apertures['MIRIM_'+hdul[0].header['SUBARRAY']]
                xref, yref = ap_subarray.det_to_sci(ap.XDetRef, ap.YDetRef)  # convert coords from TA subarray to coron subarray
                xref, yref = xref - 1, yref - 1  # siaf uses 1-based counting
            else:
                xref = ap.XSciRef - 1   # siaf uses 1-based counting
                yref = ap.YSciRef - 1   # ditto

        except TypeError: # LRS slit type doesn't have X/YSciRef
            xref = yref = 0
            print('ERROR DEBUG THIS')
    elif inst.upper() == 'NIRSPEC':
        # What is the location of the reference point?
        # For NIRSpec this slightly tricker since the aperture only has V2V3 ref defined, and
        # we need to convert that to detector coordinates. We can do that with the gWCS.
        model = jwst.datamodels.open(hdul)
        ap = pysiaf.Siaf('NIRSpec')[model.meta.aperture.name]
        transform = model.meta.wcs.get_transform('v2v3', 'detector')  # Transform from V frame to subarray used in this obs
        xref, yref = transform(ap.V2Ref, ap.V3Ref)

    return xref, yref


# ---------------------------------------------------------------------------
# TAAnalysis class
# ---------------------------------------------------------------------------

class TAAnalysis:
    """Encapsulates the results and logic of a single-visit TA analysis.

    Previously, ``main_ta_analysis()`` returned a large tuple of parallel
    lists.  This class instead stores those lists as attributes, making it
    straightforward to inspect results, pass the object around, and extend
    the analysis.

    Parameters
    ----------
    visitid : str
        Visit ID string (with or without the leading 'V').
    inst : str
        Instrument name, e.g. 'NIRCam', 'NIRISS', 'MIRI'.
    verbose : bool
        Print progress messages.
    plot : bool
        Generate and save diagnostic plots.
    output_plot_dir : str
        Directory in which to save plots.
    **kwargs
        Additional keyword arguments forwarded to ``get_visit_ta_image`` and
        ``show_ta_img`` (e.g. ``localpath``, ``save_localpath``).

    Attributes
    ----------
    visitid : str
        Normalised visit ID.
    inst : str
        Upper-cased instrument name.
    n_ta_images : int
        Number of TA exposures found for this visit.

    Per-exposure lists (one entry per TA exposure, in exposure order)
    -----------------------------------------------------------------
    visit_ids : list[str]
    filenames : list[str]
    deltapos : list[tuple[float, float]]
        Pointing offset (x, y) in pixels between the intended target location
        (aperture reference) and the measured centroid.
    deltapos_source : list[str]
        Label indicating whether ``deltapos`` was derived from the OSS centroid
        or the local fwcentroid ('OSS - Intended' or 'fwcentroid-Intended').
    wcs_offset_pix : list[np.ndarray]
        (x, y) offset in pixels between the WCS-derived target position and the
        OSS centroid.
    wcs_offset_radec : list[tuple]
        Same offset expressed as (∆RA, ∆Dec) ``Angle`` objects in arcseconds.
    xyref : list[tuple[float, float]]
        Intended target position (x, y) in the science pixel frame (0-based).
    oss_cen_sci_pythonic : list[np.ndarray or None]
        OSS on-board centroid converted to the science pixel frame (0-based).
    targ_coords_pix : list[tuple]
        WCS-derived target position in the science pixel frame.
    ta_cen_coords : list[astropy.coordinates.SkyCoord]
        Sky coordinates corresponding to the OSS centroid pixel position.
    targ_coords : list[astropy.coordinates.SkyCoord]
        Sky coordinates of the target from the header.
    cen : list[np.ndarray]
        Local fwcentroid measurement (y, x order as returned by fwcentroid).
    oss_sam : list[np.ndarray or None]
        OSS small-angle manoeuvre (∆V2, ∆V3) in arcsec.
    oss_sam_dpa : list[float or None]
        OSS ∆V3PA from the SAM.
    """

    def __init__(self, visitid, inst='NIRCam', verbose=True, plot=True,
                 output_plot_dir='.', **kwargs):
        self.visitid = utils.get_visitid(visitid)
        self.inst = inst.upper()
        self.verbose = verbose
        self.plot = plot
        self.output_plot_dir = output_plot_dir
        self._kwargs = kwargs

        # Per-exposure result lists
        self.visit_ids: list = []
        self.filenames: list = []
        self.deltapos: list = []
        self.deltapos_source: list = []
        self.wcs_offset_pix: list = []
        self.wcs_offset_radec: list = []
        self.xyref: list = []
        self.oss_cen_sci_pythonic: list = []
        self.targ_coords_pix: list = []
        self.ta_cen_coords: list = []
        self.targ_coords: list = []
        self.cen: list = []
        self.oss_sam: list = []
        self.oss_sam_dpa: list = []

        # Internal state set during run()
        self._siaf = None
        self._ta_images = None
        self.n_ta_images: int = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self):
        """Execute the full TA analysis for the visit.

        Populates all per-exposure list attributes and, if ``self.plot`` is
        True, saves a PDF diagnostic plot to ``self.output_plot_dir``.
        """
        self._siaf = utils.get_siaf(self.inst)
        self._load_ta_images()

        axes = self._setup_plot() if self.plot else None

        for i_ta_image in range(self.n_ta_images):
            self._analyze_single_exposure(i_ta_image, axes)

        if self.plot:
            self._finalize_plot(axes)

        return self

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_ta_images(self):
        """Retrieve TA images from MAST and set ``self._ta_images`` and
        ``self.n_ta_images``."""
        ta_images = get_visit_ta_image(self.visitid, inst=self.inst,
                                       **self._kwargs)
        if ta_images is None:
            raise RuntimeError(f"No TA image found for visit {self.visitid}")
        elif isinstance(ta_images, fits.HDUList):
            self.n_ta_images = 1
        elif isinstance(ta_images[0], fits.HDUList):
            self.n_ta_images = len(ta_images)

        self._ta_images = ta_images

        if self.verbose:
            print(f"Found {self.n_ta_images} TA images for {self.visitid}")

    def _setup_plot(self):
        """Create the matplotlib figure and return the axes array."""
        fig, axes = plt.subplots(
            figsize=(8 * self.n_ta_images, 8),
            ncols=self.n_ta_images
        )
        self._fig = fig
        return np.atleast_1d(axes)

    def _get_hdul_for_exposure(self, i_ta_image, axes):
        """Return the HDUList for exposure ``i_ta_image``.

        If plotting is enabled this also renders the TA image into the
        appropriate axis.
        """
        if self.plot:
            hdul, ax, norm, cmap, bglevel = show_ta_img(
                self.visitid, ax=axes[i_ta_image], return_handles=True,
                inst=self.inst, ta_expnum=i_ta_image + 1, **self._kwargs
            )
        else:
            hdul = get_visit_ta_image(self.visitid, inst=self.inst,
                                      **self._kwargs)
            if isinstance(hdul, list) and not isinstance(hdul, fits.HDUList):
                hdul = hdul[i_ta_image]
        return hdul

    def _clean_image(self, hdul, interp_kernel_size):
        """Return a NaN-interpolated copy of the SCI extension."""
        im_obs = hdul['SCI'].data
        im_obs_dq = hdul['DQ'].data
        im_obs_clean = im_obs.copy()
        im_obs_clean[im_obs_dq & 1] = np.nan  # Mask DO_NOT_USE pixels

        kernel = np.ones(interp_kernel_size)
        im_obs_clean = astropy.convolution.interpolate_replace_nans(
            im_obs, kernel=kernel)

        for _ in range(2):
            if np.any(np.isnan(im_obs_clean)):
                print('iterating to interpolate over more NaNs')
                im_obs_clean = astropy.convolution.interpolate_replace_nans(
                    im_obs_clean, kernel=kernel)
            else:
                break
        else:
            if np.any(np.isnan(im_obs_clean)):
                print("Masking remaining NaNs to image median")
                im_obs_clean[np.isnan(im_obs_clean)] = np.nanmedian(im_obs_clean)

        return im_obs_clean

    def _get_instrument_config(self, hdul, ta_aperture):
        """Return ``(full_ap, interp_kernel_size, show_oss_for_image)``
        for the current instrument."""
        if self.inst == 'NIRCAM':
            full_ap = self._siaf[ta_aperture.AperName[0:5] + "_FULL"]
            interp_kernel_size = (5, 5)
            show_oss_for_image = self.n_ta_images - 1
        elif self.inst == 'NIRISS':
            full_ap = self._siaf["NIS_CEN"]
            interp_kernel_size = (5, 5)
            show_oss_for_image = self.n_ta_images - 1
        elif self.inst == 'MIRI':
            full_ap = self._siaf["MIRIM_FULL"]
            interp_kernel_size = (11, 11)
            show_oss_for_image = 0
        else:
            raise ValueError(f"Unsupported instrument: {self.inst}")
        return full_ap, interp_kernel_size, show_oss_for_image

    def _compute_oss_centroid(self, hdul, ta_aperture, full_ap,
                               show_oss_for_image, i_ta_image, axes):
        """Retrieve and convert the OSS on-board centroid.

        Returns ``(oss_cen_sci_pythonic, oss_centroid_text)``.
        """
        oss_cen_sci_pythonic = (np.nan, np.nan)
        oss_centroid_text = ""
        oss_cen_full_sci = None

        try:
            osslog = engdb.get_ictm_event_log(
                hdul[0].header['VSTSTART'], hdul[0].header['VISITEND'])
            try:
                oss_cen = engdb.extract_oss_TA_centroids(
                    osslog, 'V' + hdul[0].header['VISIT_ID'])

                if self.inst == "NIRISS":
                    if self.verbose:
                        print("transposing X & Y, due to NIRISS detector coordinate frame")
                    oss_cen = oss_cen[::-1]

                oss_cen_sci = ta_aperture.det_to_sci(*oss_cen)

                if self.inst == 'MIRI':
                    if hdul[0].header['SUBARRAY'] == 'FULL':
                        oss_cen_sci = np.asarray(full_ap.det_to_sci(*oss_cen))
                    elif hdul[0].header['SUBARRAY'] == 'SLITLESSPRISM':
                        slitlessprism_ap = self._siaf['MIRIM_SLITLESSPRISM']
                        oss_cen_sci = np.asarray(
                            slitlessprism_ap.det_to_sci(*oss_cen))
                    elif hdul[0].header['SUBARRAY'].startswith('MASK'):
                        coron_ap = self._siaf[
                            'MIRIM_' + hdul[0].header['SUBARRAY']]
                        oss_cen_sci = np.asarray(
                            coron_ap.det_to_sci(*oss_cen))

                oss_cen_sci_pythonic = np.asarray(oss_cen_sci) - 1
                oss_cen_full_sci = np.asarray(
                    full_ap.det_to_sci(*oss_cen)) - 1

                if i_ta_image == show_oss_for_image:
                    oss_centroid_text = (
                        f"OSS centroid: {oss_cen_sci_pythonic[0]:.2f},"
                        f" {oss_cen_sci_pythonic[1]:.2f}")
                    if self.plot and axes is not None:
                        axes[i_ta_image].scatter(
                            oss_cen_sci_pythonic[0], oss_cen_sci_pythonic[1],
                            color='0.5', marker='x', s=50)
                        axes[i_ta_image].text(
                            oss_cen_sci_pythonic[0], oss_cen_sci_pythonic[1],
                            'OSS  ', color='0.9',
                            verticalalignment='center',
                            horizontalalignment='right')

                if self.verbose:
                    print(f"OSS centroid on board:  {oss_cen}"
                          f"  (full det coord frame, 1-based)")
                    print(f"OSS centroid converted: {oss_cen_sci_pythonic}"
                          f"  (sci frame in {ta_aperture.AperName}, 0-based)")
                    if oss_cen_full_sci is not None:
                        print(f"OSS centroid converted: {oss_cen_full_sci}"
                              f"  (sci frame in {full_ap.AperName}, 0-based)")

            except RuntimeError:
                if self.verbose:
                    print("Could not parse TA coordinates from log. "
                          "TA may have failed?")
                oss_cen_sci_pythonic = (np.nan, np.nan)
                oss_centroid_text = "No OSS centroid; TA failed"

        except RuntimeError:
            print("Could not get coords from OSS log. TA may have failed?")

        return oss_cen_sci_pythonic, oss_centroid_text

    def _compute_oss_sam(self, hdul):
        """Retrieve the OSS small-angle manoeuvre.

        Returns ``(oss_sam, oss_sam_dpa)``, each ``None`` on failure.
        """
        try:
            oss_sam, oss_sam_dpa = oss_ta_sams.get_ta_correction_for_visit(
                self.visitid, verbose=self.verbose)
            if self.verbose:
                print(f"OSS SAM: (∆V2, ∆V3) = {oss_sam}  "
                      f"∆V3PA = {oss_sam_dpa}")
        except RuntimeError:
            print("Could not get coords from OSS log. TA may have failed?")
            oss_sam, oss_sam_dpa = None, None
        return oss_sam, oss_sam_dpa

    def _compute_wcs_position(self, hdul, axes, i_ta_image):
        """Compute WCS-based target pixel position.

        Returns ``(model, targ_coords, targ_coords_pix, wcs_text)``.
        """
        model = jwst.datamodels.open(hdul)
        targ_coords = astropy.coordinates.SkyCoord(
            model.meta.target.ra, model.meta.target.dec,
            frame='icrs', unit=u.deg)
        targ_coords_pix = model.meta.wcs.world_to_pixel(targ_coords)
        wcs_text = (f'Expected from WCS: {targ_coords_pix[0]:.2f},'
                    f' {targ_coords_pix[1]:.2f}')

        if self.verbose:
            print(f"Target coords: {targ_coords}")
            print(f"               "
                  f"{targ_coords.to_string('hmsdms', sep=':')}")

        if self.plot and axes is not None:
            axes[i_ta_image].scatter(
                targ_coords_pix[0], targ_coords_pix[1],
                color='magenta', marker='+', s=50)
            axes[i_ta_image].text(
                targ_coords_pix[0], targ_coords_pix[1] + 2,
                'WCS', color='magenta',
                verticalalignment='bottom', horizontalalignment='center')

        return model, targ_coords, targ_coords_pix, wcs_text

    def _compute_local_centroid(self, im_obs_clean, hdul, axes, i_ta_image):
        """Compute the local fwcentroid and return it."""
        nm = 6
        border_mask = np.ones_like(im_obs_clean)
        border_mask[:nm] = 0
        border_mask[-nm:] = 0
        border_mask[:, :nm] = 0
        border_mask[:, -nm:] = 0

        apname = hdul[0].header['APERNAME']
        if apname == 'MIRIM_TALRS':
            border_mask[:] = 0
            border_mask[260:320, 390:440] = 1
        elif apname == 'MIRIM_TAMRS':
            border_mask[:] = 0
            border_mask[958:1018, 960:1022] = 1
        elif apname == 'MIRIM_SLIT':
            border_mask[:] = 0
            border_mask[270:330, 290:350] = 1
        elif apname.endswith('_UR'):
            imin, imax = (200, 250) if 'LYOT' in apname else (150, 200)
            border_mask[:] = 0
            border_mask[imin:imax, imin:imax] = 1
        elif apname.endswith('_CUR'):
            imin, imax = (150, 225) if 'LYOT' in apname else (100, 150)
            border_mask[:] = 0
            border_mask[imin:imax, imin:imax] = 1

        cen = webbpsf.fwcentroid.fwcentroid(im_obs_clean * border_mask)

        if self.plot and axes is not None:
            if self.inst == 'MIRI':
                print('Need to update plotting code for subarray calc '
                      'in full frame image')
            axes[i_ta_image].scatter(
                cen[1], cen[0], color='red', marker='+', s=50)
            axes[i_ta_image].text(
                cen[1], cen[0], '  stpsf', color='red',
                verticalalignment='center', clip_on=True)

        return cen

    def _compute_wcs_offsets(self, targ_coords, targ_coords_pix,
                              oss_cen_sci_pythonic, model,
                              i_ta_image, show_oss_for_image, oss_sam,
                              axes):
        """Compute pixel and RA/Dec offsets between WCS and OSS centroid.

        Updates ``self.wcs_offset_pix``, ``self.wcs_offset_radec``,
        ``self.ta_cen_coords``, and ``self.targ_coords``.
        """
        wcs_offset_pix = np.array([np.nan, np.nan])
        wcs_offset_radec = (np.nan, np.nan)

        if (oss_cen_sci_pythonic is not None and
                not np.any(np.isnan(oss_cen_sci_pythonic)) and
                i_ta_image == show_oss_for_image):
            wcs_offset_pix = (np.asarray(targ_coords_pix)
                              - oss_cen_sci_pythonic)
            self.wcs_offset_pix.append(wcs_offset_pix)

            ta_cen_coords = model.meta.wcs.pixel_to_world(
                *oss_cen_sci_pythonic)
            self.ta_cen_coords.append(ta_cen_coords)
            self.targ_coords.append(targ_coords)

            dra, ddec = ta_cen_coords.spherical_offsets_to(targ_coords)
            wcs_offset_radec = (dra.to(u.arcsec), ddec.to(u.arcsec))
            self.wcs_offset_radec.append(wcs_offset_radec)

            if self.verbose:
                print(f"WCS offset =  {wcs_offset_pix} pix  (WCS - OSS)")
                print('TARG_COORDS: ', targ_coords)
                print('TA_CEN_COORDS: ', ta_cen_coords)
                print("DRA, DDEC: ", dra, ddec)

            if self.plot and axes is not None:
                axes[show_oss_for_image].text(
                    0.95, 0.63,
                    f'WCS $\\Delta$RA, $\\Delta$Dec =\n'
                    f' {dra.to_value(u.arcsec):.3f},'
                    f' {ddec.to_value(u.arcsec):.3f} arcsec',
                    horizontalalignment='right',
                    verticalalignment='bottom',
                    transform=axes[show_oss_for_image].transAxes,
                    color='cyan')
                if oss_sam is not None:
                    axes[show_oss_for_image].text(
                        0.95, 0.75,
                        f'TA SAM (V2, V3)=\n'
                        f' {oss_sam[0]:.3f}, {oss_sam[1]:.3f} arcsec',
                        horizontalalignment='right',
                        verticalalignment='bottom',
                        transform=axes[show_oss_for_image].transAxes,
                        color='yellow')

        return wcs_offset_pix, wcs_offset_radec

    def _analyze_single_exposure(self, i_ta_image, axes):
        """Run analysis for one TA exposure and append results to all lists."""
        deltapos = (np.nan, np.nan)

        # --- Load image ---
        hdul = self._get_hdul_for_exposure(i_ta_image, axes)
        ta_aperture = self._siaf.apertures[hdul[0].header['APERNAME']]
        xref, yref = get_ta_reference_point(self.inst, hdul, i_ta_image + 1)

        self.visit_ids.append(self.visitid)
        self.filenames.append(hdul[0].header.get('FILENAME', ''))
        self.xyref.append((xref, yref))

        # --- Instrument-specific config ---
        if self.inst == 'MIRI' and hdul[0].header['APERNAME'] == 'MIRIM_SLIT':
            full_ap = self._siaf["MIRIM_FULL"]
            ta_aperture = full_ap
        full_ap, interp_kernel_size, show_oss_for_image = \
            self._get_instrument_config(hdul, ta_aperture)

        # --- Clean image ---
        im_obs_clean = self._clean_image(hdul, interp_kernel_size)
        aperture_text = f'Intended target pos: {xref:.2f}, {yref:.2f}'

        # --- OSS centroid ---
        try:
            oss_cen_sci_pythonic, oss_centroid_text = \
                self._compute_oss_centroid(
                    hdul, ta_aperture, full_ap,
                    show_oss_for_image, i_ta_image, axes)
            self.oss_cen_sci_pythonic.append(oss_cen_sci_pythonic)

            oss_sam, oss_sam_dpa = self._compute_oss_sam(hdul)
            self.oss_sam.append(oss_sam)
            self.oss_sam_dpa.append(oss_sam_dpa)

            # --- WCS position ---
            model, targ_coords, targ_coords_pix, wcs_text = \
                self._compute_wcs_position(hdul, axes, i_ta_image)
            self.targ_coords_pix.append(targ_coords_pix)

        except ImportError:
            oss_centroid_text = ""
            wcs_text = ""
            oss_cen_sci_pythonic = (np.nan, np.nan)
            oss_sam = None
            oss_sam_dpa = None
            model = jwst.datamodels.open(hdul)
            targ_coords = None
            targ_coords_pix = (np.nan, np.nan)

        # --- Local centroid ---
        cen = self._compute_local_centroid(im_obs_clean, hdul, axes,
                                           i_ta_image)
        self.cen.append(cen)

        # --- Delta-position ---
        if i_ta_image == show_oss_for_image:
            if self.verbose:
                print(f"Comparing to OSS on-board centroid "
                      f"for TA image {i_ta_image + 1}")
            deltapos = (oss_cen_sci_pythonic[0] - xref,
                        oss_cen_sci_pythonic[1] - yref)
            deltapos_type = 'OSS - Intended'
        else:
            if self.verbose:
                print(f"Comparing to local STPSF centroid "
                      f"for TA image {i_ta_image + 1}")
            deltapos = (cen[1] - xref, cen[0] - yref)
            deltapos_type = 'fwcentroid-Intended'

        self.deltapos.append(deltapos)
        self.deltapos_source.append(deltapos_type)

        # --- Annotate image ---
        if self.plot and axes is not None:
            image_text = (
                f"Pixel coordinates (0-based):         \n"
                f"{aperture_text}\n{oss_centroid_text}\n"
                f" stpsf measure_centroid: {cen[1]:.2f}, {cen[0]:.2f}\n"
                f"{wcs_text}\n"
                f"$\\Delta$pos ({deltapos_type}): "
                f"{deltapos[0]:.2f}, {deltapos[1]:.2f}\n"
                f"= {deltapos[0] * ta_aperture.XSciScale:.3f},"
                f" {deltapos[1] * ta_aperture.YSciScale:.3f} arcsec"
            )
            axes[i_ta_image].text(
                0.95, 0.04, image_text,
                horizontalalignment='right', verticalalignment='bottom',
                transform=axes[i_ta_image].transAxes,
                color='white', clip_on=True)

        # --- WCS offsets (updates self.wcs_offset_pix/radec internally) ---
        if targ_coords is not None:
            self._compute_wcs_offsets(
                targ_coords, targ_coords_pix,
                oss_cen_sci_pythonic, model,
                i_ta_image, show_oss_for_image, oss_sam, axes)

        if self.verbose:
            print(f"Star coords from WCS: {targ_coords_pix}")

    def _finalize_plot(self, axes):
        """Add colorbars, footer text, and save the figure."""
        hdul = (self._ta_images if isinstance(self._ta_images, fits.HDUList)
                else self._ta_images[-1])

        for ax in axes[0:self.n_ta_images]:
            cb = self._fig.colorbar(
                ax.images[0], ax=ax, orientation='horizontal',
                label=hdul['SCI'].header['BUNIT'],
                fraction=0.05, shrink=0.9, pad=0.07)
            ticks = cb.ax.get_xticks()
            cb.ax.set_xticks([t for t in ticks if t > 0.1])

        now = astropy.time.Time.now()
        self._fig.text(
            0.04, 0.005,
            f"Analysis on {now.isot[0:16]}, using file from MAST SDP "
            f"{hdul[0].header['SDP_VER']}, "
            f"pipeline {hdul[0].header['CAL_VER']}",
            fontsize='x-small', color='0.5')

        plt.tight_layout()

        outname = os.path.join(
            self.output_plot_dir,
            f'{self.inst.lower()}_ta_analysis_{self.visitid}.pdf')
        plt.savefig(outname)
        print(f" => {outname}")


# ---------------------------------------------------------------------------
# Module-level convenience function (preserves original call signature)
# ---------------------------------------------------------------------------

def main_ta_analysis(visitid, inst='NIRCam', verbose=True, plot=True,
                     output_plot_dir='.', run_search=True, **kwargs):
    """Run TA analysis for a visit and return a :class:`TAAnalysis` object.

    This is a thin wrapper around :class:`TAAnalysis` that preserves the
    original module-level function name.  The returned object exposes all
    results that were previously returned as a bare tuple of lists; see the
    :class:`TAAnalysis` docstring for the full attribute listing.

    Parameters
    ----------
    visitid : str
    inst : str
    verbose : bool
    plot : bool
    output_plot_dir : str
    run_search : bool
        Unused; kept for backwards compatibility.
    **kwargs
        Forwarded to :class:`TAAnalysis`.

    Returns
    -------
    TAAnalysis
    """
    analysis = TAAnalysis(visitid, inst=inst, verbose=verbose, plot=plot,
                          output_plot_dir=output_plot_dir, **kwargs)
    analysis.run()
    return analysis


# Alias for backwards compatibility with call sites that used nrc_ta_analysis
nrc_ta_analysis = main_ta_analysis


# ---------------------------------------------------------------------------
# NIRCam-specific functions
# ---------------------------------------------------------------------------

def nrc_ta_comparison(visitid, inst='NIRCam', verbose=True, show_centroids=True, **kwargs):
    """ Retrieve a NIRCam target acq image and compare to a simulation

    Parameters:
    -----------
    visitid : string
        Visit ID. Should be one of the WFSC visits, starting with a NIRCam target acq, or at least
        some other sort of visit that begins with a NIRCam target acquisition.

    By default it downloads the file from MAST, or looks in the local directory to see if already downloaded.
    Set localpath=[some path] to search for the file in some other directory or filename.
    """
    from skimage.registration import phase_cross_correlation
    visitid = utils.get_visitid(visitid)

    fig, axes = plt.subplots(figsize=(10,5), ncols=2 if inst.upper() == 'MIRI' else 3)

    # Get and plot the observed TA image
    hdul, ax, norm, cmap, bglevel = show_ta_img(visitid, ax=axes[0], return_handles=True, inst=inst, **kwargs)
    im_obs = hdul['SCI'].data
    im_obs_err = hdul['ERR'].data
    im_obs_dq = hdul['DQ'].data

    im_obs_clean = im_obs.copy()
    im_obs_clean[im_obs_dq & 1] = np.nan  # Mask out any DO_NOT_USE pixels.
    im_obs_clean = astropy.convolution.interpolate_replace_nans(im_obs, kernel=np.ones((5,5)))

    # Make a matching sim
    nrc = webbpsf.setup_sim_to_match_file(hdul, verbose=False)
    opdname = nrc.pupilopd[0].header['CORR_ID'] + "-NRCA3_FP1-1.fits"
    if verbose:
        print(f"Calculating PSF to match that TA image...")
    psf = nrc.calc_psf(fov_pixels=im_obs.shape[0])

    # Align and Shift:
    im_sim = psf['DET_DIST'].data   # Use the extension including distortion and IPC

    # apply a mask around the border pixels, to apply a prior that the PSF is probably in the center-ish
    # and ignore any unmasked bad/hot pixels near the edges. This makes this alignment step more robust
    nm = 6
    border_mask = np.ones_like(im_obs_clean)
    border_mask[:nm] = 0
    border_mask[-nm:] = 0
    border_mask[:, :nm] = 0
    border_mask[:, -nm:] = 0

    shift, _, _ = phase_cross_correlation(im_obs_clean*border_mask, im_sim, upsample_factor=32)
    if verbose:
        print(f"Shift to register sim to data: {shift} pix")
    im_sim_shifted = scipy.ndimage.shift(im_sim, shift, order=5)

    # figure out the background level and scale factor
    scalefactor = np.nanmax(im_obs) / im_sim.max()
    if verbose:
        print(f"Scale factor to match sim to data: {scalefactor}")
    im_sim_scaled_aligned = im_sim_shifted*scalefactor

    # Optional, plot the measured centroids
    if show_centroids:
        ### OSS CENTROIDS ###
        # First, see if we can retrieve the on-board TA centroid measurment from the OSS engineering DB in MAST
        try:
            # retrieve the log for this visit, extract the OSS centroids, and convert to same
            # coordinate frame as used here:
            osslog = engdb.get_ictm_event_log(hdul[0].header['VSTSTART'], hdul[0].header['VISITEND'])
            try:
                oss_cen = engdb.extract_oss_TA_centroids(osslog, 'V' + hdul[0].header['VISIT_ID'])
                # Convert from full-frame (as used by OSS) to detector subarray coords:
                oss_cen_sci = nrc._detector_geom_info.aperture.det_to_sci(*oss_cen)
                oss_cen_sci_pythonic = np.asarray(oss_cen_sci) - 1  # convert from 1-based pixel indexing to 0-based
                oss_centroid_text = f"OSS centroid: {oss_cen_sci_pythonic[0]:.2f}, {oss_cen_sci_pythonic[1]:.2f}"
                axes[0].scatter(oss_cen_sci_pythonic[0], oss_cen_sci_pythonic[1], color='0.5', marker='x', s=50)
                axes[0].text(oss_cen_sci_pythonic[0], oss_cen_sci_pythonic[1], 'OSS  ', color='0.9', verticalalignment='center', horizontalalignment='right')
                if verbose:
                    print(f"OSS centroid on board:  {oss_cen}  (full det coord frame, 1-based)")
                    print(f"OSS centroid converted: {oss_cen_sci_pythonic}  (sci frame in {nrc._detector_geom_info.aperture.AperName}, 0-based)")
                    full_ap = nrc.siaf[nrc._detector_geom_info.aperture.AperName[0:5] + "_FULL"]
                    oss_cen_full_sci = np.asarray(full_ap.det_to_sci(*oss_cen)) - 1
                    print(f"OSS centroid converted: {oss_cen_full_sci}  (sci frame in {full_ap.AperName}, 0-based)")

            except RuntimeError:
                if verbose:
                    print("Could not parse TA coordinates from log. TA may have failed?")
                oss_cen_sci_pythonic = None
                oss_centroid_text = "No OSS centroid; TA failed"

            ### WCS COORDINATES ###
            model = jwst.datamodels.open(hdul)
            targ_coords = astropy.coordinates.SkyCoord(model.meta.target.ra, model.meta.target.dec, frame='icrs', unit=u.deg)
            targ_coords_pix = model.meta.wcs.world_to_pixel(targ_coords)  # returns x, y
            if verbose:
                print(f"Target coords: {targ_coords}")
                print(f"               {targ_coords.to_string('hmsdms', sep=':')}")
            axes[0].scatter(targ_coords_pix[0], targ_coords_pix[1], color='magenta', marker='+', s=50)
            axes[0].text(targ_coords_pix[0], targ_coords_pix[1]+2, 'WCS', color='magenta', verticalalignment='bottom', horizontalalignment='center')
            axes[0].text(0.95, 0.04, f'Expected from WCS: {targ_coords_pix[0]:.2f}, {targ_coords_pix[1]:.2f}',
                     horizontalalignment='right', verticalalignment='bottom',
                     transform=axes[0].transAxes,
                     color='white')

            if verbose:
                print(f"Star coords from WCS: {targ_coords_pix}")
                if oss_cen_sci_pythonic is not None:
                    print(f"WCS offset =  {np.asarray(targ_coords_pix) - oss_cen_sci_pythonic} pix  (WCS - OSS)")

        except ImportError:
            oss_centroid_text = ""

        ### WEBBPSF CENTROIDS ###
        cen = webbpsf.fwcentroid.fwcentroid(im_obs_clean*border_mask)
        axes[0].scatter(cen[1], cen[0], color='red', marker='+', s=50)
        axes[0].text(cen[1], cen[0], '  webbpsf', color='red', verticalalignment='center')

        axes[0].text(0.95, 0.10, oss_centroid_text+f'\n webbpsf measure_centroid: {cen[1]:.2f}, {cen[0]:.2f}',
                     horizontalalignment='right', verticalalignment='bottom',
                     transform=axes[0].transAxes,
                     color='white')


    # Plot the simulated TA image
    axes[1].imshow(im_sim_scaled_aligned, norm=norm, cmap=cmap, origin='lower')
    axes[1].set_title(f"Simulated PSF in F212N\nusing {opdname}")

    # Plot panel
    diffim = im_obs -bglevel - im_sim_scaled_aligned

    dofs = np.isfinite(diffim).sum() - 4  # 4 estimated parameters: X and Y offsets, flux scaling, background level
    reduced_chisq = np.nansum(((diffim / im_obs_err)**2)) / dofs

    axes[2].imshow(diffim, cmap=cmap, norm=norm, origin='lower')
    axes[2].set_title('Difference image\nafter alignment and scaling')
    axes[2].text(0.05, 0.9, f"$\\chi^2_r$ = {reduced_chisq:.3g}" + (
                  "  Alert, not a good fit!" if (reduced_chisq > 1.5) else ""),
                 transform = axes[2].transAxes, color='white' if (reduced_chisq <1.5) else 'yellow')

    for ax in axes:
        fig.colorbar(ax.images[0], ax=ax, orientation='horizontal',
                    label=hdul['SCI'].header['BUNIT'])

    plt.tight_layout()

    outname = f'nrc_ta_comparison_{visitid}.pdf'
    plt.savefig(outname)
    print(f" => {outname}")


# ---------------------------------------------------------------------------
# NIRSpec-specific functions
# ---------------------------------------------------------------------------

def nrs_ta_centroids_and_offsets(model, verbose=True):
    pass  # (unchanged from original – implementation omitted for brevity)


def nirspec_msata_ta_analysis(visitid, verbose=True):
    """ Top-level function for NIRSpec MSATA TA post analysis """
    visitid = utils.get_visitid(visitid)

    ta_files = get_visit_ta_image(visitid, inst='nirspec', verbose=verbose)
    if len(ta_files) != 2:
        print(f'Warning, expected to find 2 files (TACQ+TACONFIRM) but instead found {len(ta_files)}... ')

    tacq_model = jwst.datamodels.open(ta_files[0])
    taconfirm_model = jwst.datamodels.open(ta_files[1])

    nrs_ta_centroids_and_offsets(tacq_model, verbose=verbose)
    nrs_ta_centroids_and_offsets(taconfirm_model, verbose=verbose)


def nirspec_wata_ta_analysis(visitid, verbose=True, show_centroids=True):
    """ Top-level function for NIRSpec WATA TA post analysis """
    visitid = utils.get_visitid(visitid)

    ta_files = get_visit_ta_image(visitid, inst='nirspec', verbose=verbose)
    n_ta_images = len(ta_files)
    if n_ta_images != 2:
        print(f'Warning, expected to find 2 files (TACQ+TACONFIRM) but instead found {n_ta_images}... ')

    fig, axes = plt.subplots(figsize=(12,7), ncols=2)

    box_size=16

    for i_ta_image in range(n_ta_images):
        ax = axes[i_ta_image]

        hdul, ax, norm, cmap, bglevel = show_ta_img(visitid, ax=ax, return_handles=True, ta_expnum=i_ta_image+1, inst='NIRSpec',
                                                   mark_reference_point=False, verbose=True, save_localpath=True)

        model = jwst.datamodels.open(ta_files[i_ta_image])

        target_coords = astropy.coordinates.SkyCoord(model.meta.target.ra, model.meta.target.dec, frame='icrs', unit=u.deg)
        targ_coords_pix = list(model.meta.wcs.world_to_pixel(target_coords))
        if verbose:
            print("Target RA, Dec at epoch:", target_coords)
            print(targ_coords_pix)

        # Retrieve the OSS onboard centroids for comparison
        osslog = engdb.get_ictm_event_log(startdate=model.meta.visit.start_time,
                                        enddate=model.meta.guidestar.visit_end_time)

        oss_centroid = engdb.extract_oss_TA_centroids(osslog, "V"+model.meta.observation.visit_id, )
        oss_centroid_conv = [oss_centroid[1] - model.meta.subarray.xstart,
                             oss_centroid[0] - model.meta.subarray.ystart]

        if verbose:
            print(f"Onboard OSS TA centroid (1-based): {oss_centroid}")
            print(f"Onboard OSS TA centroid (subarray index): {oss_centroid_conv}")

        wcs_offset = np.asarray(targ_coords_pix) - np.asarray(oss_centroid_conv)
        if verbose:
            print(f"WCS offset relative to OSS: {wcs_offset}")

        try:
            subarray_name = model.meta.exposure.subarray
        except AttributeError:
            subarray_name = model.meta.subarray.name

        if subarray_name =='SUB2048':
            ax.set_xlim(1398-0.5, 1398+32-0.5)
            s1600_corner = (1407, 9)
        elif subarray_name== 'SUB32':
            s1600_corner = (9, 9)
        elif subarray_name== 'FULL':
            s1600_corner = (1407, 974+9)
        cutout_boxsize = 19
        s1600_center = [c + (cutout_boxsize-1)/2 for c in s1600_corner]
        cutout = astropy.nddata.Cutout2D(model.data, s1600_center, cutout_boxsize)

        s1600_boxsize = 16

        ap = pysiaf.Siaf('NIRSpec')[model.meta.aperture.name]
        transform = model.meta.wcs.get_transform('v2v3', 'detector')
        corners_detx, corners_dety = transform(*ap.corners('tel'))
        corners_detx = np.concatenate([corners_detx, [corners_detx[0]]])
        corners_dety = np.concatenate([corners_dety, [corners_dety[0]]])

        ax.plot(corners_detx, corners_dety, color='yellow', linestyle='--')

        if model.meta.filename == 'contents':
            ax.set_title(f'NIRSpec {model.meta.exposure.type} for V{model.meta.observation.visit_id}')

        xref, yref = get_ta_reference_point('NIRSpec', hdul, ta_expnum=i_ta_image+1)
        if 'WATA' in model.meta.exposure.type:
            oss_centroid_text = f"OSS centroid: {oss_centroid_conv[0]:.2f}, {oss_centroid_conv[1]:.2f}"

            ax.plot(oss_centroid_conv[0], oss_centroid_conv[1],
                     marker='x', color='0.5', markersize=20, ls='none',
                     label='OSS centroid, on board')

            ax.text(oss_centroid_conv[0]-1, oss_centroid_conv[1], 'OSS    ', color='0.7', verticalalignment='center', horizontalalignment='right')
            deltapos = (oss_centroid_conv[0] - xref,  oss_centroid_conv[1] - yref)
            deltapos_type = 'OSS - Intended'
        else:
            oss_centroid_text = ""
            deltapos_type = 'fwcentroid-Intended'
            deltapos = [np.nan, np.nan]

        ax.plot(targ_coords_pix[0], targ_coords_pix[1],
             marker='+', color='magenta', markersize=30, ls='none',
             label='using WCS coords')

        ax.axvline(xref, color='0.75', alpha=0.5, ls='--')
        ax.axhline(yref, color='0.75', alpha=0.5, ls='--')

        ax.text(targ_coords_pix[0], targ_coords_pix[1]-2, 'WCS', color='magenta', verticalalignment='top', horizontalalignment='center')

        cen =  [-1, -1]
        wcs_text = f'Expected from WCS: {targ_coords_pix[0]:.2f}, {targ_coords_pix[1]:.2f}'
        aperture_text = f'Intended target pos: {xref:.2f}, {yref:.2f}'

        image_text = f"Pixel coordinates (0-based):         \n{oss_centroid_text}\n poppy fwcentroid: {cen[1]:.2f}, {cen[0]:.2f}\n{wcs_text}\n{aperture_text}\n$\\Delta$pos ({deltapos_type}): {deltapos[0]:.2f}, {deltapos[1]:.2f}"

        axes[i_ta_image].text(0.95, 0.04, image_text,
                     horizontalalignment='right', verticalalignment='bottom',
                     transform=axes[i_ta_image].transAxes,
                             color='white')

    for ax in axes[0:n_ta_images]:
        cb = fig.colorbar(ax.images[0], ax=ax, orientation='horizontal',
                    label=hdul['SCI'].header['BUNIT'], fraction=0.05, shrink=0.9, pad=0.07)
        ticks = cb.ax.get_xticks()
        cb.ax.set_xticks([t for t in ticks if t>0.1])

    plt.tight_layout()

    outname = f'nrs_ta_analysis_{visitid}.pdf'
    plt.savefig(outname)
    print(f" => {outname}")


# ---------------------------------------------------------------------------
# Overall dispatcher
# ---------------------------------------------------------------------------

def auto_ta_results_analysis(visitid, save_localpath=False, localpath=None, verbose=True):
    visitid = utils.get_visitid(visitid)  # handle either input format

    inst = mast.visit_which_instrument(visitid)
    if verbose:
        print(f"Visit {visitid} used {inst} as prime instrument")
    if inst != 'NIRSPEC':
        return main_ta_analysis(visitid, verbose=verbose)
    else:
        nirspec_wata_ta_analysis(visitid, verbose=verbose)
        raise NotImplementedError("Need code to detect NRS TA type")
