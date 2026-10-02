import astropy
from astropy.io import fits
from astropy import table as astropy_table
from astropy import units as u
from copy import deepcopy
import jwst
import logging
import matplotlib
from matplotlib import pyplot as plt
import numpy as np
import os
from pathlib import Path
import shutil
import stpsf
import tempfile


from support_ta_monitor_guiding import which_guider_used
from support_ta_monitor_logs import extract_oss_TA_centroids, get_ictm_event_log
from support_ta_monitor_oss import get_ta_correction_for_visit
from support_ta_monitor_utils import get_siaf, get_visitid


# ---------------------------------------------------------------------------
# Image display helpers
# ---------------------------------------------------------------------------
def _miri_box_limits(hdul):
    """
    Return the display crop regions for a MIRI TA image.
    """
    apname = hdul[0].header['APERNAME']
    xlim = (0, 1023)
    ylim = (0, 1019)

    boxsize=64
    if apname =='MIRIM_TAMRS':
        # crop to upper corner
        xlim = (1023 - boxsize, 1023)
        ylim = (1019 - boxsize, 1019)
    elif apname == 'MIRIM_TASLITLESSPRISM' and hdul[0].header['SUBARRAY'] == 'SLITLESSPRISM':
        # crop to upper part.
        xlim = (8, None)
        ylim = (415 - boxsize, 415)
    elif apname == 'MIRIM_SLITLESSPRISM' and hdul[0].header['SUBARRAY'] == 'SLITLESSPRISM':
        # crop to upper part.
        xlim = (8, None)
        ylim = (415 - boxsize - 80, 415 - 80)
    elif apname =='MIRIM_TALRS':
        xlim = (382, 382 + boxsize)
        ylim = (258, 258 + boxsize)
    elif apname =='MIRIM_SLIT':
        xlim = (294, 294 + boxsize)
        ylim = (269, 269 + boxsize)

    non_nan_y = []
    for row in range(dat_region.shape[0]):
        if not np.all(np.isnan(dat_region[row,:])):
            non_nan_y.append(row)

    non_nan_x = []
    for row in range(dat_region.shape[1]):
        if not np.all(np.isnan(dat_region[:,row])):
            non_nan_x.append(row)

    x_lim_low = max(xlim[0], min(non_nan_x))
    x_lim_high = min(xlim[1], max(non_nan_x))

    y_lim_low = max(ylim[0], min(non_nan_y))
    y_lim_high = min(ylim[1], max(non_nan_y))

    xlim, ylim = (x_lim_low, x_lim_high), (y_lim_low, y_lim_high)

    return xlim, ylim


def _crop_display_for_miri(ax, hdul):
    """ Set xlim and ylim to crop the display region for a MIRI TA image
    Many MIRI TA images use full array, even though only a subarray is of interest.
    """
    # Note, this would be more elegant to look up from siaf but we just hard-code values here since none of this will ever change.
    xlim, ylim = _miri_box_limits(hdul)
    if xlim[1] is None:
        xlim = (xlim[0], )

    ax[0].set_xlim(*xlim)
    ax[0].set_ylim(*ylim)


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
            ax[0].set_xlim(1398-0.5, 1398+32-0.5)
            # no ylim crop needed, this is already only 32 pix tall
        elif subarray_name == 'FULL':
            # crop displayed region to be consistent with the SUB32 view
            ax[0].set_xlim(1398-0.5, 1398+32-0.5)
            ax[0].set_ylim(974-0.5, 975+32-0.5)


def _display_limits(instrument, hdul):
    if instrument == "MIRI":
        return _miri_box_limits(hdul)
    return (None, None), (None, None)


def _get_ta_reference_point(inst, hdul, filename):
    """ Determine the TA reference point, i.e. where was the target 'supposed to be' in any given observation
    This is usually the aperture reference location, but may be modified by any TA dithers, or
    by subarray/full array coord system shenanigans for MIR.
    """
    siaf = get_siaf(inst)
    ap = siaf.apertures[hdul[0].header['APERNAME']]

    if inst.upper() in ['NIRCAM', 'NIRISS']:
        xref = ap.XSciRef - 1   # siaf uses 1-based counting
        yref = ap.YSciRef - 1   # ditto

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
                logging.debug("TODO need to get more authoritative intended target position for MIRIM TA CONFIRM")
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
            logging.debug('ERROR DEBUG THIS')
    elif inst.upper() == 'NIRSPEC':
        # What is the location of the reference point?
        # For NIRSpec this slightly tricker since the aperture only has V2V3 ref defined, and
        # we need to convert that to detector coordinates. We can do that with the gWCS.
        model = jwst.datamodels.open(filename)
        ap = pysiaf.Siaf('NIRSpec')[model.meta.aperture.name]
        transform = model.meta.wcs.get_transform('v2v3', 'detector')  # Transform from V frame to subarray used in this obs
        xref, yref = transform(ap.V2Ref, ap.V3Ref)

    return xref, yref


def show_ta_img(visitid, hdul, filename, ax=None, return_handles=False, inst='NIRCam', **kwargs):
    """ Retrieve and display a target acq image"""

    inst = inst.upper()

    # If there are multiple TA images, you have to pick which one you want to display
    if len(hdul) == 0:
        raise RuntimeError("No TA images found for that visit")

    ta_img = hdul['SCI'].data
    if "integration" in kwargs:
        ta_img = ta_img[0, kwargs["integration"], :, :]
    if "dq_data" in kwargs and kwargs["dq_data"] is not None and kwargs["flagged"]:
        dq_data = kwargs["dq_data"]
        ta_img = ta_img.astype(np.float64)
        ta_img[dq_data != 0] = np.nan # Mask DO_NOT_USE pixels
    
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
    cmap = plt.get_cmap("viridis").with_extremes(bad="orange")

    norm = matplotlib.colors.AsinhNorm(linear_width = asinh_linear_width, vmax=vmax,
                                       vmin=-1*rsig)

    model = jwst.datamodels.open(filename)
    annotate_subarray = f"\n{model.meta.subarray.name} " if inst.upper() == "NIRSPEC" else ""
    annotation_text = f"Proposer: {model.meta.target.proposer_name}\n"
    annotation_text += f"{model.meta.instrument.filter}, {model.meta.exposure.readpatt}"
    annotation_text += f":{model.meta.exposure.ngroups}:{model.meta.exposure.nints}"
    annotation_text += f"{annotate_subarray}\n"
    annotation_text += f"Exposure Time: {model.meta.exposure.effective_exposure_time:.2f} s"

    if ax is None:
        ax = plt.gca()
    ax[0].imshow(ta_img - bglevel, norm=norm, cmap=cmap, origin='lower')
    ax[0].set_ylabel("[Pixels]")

    if inst.upper() == 'MIRI' and kwargs.get("zoom", True):
        _crop_display_for_miri(ax, hdul)
    elif inst.upper() == 'NIRSPEC' and kwargs.get("zoom", True):
        _crop_display_for_nirspec(ax, hdul)

    if kwargs.get("plot", True):
        xref, yref = _get_ta_reference_point(inst, hdul, filename)
        ax[0].axvline(xref, color='0.75', alpha=0.5, ls='--')
        ax[0].axhline(yref, color='0.75', alpha=0.5, ls='--')

    # mark aperture, and which guider was used
    annotation_text += f"\n{hdul[0].header['APERNAME']} using {which_guider_used(visitid)}"

    if return_handles:
        return hdul, ax, norm, cmap, bglevel, annotation_text


class TAPlot:
    """
    Creates a zoomed-in TA plot including crosshairs and metadata. Based on the
    TAAnalysis plot which was itself based on the ``main_ta_analysis()`` function.

    Parameters
    ----------
    visitid : str
        Visit ID string (with or without the leading 'V').
    inst : str
        Instrument name, e.g. 'NIRCam', 'NIRISS', 'MIRI'.
    ta_file : str
        Path to the TA file to be used for plotting
    **kwargs
        Additional keyword arguments forwarded to ``get_visit_ta_image`` and
        ``show_ta_img`` (e.g. ``localpath``, ``save_localpath``).

    Attributes
    ----------
    visitid : str
        Normalised visit ID.
    inst : str
        Upper-cased instrument name.

    Per-exposure lists (one entry per TA exposure, in exposure order)
    -----------------------------------------------------------------
    visit_id : str
    filename : str
    deltapos : tuple[float, float]
        Pointing offset (x, y) in pixels between the intended target location
        (aperture reference) and the measured centroid.
    deltapos_source : str
        Label indicating whether ``deltapos`` was derived from the OSS centroid
        or the local fwcentroid ('OSS - Intended' or 'fwcentroid-Intended').
    wcs_offset_pix : np.ndarray
        (x, y) offset in pixels between the WCS-derived target position and the
        OSS centroid.
    wcs_offset_radec : tuple
        Same offset expressed as (∆RA, ∆Dec) ``Angle`` objects in arcseconds.
    xyref : tuple[float, float]
        Intended target position (x, y) in the science pixel frame (0-based).
    oss_cen_sci_pythonic : np.ndarray or None
        OSS on-board centroid converted to the science pixel frame (0-based).
    targ_coords_pix : tuple
        WCS-derived target position in the science pixel frame.
    ta_cen_coords : astropy.coordinates.SkyCoord
        Sky coordinates corresponding to the OSS centroid pixel position.
    targ_coords : astropy.coordinates.SkyCoord
        Sky coordinates of the target from the header.
    cen : np.ndarray
        Local fwcentroid measurement (y, x order as returned by fwcentroid).
    oss_sam : np.ndarray or None
        OSS small-angle manoeuvre (∆V2, ∆V3) in arcsec.
    oss_sam_dpa : float or None
        OSS ∆V3PA from the SAM.
    """

    def __init__(self, visitid, ta_file, inst='NIRCam', **kwargs):
        self.visitid = get_visitid(visitid)
        self.inst = inst.upper()
        self.ta_file = ta_file
        self.check_image = kwargs.get("check_image", False)

        # Per-exposure result lists
        self.visit_ids: str = ""
        self.filenames: str = ""
        self.deltapos = None
        self.deltapos_source: str = ""
        self.wcs_offset_pix = None
        self.wcs_offset_radec = None
        self.xyref = None
        self.oss_cen_sci_pythonic = None
        self.targ_coords_pix = None
        self.ta_cen_coords = None
        self.targ_coords = None
        self.cen = None
        self.oss_sam = None
        self.oss_sam_dpa = None
        self.hdul = self._get_hdul_for_exposure()

        # Internal state set during run()
        self._siaf = get_siaf(self.inst)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def get_plot(self, **kwargs):
        """
        Returns a plot for the exposure (with associated keyword arguments)
        """
        self.uncal = False
        if "integration" in kwargs:
            self.uncal = True
            self.integration = kwargs["integration"]
        self._analyze_single_exposure()

        do_plot = kwargs.get("plot", True)

        xlim, ylim = _display_limits(self.inst, self.hdul)
        logging.info(f"Plot Limits are {xlim} {ylim}")

        fig, ax = plt.subplots(1, 2)
        ax[0].title.set_visible(False)
        ax[1].title.set_visible(False)
        ax[1].axis('off')

        hdul, ax, norm, cmap, bglevel, plot_text = show_ta_img(
            self.visitid,
            self.hdul,
            self.ta_file,
            ax=ax,
            return_handles=True,
            inst=self.inst,
            **kwargs
        )

        if not self.check_image:
            self._plot_oss_centroid(ax, do_plot, xlim, ylim)
        self._plot_wcs_position(ax, do_plot, xlim, ylim)
        self._plot_local_centroid(ax, do_plot, xlim, ylim)

        wcs_text = self._plot_wcs_offsets()
        if wcs_text != "":
            plot_text += f"\n{wcs_text}"
        annotation_text = self._annotate_plot()
        if annotation_text != "":
            plot_text += f"\n{annotation_text}"
        self._finalize_plot(fig, ax, plot_text)

        return fig

    def _get_hdul_for_exposure(self):
        """Return the HDUList for exposure ``i_ta_image``.

        If plotting is enabled this also renders the TA image into the
        appropriate axis.
        """
        with fits.open(self.ta_file) as ff:
            hdul = deepcopy(ff)
        return hdul

    def _clean_image(self, hdul, interp_kernel_size):
        """Return a NaN-interpolated copy of the SCI extension."""
        im_obs = hdul['SCI'].data
        if self.uncal:
            im_obs = im_obs[0, self.integration, :, :]
        im_obs_clean = im_obs.copy()
        if 'DQ' in hdul:
            im_obs_dq = hdul['DQ'].data
        else:
            return im_obs_clean
        im_obs_clean[im_obs_dq & 1] = np.nan  # Mask DO_NOT_USE pixels

        kernel = np.ones(interp_kernel_size)
        im_obs_clean = astropy.convolution.interpolate_replace_nans(
            im_obs, kernel=kernel)

        for _ in range(2):
            if np.any(np.isnan(im_obs_clean)):
                logging.debug('iterating to interpolate over more NaNs')
                im_obs_clean = astropy.convolution.interpolate_replace_nans(
                    im_obs_clean, kernel=kernel)
            else:
                break
        else:
            if np.any(np.isnan(im_obs_clean)):
                logging.debug("Masking remaining NaNs to image median")
                im_obs_clean[np.isnan(im_obs_clean)] = np.nanmedian(im_obs_clean)

        return im_obs_clean

    def _get_instrument_config(self, ta_aperture):
        """Return ``(full_ap, interp_kernel_size)`` for the current instrument."""
        if self.inst == 'NIRCAM':
            full_ap = self._siaf[ta_aperture.AperName[0:5] + "_FULL"]
            interp_kernel_size = (5, 5)
        elif self.inst == 'NIRISS':
            full_ap = self._siaf["NIS_CEN"]
            interp_kernel_size = (5, 5)
        elif self.inst == 'MIRI':
            full_ap = self._siaf["MIRIM_FULL"]
            interp_kernel_size = (11, 11)
        else:
            raise ValueError(f"Unsupported instrument: {self.inst}")
        return full_ap, interp_kernel_size

    def _compute_oss_centroid(self, hdul, ta_aperture, full_ap):
        """Retrieve and convert the OSS on-board centroid.

        Returns ``(oss_cen_sci_pythonic, oss_centroid_text)``.
        """
        oss_cen_sci_pythonic = (np.nan, np.nan)
        oss_centroid_text = ""
        oss_cen_full_sci = None

        try:
            osslog = get_ictm_event_log(
                hdul[0].header['VSTSTART'], hdul[0].header['VISITEND']
            )
            try:
                oss_cen = extract_oss_TA_centroids(
                    osslog, 'V' + hdul[0].header['VISIT_ID']
                )

                if self.inst == "NIRISS":
                    logging.debug("transposing X & Y, due to NIRISS detector coordinate frame")
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

                oss_centroid_text = (
                    f"OSS centroid: {oss_cen_sci_pythonic[0]:.2f},"
                    f" {oss_cen_sci_pythonic[1]:.2f}"
                )

                msg = f"OSS centroid on board:  {oss_cen}  (full det coord frame, 1-based)"
                logging.debug(msg)
                msg = f"OSS centroid converted: {oss_cen_sci_pythonic}  (sci frame in {ta_aperture.AperName}, 0-based)"
                logging.debug(msg)
                if oss_cen_full_sci is not None:
                    msg = f"OSS centroid converted: {oss_cen_full_sci}  (sci frame in {full_ap.AperName}, 0-based)"
                    logging.debug(msg)

            except RuntimeError:
                logging.info("Could not parse TA coordinates from log. TA may have failed?")
                oss_cen_sci_pythonic = (np.nan, np.nan)
                oss_centroid_text = "No OSS centroid; TA failed"

        except RuntimeError:
            logging.info("Could not get coords from OSS log. TA may have failed?")

        return oss_cen_sci_pythonic, oss_centroid_text

    def _plot_oss_centroid(self, ax, plot_centroid, xlim, ylim):
        """
        Add the OSS centroid text to the figure.
        """
        if not np.isnan(self.oss_cen_sci_pythonic[0]):
            if plot_centroid:
                if xlim[0] is not None and self.oss_cen_sci_pythonic[0] < xlim[0]:
                    return
                if xlim[1] is not None and self.oss_cen_sci_pythonic[0] > xlim[1]:
                    return
                if ylim[0] is not None and self.oss_cen_sci_pythonic[1] < ylim[0]:
                    return
                if ylim[1] is not None and self.oss_cen_sci_pythonic[1] > ylim[1]:
                    return
                ax[0].scatter(
                    self.oss_cen_sci_pythonic[0],
                    self.oss_cen_sci_pythonic[1],
                    color='0.5',
                    marker='x',
                    s=50
                )
                ax[0].text(
                    self.oss_cen_sci_pythonic[0], self.oss_cen_sci_pythonic[1],
                    'OSS  ', color='0.9',
                    verticalalignment='center',
                    horizontalalignment='right')

    def _compute_oss_sam(self):
        """Retrieve the OSS small-angle manoeuvre.

        Returns ``(oss_sam, oss_sam_dpa)``, each ``None`` on failure.
        """
        try:
            oss_sam, oss_sam_dpa = get_ta_correction_for_visit(self.visitid)
            logging.debug(f"OSS SAM: (∆V2, ∆V3) = {oss_sam}  ∆V3PA = {oss_sam_dpa}")
        except RuntimeError:
            logging.info("Could not get coords from OSS log. TA may have failed?")
            oss_sam, oss_sam_dpa = None, None
        return oss_sam, oss_sam_dpa

    def _compute_wcs_position(self, hdul):
        """Compute WCS-based target pixel position.

        Returns ``(model, targ_coords, targ_coords_pix, wcs_text)``.
        """
        model = jwst.datamodels.open(self.ta_file)
        targ_coords = astropy.coordinates.SkyCoord(
            model.meta.target.ra, model.meta.target.dec,
            frame='icrs', unit=u.deg
        )
        if model.meta.wcs is not None:
            targ_coords_pix = model.meta.wcs.world_to_pixel(targ_coords)
        else:
            targ_coords_pix = (0., 0.)
        wcs_text = (f'Expected from WCS: {targ_coords_pix[0]:.2f},'
                    f' {targ_coords_pix[1]:.2f}')

        logging.debug(f"Target coords: {targ_coords}")
        logging.debug(f"               {targ_coords.to_string('hmsdms', sep=':')}")

        return model, targ_coords, targ_coords_pix, wcs_text

    def _plot_wcs_position(self, ax, plot_wcs, xlim, ylim):
        if plot_wcs:
            if xlim[0] is not None and self.targ_coords_pix[0] < xlim[0]:
                return
            if xlim[1] is not None and self.targ_coords_pix[0] > xlim[1]:
                return
            if ylim[0] is not None and self.targ_coords_pix[1] < ylim[0]:
                return
            if ylim[1] is not None and self.targ_coords_pix[1] > ylim[1]:
                return
            ax[0].scatter(
               self.targ_coords_pix[0], self.targ_coords_pix[1],
               color='magenta', marker='+', s=50
            )
            ax[0].text(
                self.targ_coords_pix[0], self.targ_coords_pix[1] + 2,
                'WCS', color='magenta',
                verticalalignment='bottom', horizontalalignment='center')

    def _compute_local_centroid(self, im_obs_clean, hdul):
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

        cen = stpsf.fwcentroid.fwcentroid(im_obs_clean * border_mask)

        if self.inst == 'MIRI':
            logging.debug('Need to update plotting code for subarray calc  in full frame image')

        return cen

    def _plot_local_centroid(self, ax, plot_local_centroid, xlim, ylim):
        if plot_local_centroid:
            if xlim[0] is not None and self.cen[0] < xlim[0]:
                return
            if xlim[1] is not None and self.cen[0] > xlim[1]:
                return
            if ylim[0] is not None and self.cen[1] < ylim[0]:
                return
            if ylim[1] is not None and self.cen[1] > ylim[1]:
                return
            ax[0].scatter(
                self.cen[1], self.cen[0], color='red', marker='+', s=50
            )
            ax[0].text(
                self.cen[1], self.cen[0], '  stpsf', color='red',
                verticalalignment='top', horizontalalignment='left', clip_on=True
            )

    def _compute_wcs_offsets(self, targ_coords, targ_coords_pix,
                              oss_cen_sci_pythonic, model,
                              oss_sam):
        """Compute pixel and RA/Dec offsets between WCS and OSS centroid.

        Updates ``self.wcs_offset_pix``, ``self.wcs_offset_radec``,
        ``self.ta_cen_coords``, and ``self.targ_coords``.
        """
        wcs_offset_pix = np.array([np.nan, np.nan])
        wcs_offset_radec = (np.nan, np.nan)

        if oss_cen_sci_pythonic is not None and not np.any(np.isnan(oss_cen_sci_pythonic)):
            wcs_offset_pix = (np.asarray(targ_coords_pix) - oss_cen_sci_pythonic)
            self.wcs_offset_pix = wcs_offset_pix

            if model.meta.wcs is not None:
                ta_cen_coords = model.meta.wcs.pixel_to_world(*oss_cen_sci_pythonic)
            else:
                self.ta_cen_coords = None
                self.targ_coords = None
                self.wcs_offset_radec = None
                return wcs_offset_pix, None
            self.ta_cen_coords = ta_cen_coords
            self.targ_coords = targ_coords

            dra, ddec = ta_cen_coords.spherical_offsets_to(targ_coords)
            wcs_offset_radec = (dra.to(u.arcsec).value, ddec.to(u.arcsec).value)
            self.wcs_offset_radec = wcs_offset_radec

            logging.debug(f"WCS offset =  {wcs_offset_pix} pix  (WCS - OSS)")
            logging.debug(f'TARG_COORDS: {targ_coords}')
            logging.debug(f'TA_CEN_COORDS: {ta_cen_coords}')
            logging.debug(f"DRA, DDEC: {dra} {ddec}")

        return wcs_offset_pix, wcs_offset_radec

    def _plot_wcs_offsets(self):
        plot_text = ""
        if self.wcs_offset_radec is not None:
            plot_text = f'WCS $\\Delta$RA, $\\Delta$Dec = {self.wcs_offset_radec[0]:.3f},'
            plot_text += f' {self.wcs_offset_radec[1]:.3f} arcsec'
        if self.oss_sam is not None:
            if plot_text != "":
                plot_text += "\n"
            plot_text += f'TA SAM (V2, V3)= {self.oss_sam[0]:.3f}, {self.oss_sam[1]:.3f} arcsec'
        return plot_text

    def _analyze_single_exposure(self):
        """Run analysis for one TA exposure and append results to all lists."""
        deltapos = (np.nan, np.nan)

        # --- Load image ---
        ta_aperture = self._siaf.apertures[self.hdul[0].header['APERNAME']]
        xref, yref = _get_ta_reference_point(self.inst, self.hdul, self.ta_file)

        self.visit_ids = self.visitid
        self.filename = self.hdul[0].header.get('FILENAME', '')
        self.xyref = (xref, yref)

        # --- Instrument-specific config ---
        if self.inst == 'MIRI' and self.hdul[0].header['APERNAME'] == 'MIRIM_SLIT':
            full_ap = self._siaf["MIRIM_FULL"]
            ta_aperture = full_ap
        full_ap, interp_kernel_size = self._get_instrument_config(ta_aperture)
        self.ta_aperture = ta_aperture

        # --- Clean image ---
        im_obs_clean = self._clean_image(self.hdul, interp_kernel_size)

        # --- OSS centroid ---
        try:
            oss_cen_sci_pythonic, oss_centroid_text = self._compute_oss_centroid(self.hdul, ta_aperture, full_ap)

            oss_sam, oss_sam_dpa = self._compute_oss_sam()

            # --- WCS position ---
            model, targ_coords, targ_coords_pix, wcs_text = self._compute_wcs_position(self.hdul)

        except ImportError:
            oss_centroid_text = ""
            wcs_text = ""
            oss_cen_sci_pythonic = (np.nan, np.nan)
            oss_sam = None
            oss_sam_dpa = None
            model = jwst.datamodels.open(self.ta_file)
            targ_coords = None
            targ_coords_pix = (np.nan, np.nan)

        self.oss_cen_sci_pythonic = oss_cen_sci_pythonic
        self.oss_sam = oss_sam
        self.oss_sam_dpa = oss_sam_dpa
        self.targ_coords_pix = targ_coords_pix
        self.oss_centroid_text = oss_centroid_text
        self.wcs_text = wcs_text
        if targ_coords_pix[0] == 0 and targ_coords_pix[1] == 0:
            self.wcs_text = ""
        self.aperture_text = f'Intended target pos: {xref:.2f}, {yref:.2f}'

        # --- Local centroid ---
        cen = self._compute_local_centroid(im_obs_clean, self.hdul)
        self.cen = cen

        # --- Delta-position ---
        if not self.check_image:
            logging.debug(f"Comparing to OSS on-board centroid for TA image")
            deltapos = (oss_cen_sci_pythonic[0] - xref,
                        oss_cen_sci_pythonic[1] - yref)
            deltapos_type = 'OSS - Intended'
        else:
            logging.debug(f"Comparing to local STPSF centroid for TA image")
            deltapos = (cen[1] - xref, cen[0] - yref)
            deltapos_type = 'fwcentroid - Intended'

        self.deltapos = deltapos
        self.deltapos_source = deltapos_type

        # --- WCS offsets (updates self.wcs_offset_pix/radec internally) ---
        if targ_coords is not None:
            self._compute_wcs_offsets(
                targ_coords, targ_coords_pix,
                oss_cen_sci_pythonic, model,
                oss_sam)

        logging.debug(f"Star coords from WCS: {targ_coords_pix}")

    def _annotate_plot(self):
        image_text = (f"Pixel coordinates (0-based):\n")
        image_text += f" {self.aperture_text}\n"
        if not self.check_image:
            image_text += f" {self.oss_centroid_text}\n"
        image_text += f" stpsf measure_centroid: {self.cen[1]:.2f}, {self.cen[0]:.2f}\n"
        if self.wcs_text != "" and not self.check_image:
            image_text += f" {self.wcs_text}\n"
        image_text += f" $\\Delta$pos ({self.deltapos_source}): "
        image_text += f"{self.deltapos[0]:.2f}, {self.deltapos[1]:.2f}\n"
        image_text += f" = {self.deltapos[0] * self.ta_aperture.XSciScale:.3f},"
        image_text += f" {self.deltapos[1] * self.ta_aperture.YSciScale:.3f} arcsec"

        return image_text

    def _finalize_plot(self, fig, ax, incoming_text):
        """Add colorbars, footer text, and save the figure."""
        cb = fig.colorbar(
            ax[0].images[0], ax=ax[0], orientation='vertical',
            label=self.hdul['SCI'].header['BUNIT'],
            fraction=0.05, shrink=0.9, pad=0.07)
        ticks = cb.ax.get_xticks()
        cb.ax.set_xticks([t for t in ticks if t > 0.1])

        now = astropy.time.Time.now()
        sdp_ver = self.hdul[0].header['SDP_VER']
        plot_text = incoming_text + "\n\n"
        plot_text += f"Analysis on {now.isot[0:16]}.\nFile from MAST SDP {sdp_ver}"
        if "CAL_VER" in self.hdul[0].header:
            plot_text + f", pipeline {self.hdul[0].header['CAL_VER']}"
        ax[1].text(0.05, 0., plot_text, color='black', fontsize='small')

        plt.tight_layout()
