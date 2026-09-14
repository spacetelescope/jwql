
import os, sys
import requests
import functools
from astroquery.mast import Mast,Observations
from astropy.table import Table, unique, vstack
import astropy.time, astropy.stats
import astropy.io.fits as fits
import numpy as np
import scipy
import functools
import warnings
from urllib.request import urlopen
from io import BytesIO


import matplotlib, matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
#import mpl_scatter_density


import pysiaf
import jwst.datamodels
from jwql.instrument_monitors.common_monitors.ta_monitor import mast, utils
from jwql.instrument_monitors.common_monitors.ta_monitor.mast import mast_retrieve_files, set_params



@functools.lru_cache
def find_relevant_guiding_file(sci_filename, verbose=True):
    """ Given a filename of a JWST science file, retrieve the relevant guiding data product.
    This uses FITS keywords in the science header to determine the time period and guide mode,
    and then retrieves the file from MAST

    """


    sci_hdul = fits.open(sci_filename)

    progid = sci_hdul[0].header['PROGRAM']
    obs = sci_hdul[0].header['OBSERVTN']
    guidemode = sci_hdul[0].header['PCS_MODE']


    # Set up the query
    keywords = {
    'program': [progid]
    ,'observtn': [obs]
    ,'exp_type': ['FGS_'+guidemode]
    }

    params = {
        'columns': '*',
        'filters': set_params(keywords)
        }


    # Run the web service query. This uses the specialized, lower-level webservice for the
    # guidestar queries: https://mast.stsci.edu/api/v0/_services.html#MastScienceInstrumentKeywordsGuideStar

    service = 'Mast.Jwst.Filtered.GuideStar'
    t = Mast.service_request(service, params)


    if len(t) > 0:
        # Ensure unique file names, should any be repeated over multiple observations (e.g. if parallels):
        fn = list(set(t['fileName']))
        # Set of derived Observation IDs:

        products = list(set(fn))
        # If you want the uncals instead do this:
        #products = list(set([x.replace('_cal','_uncal') for x in fn]))
    products.sort()


    if verbose:
        print(f"For science data file: {sci_filename}")
        print("Found guiding telemetry files:")
        for p in products:
            print("   ", p)

    # Some guide files are split into multiple segments, which we have to deal with.
    guide_timestamp_parts = [fn.split('_')[2] for fn in products]
    is_segmented = ['seg' in part for part in guide_timestamp_parts]
    for i in range(len(guide_timestamp_parts)):
        if is_segmented[i]:
            guide_timestamp_parts[i] = guide_timestamp_parts[i].split('-')[0]
    guide_timestamps = np.asarray(guide_timestamp_parts, int)
    t_beg = astropy.time.Time(sci_hdul[0].header['DATE-BEG'])
    t_end = astropy.time.Time(sci_hdul[0].header['DATE-END'])
    obs_end_time = int(t_end.strftime('%Y%j%H%M%S'))

    delta_times = np.array(guide_timestamps-obs_end_time, float)
    # want to find the minimum delta which is at least positive
    #print(delta_times)
    delta_times[delta_times<0] = np.nan
    #print(delta_times)

    wmatch = np.argmin(np.abs(delta_times))
    wmatch = np.where(delta_times ==np.nanmin(delta_times))[0][0]
    delta_min = (guide_timestamps-obs_end_time)[wmatch]

    if verbose:
        print("Based on science DATE-END keyword and guiding timestamps, the matching GS file is: ")
        print("   ", products[wmatch])
        print(f"    t_end = {obs_end_time}\t delta = {delta_min}")

    if is_segmented[wmatch]:
        # We ought to fetch all the segmented GS files for that guide period
        products_to_fetch = [fn for fn in products if fn.startswith(products[wmatch][0:33])]
        if verbose:
            print("   That GS data is divided into multiple segment files:")
            print("   ".join(products_to_fetch))
    else:
        products_to_fetch = [products[wmatch],]

    outfiles = mast_retrieve_files(products_to_fetch)

    return outfiles


@functools.lru_cache
def find_visit_guiding_files(visitid, guidemode='FINEGUIDE', verbose=True, autodownload=True):
    """ Given a JWST visit id string, like 'V01234005001', retrieve specified guiding data products
    for that visit from MAST. Files downloaded into current working directory.

    This version of the function requires specifying a single guidemode at a time, e.g. 'ACQ1'
    and only returns that type of file. See also find_all_visit_guiding_files


    """

    visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
    progid = visitid[1:6]
    obs = visitid[6:9]

    if guidemode.upper()=='ID':
        exp_type = 'FGS_ID-IMAGE'
    elif guidemode.upper()=='ACQ' or guidemode.upper()=='ACQ1':
        exp_type = 'FGS_ACQ1'
    elif guidemode.upper()=='ACQ2':
        exp_type = 'FGS_ACQ2'
    elif guidemode.upper() == 'TRACK':
        exp_type = 'FGS_TRACK'
    elif guidemode.upper() == 'FINEGUIDE':
        exp_type = 'FGS_FINEGUIDE'
    else:
        raise ValueError(f"Unknown/invalid guidemode parameter: {guidemode}")


    # Set up the query
    keywords = {
    'program': [progid]
    ,'observtn': [obs]
    ,'exp_type': [exp_type]
    }

    params = {
        'columns': '*',
        'filters': set_params(keywords)
        }

    if verbose:
        print(params)
    # Run the web service query. This uses the specialized, lower-level webservice for the
    # guidestar queries: https://mast.stsci.edu/api/v0/_services.html#MastScienceInstrumentKeywordsGuideStar

    service = 'Mast.Jwst.Filtered.GuideStar'
    t = Mast.service_request(service, params)


    if len(t) > 0:
        # Ensure unique file names, should any be repeated over multiple observations (e.g. if parallels):
        fn = list(set(t['fileName']))
        # Set of derived Observation IDs:

        products = list(set(fn))
        # If you want the uncals instead do this:
        #products = list(set([x.replace('_cal','_uncal') for x in fn]))
        products.sort()
    else:
        print("Query returned no guiding files")
        return None

    if verbose:
        print(f"For visit: {visitid}")
        print("Found guiding telemetry files:")
        for p in products:
            print("   ", p)

    if autodownload:
        outfiles = mast_retrieve_files(products)
        return outfiles
    else:
        return products



@functools.lru_cache
def find_guiding_id_file(sci_filename=None, guidemode='ID', progid=None, obs=None, visit=1, visitid=None, verbose=True,
        autodownload=True):
    """ Given a filename of a JWST science file, retrieve the relevant guiding ID data product.
    (or Acq data product)
    This uses FITS keywords in the science header to determine the time period and guide mode,
    and then retrieves the file from MAST

    See also
    --------
    find_visit_guiding_files, find_all_visit_guiding_files

    """

    if sci_filename is not None:
        sci_hdul = fits.open(sci_filename)
        progid_str = sci_hdul[0].header['PROGRAM']
        obs_str = sci_hdul[0].header['OBSERVTN']
        visit_str = sci_hdul[0].header['VISIT_ID']
    elif visitid is not None:
        visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
        progid_str = visitid[1:6]
        obs_str = visitid[6:9]
        visit_str = visitid[1:12]
    elif progid is None or obs is None or visit is None:
        raise RuntimeError("You must supply either the sci_filename parameter, or visitid, or both progid and obs (optionally also visit)")
    else:
        progid_str = f'{progid:05d}'
        obs_str = f'{obs:03d}'
        visit_str = f'{progid:05d}{obs:03d}{visit:03d}'

    return find_visit_guiding_files(visitid='V'+visit_str, guidemode='ID')


@functools.lru_cache
def find_all_visit_guiding_files(visitid, verbose=False, exclude_stacked=True, autodownload=True):
    """ Given a JWST visit id string, like 'V01234005001', retrieve all guiding data products
    for that visit from MAST. Files downloaded into current working directory.

    This function returns all the guiding files, of all types.
    See also find_visit_guiding_files for a version that allows specifying a single
    guidemode at a time, e.g. 'ACQ1' and only returns that type of file.

    This version returns a Table of outputs, and the relevant start and end times

    """
    if visitid is not None:
        visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
        progid = visitid[1:6]
        obs = visitid[6:9]
        vis = visitid[9:12]

    # Set up the query
    keywords = {
    'program': [progid]
    ,'observtn': [obs]
    #'exp_type': [exp_type]
    #,'visit': [vis]
    }

    params = {
        'columns': '*',
        'filters': set_params(keywords)
        }

    # Run the web service query. This uses the specialized, lower-level webservice for the
    # guidestar queries: https://mast.stsci.edu/api/v0/_services.html#MastScienceInstrumentKeywordsGuideStar

    #if verbose:
    #    print(params)
    service = 'Mast.Jwst.Filtered.GuideStar'
    t = Mast.service_request(service, params)

    if len(t) > 0:
        t.sort(keys='date_end_mjd')  # Empirically this works better as a sort key than some of the other date keywords; not sure why!

        # Ensure unique file names, should any be repeated over multiple observations (e.g. if parallels):
        fn = t['fileName']
        # Set of derived Observation IDs:

        products = list(fn)
        times_start = list(t['date_obs_mjd'])
        times_end = list(t['date_end_mjd'])

    else:
        if verbose:
            print("Query returned no guiding files")
        return None

    # TODO clean up this next block of code, now that it's a table below
    if exclude_stacked:
        # ignore stacked_cal files; redundant with the _image_cal files.
        combined = [(fn, tstart, tend) for fn, tstart, tend in zip(products, times_start, times_end) if 'stacked_cal.fits' not in fn ]
        filenames = [a[0] for a in combined]
        times_start = astropy.time.Time([a[1] for a in combined], format='mjd')
        times_end = astropy.time.Time([a[2] for a in combined], format='mjd')
    else:
        filenames = products

    if verbose:
        print(f"For visit: {visitid}")
        print("Found guiding telemetry files:")
        for p in products:
            print("   ", p)

    guiding_file_table = astropy.table.Table([filenames, times_start, times_end], names = ['Filename', 'Time Start', 'Time End'])

    if autodownload:
        outfiles = mast_retrieve_files(guiding_file_table['Filename'])

    return guiding_file_table


def guiding_performance_plot(sci_filename=None, visitid=None, verbose=True, save=False, yrange=None,
                             time_range_fraction=None):
    """Generate a plot showing the guiding jitter during an exposure or visit


    """
    if sci_filename is None and visitid is None:
        raise RuntimeError("You must set either sci_filename or visitid")

    # Retrieve the guiding packet file(s) from MAST
    if visitid:
        visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
        visit_mode = True
        gs_fns = find_visit_guiding_files(visitid, verbose=verbose)
    else:
        visit_mode = False
        gs_fns = find_relevant_guiding_file(sci_filename)

        # Determine start and end times for the exposure
        with fits.open(sci_filename) as sci_hdul:
            t_beg = astropy.time.Time(sci_hdul[0].header['DATE-BEG'])
            t_end = astropy.time.Time(sci_hdul[0].header['DATE-END'])

    gs_fn = gs_fns[0]

    # We may have multiple GS filenames returned, in the case where the data is split into several segments
    # If so, concatenat them

    dither_times = []
    last_gs_fn_middle= ''
    for i, gs_fn in enumerate(gs_fns):
        gs_fn_base = os.path.splitext(os.path.basename(gs_fn))[0]

        if i==0:  # For a single file or first segment, just read it in
            # Read the data from that file, and parse into astropy Times
            pointing_table = astropy.table.Table.read(gs_fn, hdu=4)
            centroid_table = astropy.table.Table.read(gs_fn, hdu=5)
            display_gs_fn = os.path.basename(gs_fn)
            if visit_mode:
                # We have to compute means per segment, since it's not meaningful to combine across dithers
                mask = centroid_table.columns['bad_centroid_dq_flag'] == 'GOOD'
                xmean = np.nanmean(centroid_table[mask]['guide_star_position_x'])
                ymean = np.nanmean(centroid_table[mask]['guide_star_position_y'])
                centroid_table['guide_star_position_x'] -= xmean
                centroid_table['guide_star_position_y'] -= ymean


        else:  # for a later segment, read in and append
            pointing_table_more = astropy.table.Table.read(gs_fn, hdu=4)
            centroid_table_more = astropy.table.Table.read(gs_fn, hdu=5)
            # mark one point as NaN, to visually show a gap in the plot
            centroid_table_more['guide_star_position_x'][-1] = np.nan
            centroid_table_more['guide_star_position_y'][-1] = np.nan
            centroid_table_more['bad_centroid_dq_flag'][-1] = 'GOOD'

            if visit_mode:
                fn_middle = os.path.basename(gs_fn).split('-')[1]
                if fn_middle != last_gs_fn_middle: # New time in file stamp, after a dither and reacq
                    dither_times.append(astropy.time.Time(pointing_table_more.columns['time'][0], format='mjd') )
                    last_gs_fn_middle = fn_middle
                    if verbose:
                        print(f"Dither before {gs_fn} at {dither_times[-1].iso}")
                # We have to compute means per guide file, since it's not meaningful to combine across dithers
                #  But, for multiple contiguous segments, seg002 and onwards, use the same xmean as computed on
                #  the first segment, for consistency and to avoid spurious discontinuities.
                mask = centroid_table_more.columns['bad_centroid_dq_flag'] == 'GOOD'
                if 'seg' not in gs_fn or 'seg001' in gs_fn:
                    xmean = np.nanmean(centroid_table_more[mask]['guide_star_position_x'])
                    ymean = np.nanmean(centroid_table_more[mask]['guide_star_position_y'])
                centroid_table_more['guide_star_position_x'] -= xmean
                centroid_table_more['guide_star_position_y'] -= ymean

            pointing_table = astropy.table.vstack([pointing_table, pointing_table_more], metadata_conflicts='silent')
            centroid_table = astropy.table.vstack([centroid_table, centroid_table_more], metadata_conflicts='silent')
            display_gs_fn = os.path.basename(gs_fn)[0:33]+ "-seg*_cal.fits"
    if visit_mode:
        display_gs_fn = f"All (n={len(gs_fns)}) guidestar Fine Guide files for {visitid}"

    mask = centroid_table.columns['bad_centroid_dq_flag'] == 'GOOD'

    ctimes = astropy.time.Time(centroid_table['observatory_time'])
    ptimes = astropy.time.Time(pointing_table.columns['time'], format='mjd')

    # Compute the mean X and Y positions
    xmean = np.nanmean(centroid_table[mask]['guide_star_position_x'])
    ymean = np.nanmean(centroid_table[mask]['guide_star_position_y'])


    # Create Plots
    fig, axes = plt.subplots(figsize=(16,12), nrows=3)

    min_time = np.min([ptimes.plot_date.min(), ctimes.plot_date.min()])
    max_time = np.max([ptimes.plot_date.max(), ctimes.plot_date.max()])
    dtime = max_time - min_time

    if not visit_mode:
        # Find the subset of centroid data from during that exposure
        ptimes_during_exposure = (t_beg < ptimes ) & (ptimes < t_end)
        ctimes_during_exposure = (t_beg < ctimes[mask] ) & (ctimes[mask] < t_end)


    for i in range(3):
        axes[i].xaxis.axis_date()
        axes[i].set_xlim(min_time -0.01*dtime, max_time+0.01*dtime)

    if visit_mode:
        axes[0].set_title(f"Guiding during {visitid}", fontweight='bold', fontsize=18)
        if len(dither_times)>0:
            axes[1].text(0.5, 0.05, "Centroids offsets shown are relative to the mean position within each guider file (usually per dither)",
                         transform=axes[1].transAxes, horizontalalignment='center')
    else:
        axes[0].set_title(f"Guiding during {os.path.basename(sci_filename)}", fontweight='bold', fontsize=18)

    axes[0].semilogy(ptimes.plot_date, pointing_table.columns['jitter'], alpha=0.9, color='C0')
    axes[0].set_ylim(1e-2, 1e3)
    axes[0].set_ylabel("Jitter\n[mas]", fontsize=18)
    axes[0].text(0.01, 0.95, display_gs_fn, fontsize=16, transform=axes[0].transAxes, verticalalignment='top')

    axes[0].text(ptimes.plot_date.min(), 100, " Guiding Start", color='C0', clip_on=True)
    axes[0].text(ptimes.plot_date.max(), 100, "Guiding End ", color='C0',
                horizontalalignment='right', clip_on = True)


    axes[1].plot(ctimes[mask].plot_date, centroid_table[mask]['guide_star_position_x']-xmean, label='X Centroids', color='C1', alpha=0.7)
    axes[1].plot(ctimes[mask].plot_date, centroid_table[mask]['guide_star_position_y']-ymean, label='Y Centroids', color='C4', alpha=0.7)
    axes[1].legend(loc='lower right')
    axes[1].set_ylabel("GS centroid offsets\n[arcsec]", fontsize=18)
    axes[1].axhline(0, ls=":", color='gray')
    if yrange is not None:
        axes[1].set_ylim(*yrange)

    axes[2].plot(ctimes.plot_date, mask, label='GOOD Centroids', color='C1')
    frac_good = mask.sum() / len(mask)
    print(f'Fraction of good centroids: {frac_good}')
    if frac_good < 0.95:
        axes[2].text(0.5, 0.9, f"WARNING, {(1-frac_good)*100:.2f}% of guider centroids were BAD during this.",
                     color='red', fontweight='bold', transform=axes[2].transAxes, horizontalalignment='center')

    if not visit_mode:
        axes[0].text(t_beg.plot_date, 20,
                 f"    mean jitter: {pointing_table.columns['jitter'][ptimes_during_exposure].mean():.2f} mas", color='green')
        axes[0].text(t_beg.plot_date, 50, " Exposure", color='green')

        axes[0].axvspan(t_beg.plot_date, t_end.plot_date, color='green', alpha=0.15)
        axes[1].axvspan(t_beg.plot_date, t_end.plot_date, color='green', alpha=0.15)
        axes[2].axvspan(t_beg.plot_date, t_end.plot_date, color='green', alpha=0.15)
    else:
        # Annotate start of each FG file
        for i, gs_fn in enumerate(gs_fns):
            start_time = dither_times[i-1] if i>0 else ptimes.min()
            axes[0].text(start_time.plot_date, 1.5e-2, os.path.basename(gs_fn), fontsize='x-small', clip_on=True)
        # Mark dithers with vertical lines
        for dithertime in dither_times:
           for ax in axes:
                ax.axvline(dithertime.plot_date, color='black', ls='--')
           axes[2].text(dithertime.plot_date, -0.35, 'SAM', rotation=90, clip_on=True)

        exposure_table = mast.get_visit_exposure_times(visitid)
        already_plotted_exptimes = set()
        for row in exposure_table:
            if row['date_beg_mjd'].plot_date in already_plotted_exptimes:
                continue
            if verbose:
                print(f"Exposure {row['filename']} began at {row['date_beg_mjd'].iso}")

            for ax in axes:
                ax.axvspan(row['date_beg_mjd'].plot_date, row['date_end_mjd'].plot_date, color='green', alpha=0.15)
            axes[2].text(row['date_beg_mjd'].plot_date, -0.25, row['filename'], color='green', rotation=10, fontsize='small',
                         clip_on=True)
            already_plotted_exptimes.add(row['date_beg_mjd'].plot_date)


    axes[2].set_ylabel("Centroid Quality Flag\n", fontsize=18)
    axes[2].set_yticks((0,1))
    axes[2].set_ylim(-0.5, 1.5)
    axes[2].set_yticklabels(['BAD', 'GOOD'])

    if time_range_fraction:
        tl = axes[0].get_xlim()
        t_duration = tl[1] - tl[0]
        for ax in axes:
            ax.set_xlim(tl[0] + time_range_fraction[0]*t_duration,
                        tl[0] + time_range_fraction[1]*t_duration)





    if visit_mode:
        outname = f'guidingplot_{visitid}.pdf'
    else:
        outname = f'guidingplot_{gs_fn_base}.pdf'

    if save:
        plt.savefig(outname)
        if verbose:
            print(f' ==> {outname}')



def guiding_dithers_plot(visitid, verbose=True, save=False, alpha=0.2,
                             ignore_ta_exposures=True, ):
    """Generate a plot showing the guiding dither pattern during a visit


    """
    # Retrieve the guiding packet file(s) from MAST
    visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
    visit_mode = True
    gs_fns = find_visit_guiding_files(visitid, verbose=verbose)

    # We may have multiple GS filenames returned, in the case where the data is split into several segments
    # If so, concatenate them
    dither_times = []
    last_gs_fn_middle= ''
    for i, gs_fn in enumerate(gs_fns):
        gs_fn_base = os.path.splitext(os.path.basename(gs_fn))[0]

        if i==0:  # For a single file or first segment, just read it in
            # Read the data from that file, and parse into astropy Times
            pointing_table = astropy.table.Table.read(gs_fn, hdu=4)
            centroid_table = astropy.table.Table.read(gs_fn, hdu=5)
            display_gs_fn = os.path.basename(gs_fn)
            # if visit_mode:
            #     # We have to compute means per segment, since it's not meaningful to combine across dithers
            #     mask = centroid_table.columns['bad_centroid_dq_flag'] == 'GOOD'
            #     xmean = np.nanmean(centroid_table[mask]['guide_star_position_x'])
            #     ymean = np.nanmean(centroid_table[mask]['guide_star_position_y'])
            #     centroid_table['guide_star_position_x'] -= xmean
            #     centroid_table['guide_star_position_y'] -= ymean

        else:  # for a later segment, read in and append
            pointing_table_more = astropy.table.Table.read(gs_fn, hdu=4)
            centroid_table_more = astropy.table.Table.read(gs_fn, hdu=5)
            # mark one point as NaN, to visually show a gap in the plot
            centroid_table_more['guide_star_position_x'][-1] = np.nan
            centroid_table_more['guide_star_position_y'][-1] = np.nan
            centroid_table_more['bad_centroid_dq_flag'][-1] = 'GOOD'

            if visit_mode:
                fn_middle = os.path.basename(gs_fn).split('-')[1]
                if fn_middle != last_gs_fn_middle: # New time in file stamp, after a dither and reacq
                    dither_times.append(astropy.time.Time(pointing_table_more.columns['time'][0], format='mjd') )
                    last_gs_fn_middle = fn_middle
                    if verbose:
                        print(f"Dither before {gs_fn} at {dither_times[-1].iso}")
                # # We have to compute means per segment, since it's not meaningful to combine across dithers
                # mask = centroid_table_more.columns['bad_centroid_dq_flag'] == 'GOOD'
                # xmean = np.nanmean(centroid_table_more[mask]['guide_star_position_x'])
                # ymean = np.nanmean(centroid_table_more[mask]['guide_star_position_y'])
                # centroid_table_more['guide_star_position_x'] -= xmean
                # centroid_table_more['guide_star_position_y'] -= ymean

            pointing_table = astropy.table.vstack([pointing_table, pointing_table_more], metadata_conflicts='silent')
            centroid_table = astropy.table.vstack([centroid_table, centroid_table_more], metadata_conflicts='silent')
            display_gs_fn = os.path.basename(gs_fn)[0:33]+ "-seg*_cal.fits"
    if visit_mode:
        display_gs_fn = f"All (n={len(gs_fns)}) guidestar files for {visitid}"

    mask = centroid_table.columns['bad_centroid_dq_flag'] == 'GOOD'

    ctimes = astropy.time.Time(centroid_table['observatory_time'])
    ptimes = astropy.time.Time(pointing_table.columns['time'], format='mjd')

    # Compute the mean X and Y positions
    xmean = np.nanmean(centroid_table[mask]['guide_star_position_x'])
    ymean = np.nanmean(centroid_table[mask]['guide_star_position_y'])

    # Create Plots
    exposure_table = mast.get_visit_exposure_times(visitid)

    fig, ax = plt.subplots(figsize=(12,12))

    prior_xavg = None
    prior_yavg = None

    # Iterate over each exposure, plotting centroids from the time during that exposure
    for row in exposure_table:

        if ignore_ta_exposures:
            if 'TACQ' in row['exp_type'] or 'TACONFIRM' in row['exp_type'] or 'WATA' in row['exp_type']:
                continue

        exp_begin = row['date_beg_mjd']
        exp_end = row['date_end_mjd']
        during_exposure = (exp_begin < ctimes[mask] ) & (ctimes[mask] < exp_end)

        ax.plot(centroid_table[mask][during_exposure]['guide_star_position_x'],
                centroid_table[mask][during_exposure]['guide_star_position_y'],
                marker='+', alpha=alpha,
                label = row['filename'])
        xavg = np.nanmean(centroid_table[mask][during_exposure]['guide_star_position_x'])
        yavg = np.nanmean(centroid_table[mask][during_exposure]['guide_star_position_y'])
        xstd = np.nanstd(centroid_table[mask][during_exposure]['guide_star_position_x'])
        ystd = np.nanstd(centroid_table[mask][during_exposure]['guide_star_position_y'])
        if prior_xavg is not None:
            print(f'\t\t\tdither offset, measured as:\t∆X: {xavg-prior_xavg:.4f}\t\t∆Y: {yavg-prior_yavg:.4f} arcsec')
        print(f'{row["filename"]}:\t X: {xavg:.4f} ± {xstd:.4f}\t Y: {yavg:.4f} ± {ystd:.4f} arcsec')

        prior_xavg = xavg
        prior_yavg = yavg
        ax.errorbar(xavg, yavg, xerr=xstd, yerr=ystd,
                    alpha=0.5, color='black',  zorder=1000,
                )


    leg = ax.legend(fontsize='small')
    try:
        legendhandles = leg.legend_handles  # current matplotlib
    except AttributeError:
        legendhandles = leg.legendHandles  # older, deprecated

    for lh in legendhandles:
        lh.set_alpha(1)

    ax.set_title(f"Guide Star Centroid Positions during {visitid} dithers", fontweight='bold', fontsize=18)
    ax.set_xlabel("FGS X coordinate [arcsec]")
    ax.set_ylabel("FGS Y coordinate [arcsec]")
    ax.set_aspect('equal')

    # set up secondary axes
    xmin, xmax = ax.get_xlim()
    xavg = (xmin + xmax)/2
    ymin, ymax = ax.get_ylim()
    yavg = (ymin + ymax)/2
    x_ideal_to_offset_mas = lambda pos: (pos - xavg)*1000
    x_offset_mas_to_ideal = lambda mas: mas/1000 + xavg
    y_ideal_to_offset_mas = lambda pos: (pos - yavg)*1000
    y_offset_mas_to_ideal = lambda mas: mas/1000 + yavg
    ax_x2 = ax.secondary_xaxis('top', functions=(x_ideal_to_offset_mas, x_offset_mas_to_ideal))
    ax_y2 = ax.secondary_yaxis('right', functions=(y_ideal_to_offset_mas, y_offset_mas_to_ideal))
    ax_x2.set_xlabel("X offset [milliarcsec]")
    ax_y2.set_ylabel("Y offset [milliarcsec]")


    if save:
        outname = f'guiding_dithers_{visitid}.pdf'
        plt.savefig(outname)
        if verbose:
            print(f' ==> {outname}')



def guiding_performance_jitterball(sci_filename, visitid=None, gs_filename=None, fov_size = 8, nbins=50, verbose=True, save=False,
                                   t_beg=None, t_end=None, ax=None):
    """Generate a plot showing the guiding jitter during an exposure


    """
    if gs_filename is None:
        # Retrieve the guiding packet file(s) from MAST
        if visitid:
            visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
            visit_mode = True
            gs_fns = find_visit_guiding_files(visitid, verbose=verbose)
        else:
            visit_mode = False
            gs_fns = find_relevant_guiding_file(sci_filename)

    else:
        gs_fns = [gs_filename, ]
    gs_fn = gs_fns[0]

    # Determine start and end times for the exposure
    if t_beg is None or t_end is None:
        with fits.open(sci_filename) as sci_hdul:
            t_beg = astropy.time.Time(sci_hdul[0].header['DATE-BEG'])
            t_end = astropy.time.Time(sci_hdul[0].header['DATE-END'])

    # We may have multiple GS filenames returned, in the case where the data is split into several segments
    # If so, concatenat them

    for i, gs_fn in enumerate(gs_fns):
        gs_fn_base = os.path.splitext(os.path.basename(gs_fn))[0]

        if i==0:  # For a single file or first segment, just read it in
            # Read the data from that file, and parse into astropy Times
            pointing_table = astropy.table.Table.read(gs_fn, hdu=4)
            centroid_table = astropy.table.Table.read(gs_fn, hdu=5)
            display_gs_fn = os.path.basename(gs_fn)
        else:  # for a later segment, read in and append
            pointing_table_more = astropy.table.Table.read(gs_fn, hdu=4)
            centroid_table_more = astropy.table.Table.read(gs_fn, hdu=5)
            pointing_table = astropy.table.vstack([pointing_table, pointing_table_more], metadata_conflicts='silent')
            centroid_table = astropy.table.vstack([centroid_table, centroid_table_more], metadata_conflicts='silent')
            display_gs_fn = os.path.basename(gs_fn)[0:33]+ "-seg*_cal.fits"


    mask = centroid_table.columns['bad_centroid_dq_flag'] == 'GOOD'

    ctimes = astropy.time.Time(centroid_table['observatory_time'])
    ptimes = astropy.time.Time(pointing_table.columns['time'], format='mjd')

    # Compute the mean X and Y positions
    xmean = centroid_table[mask]['guide_star_position_x'].mean()
    ymean = centroid_table[mask]['guide_star_position_y'].mean()


    # Create Plots
    if ax is None:
        subplot_mode = False
        fig= plt.figure(figsize=(8,8),)


        # Add a gridspec with two rows and two columns and a ratio of 1 to 4 between
        # the size of the marginal axes and the main axes in both directions.
        # Also adjust the subplot parameters for a square plot.
        gs = fig.add_gridspec(2, 2,  width_ratios=(4, 1), height_ratios=(1, 4),
                              left=0.1, right=0.9, bottom=0.1, top=0.9,
                              wspace=0.05, hspace=0.05)
        # Create the Axes.
        ax = fig.add_subplot(gs[1, 0], projection='scatter_density')
        ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
        ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
        # Draw the scatter plot and marginals.
        #scatter_hist(x, y, ax, ax_histx, ax_histy)
    else:
        subplot_mode = True

    min_time = np.min([ptimes.plot_date.min(), ctimes.plot_date.min()])
    max_time = np.max([ptimes.plot_date.max(), ctimes.plot_date.max()])
    dtime = max_time - min_time

    # Find the subset of centroid data from during that exposure
    ptimes_during_exposure = (t_beg < ptimes ) & (ptimes < t_end)
    ctimes_during_exposure = (t_beg < ctimes[mask] ) & (ctimes[mask] < t_end)

    xpos = centroid_table[mask][ctimes_during_exposure]['guide_star_position_x']
    ypos = centroid_table[mask][ctimes_during_exposure]['guide_star_position_y']

    xmean = xpos.mean()
    ymean = ypos.mean()

    rpos = np.sqrt(xpos**2+ypos**2)
    #print(np.std(rpos))

    xoffsets = (xpos-xmean)*1000
    yoffsets = (ypos-ymean)*1000

    xstd = xoffsets.std()
    ystd = yoffsets.std()
    xmean = xoffsets.mean()
    ymean = yoffsets.mean()

    if xstd>fov_size or ystd>fov_size:
        fov_size = max(xoffsets.max(), yoffsets.max())

    if ax.name =='scatter_density':
        # if the axes is set up for this projection, we can use mpl_scatter_density
        scattercmap = utils.colormap_viridis_white_background()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # scatter_density may emit warnings about NaNs; we don't care.
            ax.scatter_density(xoffsets, yoffsets, alpha = 0.8, cmap=scattercmap)
    else:
        # otherwise use regular scatterplot
        ax.scatter(xoffsets, yoffsets, alpha = 0.8, marker='+')
    ax.set_aspect('equal')

    ax.set_xlim(-fov_size/2, fov_size/2)
    ax.set_ylim(-fov_size/2, fov_size/2)
    ax.set_xlabel("GS Centroid Offset X [milliarcsec]", fontsize=9 if subplot_mode else 18)
    ax.set_ylabel("GS Centroid Offset Y [milliarcsec]", fontsize=9 if subplot_mode else 18)


    for rad in [1,2,3]:
        color = 'darkorange' if rad==1 else 'gray'
        ax.add_artist(plt.Circle( (0,0), rad, fill=False, color='darkorange' if rad==1 else 'gray', ls='--'))
        if rad<fov_size/2:
            ax.text(0, rad+0.1, f"{rad} mas", color='black' if rad==1 else 'gray', fontweight='bold' if rad==1 else None)

    if not subplot_mode:
        fig.suptitle(f"Guiding during {os.path.basename(sci_filename)}\n", fontweight='bold', fontsize=12)
        # Draw histograms
        ax_histx.tick_params(axis="x", labelbottom=False)
        ax_histy.tick_params(axis="y", labelleft=False)

        bins = np.linspace(-fov_size/2, fov_size/2, nbins)
        ax_histx.hist(xoffsets, bins=bins)
        ax_histy.hist(yoffsets, bins=bins, orientation='horizontal')

        ax_histx.text(0.5, 0.98, f'mean: {ymean:.3f}\n$\\sigma$: {ystd:.3f}', horizontalalignment='center', verticalalignment='top')
        ax_histy.text(0.02, 0.5, f'mean: {xmean:.3f}\n$\\sigma$: {xstd:.3f}', horizontalalignment='left', verticalalignment='center')
    else:
        #ax.text(0.5, 0.02, f'Y mean: {ymean:.3f}   $\\sigma$: {ystd:.3f}  mas\nX mean: {xmean:.3f}   $\\sigma$: {xstd:.3f}   mas', horizontalalignment='center', verticalalignment='bottom',
        ax.text(0.5, 0.02, f'Y jitter $\\sigma$: {ystd:.3f} mas\nX jitter $\\sigma$: {xstd:.3f} mas', horizontalalignment='center', verticalalignment='bottom',
                transform=ax.transAxes)

    if max(xstd, ystd) > 2:
        ax.text(0.5, 0.98, f'WARNING: Guiding Jitter is\nsignificantly larger than usual!', horizontalalignment='center', verticalalignment='top',
                transform=ax.transAxes, fontweight='bold', color='darkred')



    if save:
        outname = f'guidingjitterball_{gs_fn_base}.pdf'
        plt.savefig(outname)
        if verbose:
            print(f' ==> {outname}')



@functools.cache
def get_siaf_aperture(guidername):
    """Get an FGS SIAF aperture
    With caching since loading SIAF is slow the first time"""
    gid = guidername[-1] # '1' or '2'
    s = pysiaf.Siaf('FGS')
    return s.apertures[f'FGS{gid}_FULL_OSS']  # not sure if the _OSS is needed in this case or not


@functools.cache
def get_visit_contents(visfilename):
    """Load a visit file, with caching since the
    same visit file may be used for several GS ID attempts
    """
    import visitviewer
    return visitviewer.VisitFileContents(visfilename)


def display_one_id_image(filename, destripe = True, smooth=True, ax=None,
                         show_metadata=True, plot_guidestars=True, count=0,
                        orientation='sci', return_model=False,
                         vmax_sigma=None):
    """Display a JWST Guiding ID image

    Displays on a log stretch, optionally with overplotted guide star information if the visit files are available

    Parameters
    ----------
    destripe, smooth : Bool
        should we do some image processing to make the guide stars easier to see in the images

    orientation : 'sci' or 'raw':
        'sci' puts science frame 0,0 at lower left, like MAST output products seen in DS9
        'raw' puts detetor raw frame 0,0 at upper left, like the FGS DHAS tool's plots

    return_model : bool
        Optional, return the image model if you want to do some further image manipulations
        (for efficiency to avoid reloading it multiple times)
    """

    model = jwst.datamodels.open(filename)

    im = model.data[0]

    if ax is None:
        ax = plt.gca()

    if destripe:
        im = im - np.nanmedian(im, axis=0).reshape([1, im.shape[1]])

    if smooth:
        im = scipy.ndimage.median_filter(im, size=3)


    if orientation=='raw':
        # Display like in raw detector orientation, consistent with usage on-board and in FGS DHAS analyses

        if model.meta.instrument.detector=='GUIDER2':
            im = im.transpose()
            im = im[::-1]
        else:
            im = np.rot90(im)
            im = im[:, ::-1] # maybe??
        origin='upper' # Argh, the FGS DHAS diagnostic plots put 0,0 at the UPPER left
    else:
        origin='lower'

    # For bright crowded fields, only part of the FOV has data, surrounded by lots of NaNs
    is_bcf = (np.nansum(im[0:100]) == 0)

    if is_bcf:
        # only compute stats on the part that was read out
        mean, median, sigma = astropy.stats.sigma_clipped_stats(im[672:1372], )
    else:
        mean, median, sigma = astropy.stats.sigma_clipped_stats(im, )

    if vmax_sigma is None:
        vmax_sigma = 50 if is_bcf else 10

    norm = matplotlib.colors.AsinhNorm(vmin = median-sigma, vmax=vmax_sigma*sigma, linear_width=vmax_sigma/5*sigma)

    ax.imshow(im, norm=norm, origin=origin)

    ax.set_title(os.path.basename(filename))
    #ax.xaxis.set_ticks([])
    #ax.yaxis.set_ticks([])

    if show_metadata:
        ax.text(0.01, 0.99, f'{model.meta.instrument.detector}\nGS index: {model.meta.guidestar.gs_order}\n{model.meta.observation.date_beg[:-4]}',
                color='yellow',
                transform=ax.transAxes,
                verticalalignment='top')
        if orientation=='raw':
            ax.text(0.99, 0.99, f'detector raw orientation',
                color='yellow',
                transform=ax.transAxes,
                verticalalignment='top', horizontalalignment='right')


    if plot_guidestars:
        ap = get_siaf_aperture(model.meta.instrument.detector)
        pixscale = (ap.XSciScale + ap.YSciScale)/2

        # 12 arcsec is the new threshold, as of mid 2025
        def add_circle(x,y, radius=12/pixscale/3, color='white',
                           label=None):
                ax.add_patch(matplotlib.patches.Circle( (x,y), radius, edgecolor=color,
                                                       facecolor='none'))
                ax.add_patch(matplotlib.patches.Circle( (x,y), radius*3, edgecolor=color,
                                                       facecolor='none', ls='dotted'))

                if label is not None:
                    ax.text(x, y, label, color=color, fontweight='bold', alpha=0.75)


        visfilename = f'V{model.meta.observation.visit_id}.vst'
        if os.path.exists(visfilename):
            if count==0: print(f'Found visit file {visfilename}')
            vis = get_visit_contents(visfilename)
            if count==0: print("Retrieving and plotting guide star info from visit file")

            gsinfo = vis.guide_activities[model.meta.guidestar.gs_order - 1]

            if orientation=='raw':
                coord_transform = ap.idl_to_det
            else:
                def coord_transform(*args):
                    x,y = ap.idl_to_sci(*args)
                    return  y, model.data.shape[-1]-x  # I don't understand the coord transform and why this flip is needed but it works

            dety, detx = coord_transform(gsinfo.GSXID, gsinfo.GSYID)
            #ax.scatter(detx, dety, s=300, marker='o', color='orange', facecolor='none')

            add_circle(detx, dety, label=f'commanded\nGS candidate {model.meta.guidestar.gs_order }\n',
                       color='orange')

            for ref_id in range(1,10):
                if hasattr(gsinfo, f'REF{ref_id}X'):
                    dety, detx = coord_transform(getattr(gsinfo, f'REF{ref_id}X'),
                                               getattr(gsinfo, f'REF{ref_id}Y'))
                    add_circle(detx, dety,
                               label=f'commanded\nRef {ref_id}\n', color='magenta')

    if return_model:
        return model


def display_one_guider_image(filename,  ax=None, use_dq=False,
                         show_metadata=True, count=0,
                         orientation='sci', return_model=False, cube_slice=None):
    """Display a JWST Guiding Acq image

    Displays on a asinh stretch

    Parameters
    ----------
    orientation : 'sci' or 'raw':
        'sci' puts science frame 0,0 at lower left, like MAST output products seen in DS9
        'raw' puts detetor raw frame 0,0 at upper left, like the FGS DHAS tool's plots

    return_model : bool
        Optional, return the image model if you want to do some further image manipulations
        (for efficiency to avoid reloading it multiple times)

    cube_slice : int
        For TRACK or FG cubes, which slice of the datacube to show
    """

    model = jwst.datamodels.open(filename)


    if model.data.ndim == 3 and 'track' in filename:
        # The star location in track images may move over time, by design.
        # So just take and display one slice here, rather than trying to average over many
        if cube_slice is None:
            cube_slice = 0
        elif cube_slice == -1:
            cube_slice = model.data.shape[0]-1
        im = model.data[cube_slice]
        cubemode = True
        cubelabel = f"frame {cube_slice+1} of {model.data.shape[0]}"
    elif model.data.ndim == 3 and 'track' not in filename:
        # for fine guide images we can average over time, generally  (*small caveat for SGD subpix dithers)
        if cube_slice is None:
            im = model.data.mean(axis=0)
            cubelabel = f"average of {model.data.shape[0]} frames"
        else:
            if cube_slice == -1:
                cube_slice = model.data.shape[0] - 1
            im = model.data[cube_slice]
            cubelabel = f"frame {cube_slice + 1} of {model.data.shape[0]}"

        cubemode = True
    else:
        im = model.data
        cubemode = False
    dq = model.dq

    if ax is None:
        ax = plt.gca()

    if orientation=='raw':
        # Display like in raw detector orientation, consistent with usage on-board and in FGS DHAS analyses
        if model.meta.instrument.detector=='GUIDER2':
            im = im.transpose()
            im = im[::-1]
            dq = dq.transpose()
            dq = dq[::-1]
        else:
            im = np.rot90(im)
            im = im[:, ::-1] # maybe??
            dq = np.rot90(dq)
            dq = dq[:, ::-1]
        origin='upper' # Argh, the FGS DHAS diagnostic plots put 0,0 at the UPPER left

        # Subarray starting coords in DET frame
        startx = model.meta.subarray.detxcor
        starty = model.meta.subarray.detycor
    else:
        origin='lower'
        # Subarray starting coords in SCI frame
        startx = model.meta.subarray.xstart
        starty = model.meta.subarray.ystart


    mean, median, sigma = astropy.stats.sigma_clipped_stats(im, )

    vmax = np.nanmax(im)
    if not vmax > 0:
        print(f"Error, vmax is {vmax}. Overriding to 1e3")
        vmax=1e3
    norm = matplotlib.colors.AsinhNorm(vmin = median-sigma, vmax=vmax, linear_width=vmax/1e3)

    extent = [startx-0.5, startx+im.shape[1]+0.5, starty-0.5, starty+im.shape[0]+0.5]

    ax.imshow(im, norm=norm, origin=origin, extent=extent)

    if use_dq:
        bpmask = np.zeros_like(im, float) + np.nan
        bpmask[(dq & 1)==1] = 1
        ax.imshow(bpmask, vmin=0, vmax=1.5, cmap=matplotlib.cm.inferno, origin=origin, extent=extent)

    ax.set_title(os.path.basename(filename))
    #ax.xaxis.set_ticks([])
    #ax.yaxis.set_ticks([])

    if show_metadata:
        ax.text(0.01, 0.99, f'{model.meta.instrument.detector}\nGS index: {model.meta.guidestar.gs_order}\n{model.meta.observation.date_beg[:-4]}',
                color='yellow',
                transform=ax.transAxes,
                verticalalignment='top')
        ax.text(0.99, 0.99, (f'detector raw orientation' if orientation=='raw' else 'science orientation') +
                                                                                   ("\n"+cubelabel if cubemode else ""),
            color='yellow',
            transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right')

    if return_model:
        return model


def show_all_gs_images(filenames, guidemode='ID', orientation='raw'):
    """Show a set of GS ID/Acq images, notionally all from the same visit

    Displays a grid of plots up to 3x3 for the 3 candidates times 3 attempts each

    Parameters
    ----------
    guidemode : str
        ID, ACQ1, ACQ2, TRACK, or FG
    orientation : str
        'raw' for FGS detector raw coordinates, like OSS on board, or 'sci' for science frame on the ground
    """

    print(f"Found a total of {len(filenames)} {guidemode} images for that observation.")

    ncols= min(3, len(filenames))
    nrows = int(np.ceil(len(filenames)/3))

    print(f'Loading and plotting {guidemode} images...')
    fig, axes = plt.subplots(figsize=(16,6*nrows), nrows=nrows, ncols=ncols,
                            gridspec_kw={'wspace': 0.1,
                                         'left': 0.05,
                                         'right': 0.97,
                                         'top': 0.90,
                                         'bottom': 0.05,
                                         })

    axesf = axes.flatten() if nrows*ncols>1 else [axes,]


    for i, filename in enumerate(filenames):
        if guidemode=='ID':
            display_one_id_image(filename, ax=axesf[i], orientation=orientation, count=i)
        else:
            display_one_guider_image(filename, ax=axesf[i], count=i, orientation=orientation)


        #if np.mod(i,3):
        #    axesf[i].set_yticklabels([])

    for extra_ax in axesf[i+1:]:
        extra_ax.set_axis_off()


def retrieve_and_display_id_images(sci_filename=None, progid=None, obs=None, visit=1, visitid=None, save=True, save_dpi=150):
    """ Top-level routine to retrieve and display FGS ID images for a given visit

    You can specify the visit either by giving a science filename (in which case
    the metadata is read from the header) or directly supplying program ID, observation,
    and optionally visit number.
    """
    # user interface convenience - infer whether the provided string is a visit id automatically
    if sci_filename is not None and sci_filename.startswith('V') and visitid is None:
        visitid = sci_filename
        sci_filename = None

    if visitid is not None:
        visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
        progid = int(visitid[1:6])
        obs = int(visitid[6:9])
        visit = int(visitid[9:12])
    filenames = find_guiding_id_file(sci_filename=sci_filename,
                                                      progid=progid, obs=obs, visit=visit)

    if filenames[0].endswith('uncal.fits'):
        print("Warning, can only find _uncal.fits images in MAST. Guide data not yet processed through pipeline fully. Please try again later")
        print(filenames)
        return

    show_all_gs_images(filenames)
    visit_id = fits.getheader(filenames[0],ext=0)['VISIT_ID']
    fig = plt.gcf()
    fig.suptitle(f"FGS ID in V{visit_id}", fontsize=16, fontweight='bold')

    if save:
        outname = f'V{visit_id}_ID_images.pdf'
        plt.savefig(outname, dpi=save_dpi, transparent=True)
        print(f"Output saved to {outname}")


def retrieve_and_display_guider_images(visitid=None, progid=None, obs=None, visit=1, guidemode='ACQ1', save=True, save_dpi=150):
    """ Top-level routine to retrieve and display FGS Acq/Track/Fine Guide images for a given visit

    You can specify the visit either by giving a science filename (in which case
    the metadata is read from the header) or directly supplying program ID, observation,
    and optionally visit number.

    Parameters
    ----------
    guidemode : str
        'ACQ1' or 'ACQ2' or 'TRACK' or 'FINEGUIDE'
    """
    if visitid is not None:
        visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
        progid = int(visitid[1:6])
        obs = int(visitid[6:9])
        visit = int(visitid[9:12])

    filenames = find_visit_guiding_files(visitid=visitid, guidemode=guidemode,)

    if filenames is None or len(filenames)==0:
        print(f"Warning, could not find any image files for {guidemode} for that observation")
        return

    if filenames[0].endswith('uncal.fits'):
        print("Warning, can only find _uncal.fits images in MAST. Guide data not yet processed through pipeline fully. Please try again later")
        for fn in filenames:
            print("\t"+fn)
        return


    show_all_gs_images(filenames, guidemode=guidemode)
    visit_id = fits.getheader(filenames[0],ext=0)['VISIT_ID']
    fig = plt.gcf()
    fig.suptitle(f"FGS {guidemode} in V{visit_id}", fontsize=16, fontweight='bold')

    if save:
        outname = f'V{visit_id}_{guidemode}_images.pdf'
        plt.savefig(outname, dpi=save_dpi, transparent=True)
        print(f"Output saved to {outname}")


def visit_guider_images(visitid, ):
    """ Retrieve and display to PDF all the guider images in a visit

    See functions retrieve_and_display_id_images and retrieve_and_display_guider_images for further details.
    """
    retrieve_and_display_id_images(visitid=visitid)
    for guidemode in ['ACQ1', 'ACQ2', 'TRACK']:
        retrieve_and_display_guider_images(visitid=visitid, guidemode=guidemode)

    print(f"Outputs saved to {visitid}_*_images.pdf")


def which_guider_used(visitid, guidemode = 'FINEGUIDE'):
    """ Query MAST for which guider was used in a given visit.

    Parameters
    ----------
    visitid : str
        visit ID, like "V01234004001"
    guidemode : str
        Which kind of guide mode to check. Defaults to FINEGUIDE but
        would need to be TRACK for moving targets.
        If FINEGUIDE is specified and no guide files are found, the
        code will now automatically retry using TRACK instead.

    """
    visitid = utils.get_visitid(visitid)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
    progid = (visitid[1:6])  # These must be strings
    obs = (visitid[6:9])
    visit = (visitid[9:12])

    keywords = {
    'program': [progid]
    ,'observtn': [obs]
    ,'visit': [visit]
    ,'exp_type': ['FGS_'+guidemode]
    }

    params = {
    'columns': '*',
    'filters': set_params(keywords)
    }

    # Run the web service query. This uses the specialized, lower-level webservice for the
    # guidestar queries: https://mast.stsci.edu/api/v0/_services.html#MastScienceInstrumentKeywordsGuideStar

    service = 'Mast.Jwst.Filtered.GuideStar'
    t = Mast.service_request(service, params)

    # check the APERNAME which should be either the string FGS1_FULL or FGS2_FULL.
    # All guiding in a visit will use the same guide star, so it's sufficiient to just check the first one
    if len(t) > 0:
        guider_used = t['apername'][0][0:4]
    else:
        guider_used = None

    if guider_used is None and guidemode=='FINEGUIDE':
        # if we can't find any FG, then fail back and try TRACK automatically in case this was a moving target visit
        guider_used = which_guider_used(visitid, guidemode='TRACK')
    return guider_used

def visit_guiding_timeline(visitid):
    """ Print out a timeline of guiding events within a visit
    including exposures and OSS event log messages, and inferred notes on FGS activity success or failure
    """
    guiding_file_table = find_all_visit_guiding_files(visitid, autodownload=False)

    filenames = guiding_file_table['Filename']

    # Retrieve the OSS log messages for that visit
    #visitstart = astropy.io.fits.getheader(filenames[0])['VSTSTART']  # use actual visit start time from header
    logstart = guiding_file_table[0]['Time Start'] - 2*astropy.units.hour  # guess, padded more than enough for slew times
    logstop = guiding_file_table[-1]['Time End'] + 10*astropy.units.minute  # guess
    log = engdb.get_ictm_event_log(startdate=logstart.isot, enddate=logstop.isot)

    # Extract just the OSS log messages for FGS events during that visit
    visit_log_table = engdb.eventtable_extract_visit(log, visitid, verbose=False)
    fgs_log_table = visit_log_table[[('FGS' in m)  for m in visit_log_table['Message']]]

    # Cast Time column to astropy Time object
    fgs_log_table['Time'] = astropy.time.Time(fgs_log_table['Time'] )

    ### Iterate over files and OSS log messages to print in an interspersed sequence

    current_attitude_state = None
    detected_dither = False

    i_time = 0

    for i in range(len(guiding_file_table)):
        fn = filenames[i]
        try:
            next_fn = filenames[i+1]
        except IndexError:
            next_fn = '_none_'
        time = guiding_file_table[i]['Time Start']


        _, this_step, _ = fn.split('_', maxsplit=2)
        _, next_step, _ = next_fn.split('_', maxsplit=2)

        # Simple logic to check through the flow of activities and see if it looks as it should
        # for nominal successful guiding, or not.
        # CAVEAT: Probably needs more checking and logic for edge cases. Doesn't handle moving targets yet
        if this_step=='gs-id':
            if next_step=='gs-acq1':
                msg = f"FGS ID on GS try {fn[20]} successful"  # TODO update logic for GS ID, actually this will count from 1 to 9
                current_attitude_state = 'ID'
            else:
                msg = "FGS ID failed"
        elif this_step=='gs-acq1':
            if next_step=='gs-acq2':
                msg = f"Acq1 at {current_attitude_state} attitude successful"
            else:
                msg = "Acq1 failed"
        elif this_step=='gs-acq2':
            if current_attitude_state=='ID':  # acq2 at ID attitude should be followed by Acq1 at Sci attitude
                if next_step=='gs-acq1':
                    msg = f"Acq2 at {current_attitude_state} attitude successful"
                    current_attitude_state = 'Sci'
                else:
                    msg = "Acq2 failed"
            elif current_attitude_state in ['Sci', 'dither'] :  # acq2 at Sci or dither attitude should be followed by Track
                if next_step=='gs-track':
                    msg = f"Acq2 at {current_attitude_state} attitude successful"
                else:
                    msg = "Acq2 failed"

        elif this_step=='gs-track':
            if next_step=='gs-fg':
                msg = f"Track successful"
        elif this_step=='gs-fg':
            _, prev_step, _ = filenames[i-1].split('_', maxsplit=2)
            if prev_step != 'gs-fg':
                msg = 'Fine Guide started'
            else:
                msg = " ... FG continued"
            if next_step != 'gs-fg' and i != len(filenames)-1:
                detected_dither = True
                current_attitude_state = 'dither'
        else:
            msg = ""

        # Print any OSS log messages that occurred before this image
        while(fgs_log_table[i_time]['Time'].iso < time):
            print(f"{fgs_log_table[i_time]['Time'].iso}    OSS: {fgs_log_table[i_time]['Message']}")
            i_time += 1

        print(f"{time.iso}\t\t{msg:35s}\t{fn:50s}")

        if detected_dither:
            print(f"{guiding_file_table[i]['Time End'].iso}\t\t--Stop FG, for Dither move--")
            detected_dither = False

        prev_step=this_step

    # Print any remaining messages at the end
    while(i_time < len(fgs_log_table)):
        print(f"{fgs_log_table[i_time]['Time'].iso}\t   OSS: { fgs_log_table[i_time]['Message']}")
        i_time += 1


def _which_si_from_filenames(filenames_list):
    """ Minor utility function to infer which SI was used in a given viist, based on filenames
    """
    si_filename_strs = {'MIRI': 'mir', 'NIRCAM':'nrc', 'NIRISS':'nis', 'NIRSPEC':'nrs'}
    for si in si_filename_strs:
        if si_filename_strs[si] in filenames_list[0]:
            return si
    return None

def visit_guiding_sequence(visitid, verbose=True, include_performance=True):
    """ Plot complete image sequence of guiding events within a visit
    including exposures and OSS event log messages, and inferred notes on FGS activity success or failure

    This is a high-level function that invokes much of the other code in this submodule.
    """
    try:
        import mpl_scatter_density  # adds projection='scatter_density'
        HAS_MPL_SCATTER_DENSITY = True
    except ImportError:
        HAS_MPL_SCATTER_DENSITY = False


    visitid = utils.get_visitid(visitid)  # handle either input format

    # Retrieve guider exposure filenames and times
    print(f"Retrieving guiding files for {visitid}")
    guiding_file_table = find_all_visit_guiding_files(visitid, autodownload=True)

    if (guiding_file_table is None) or len(guiding_file_table) == 0:
        raise RuntimeError("No guiding files found in MAST for that visit")

    filenames = guiding_file_table['Filename']

    # Retrieve science exposure filenames and times
    exposure_table = mast.get_visit_exposure_times(visitid, extra_columns=True)
    if exposure_table is None:
        which_si = "UNKNOWN (no science files found in MAST for that visit)"
    else:
        exposure_table.sort(['date_beg_mjd', 'filename'])
        which_si = _which_si_from_filenames(exposure_table['filename'])
    print("That visit used "+which_si)

    # Retrieve the OSS log messages for that visit
    # visitstart = astropy.io.fits.getheader(filenames[0])['VSTSTART']  # use actual visit start time from header
    logstart = guiding_file_table[0][
                   'Time Start'] - 2 * astropy.units.hour  # guess, padded more than enough for slew times
    logstop = guiding_file_table[-1]['Time End'] + 10 * astropy.units.minute  # guess

    log = engdb.get_ictm_event_log(startdate=logstart.isot, enddate=logstop.isot)

    # Extract just the OSS log messages for FGS events during that visit
    visit_log_table = engdb.eventtable_extract_visit(log, visitid, verbose=False)
    fgs_log_table = visit_log_table[[('FGS' in m) for m in visit_log_table['Message']]]

    # Cast Time column to astropy Time object
    fgs_log_table['Time'] = astropy.time.Time(fgs_log_table['Time'])

    ### Iterate over files and OSS log messages to print in an interspersed sequence

    current_attitude_state = None
    detected_dither = False

    i_time = 0

    outname = f'guiding_sequence_{visitid}.pdf'
    with PdfPages(outname) as pdf:

        for i in range(len(guiding_file_table)):
            fn = filenames[i]
            try:
                next_fn = filenames[i + 1]
            except IndexError:
                next_fn = '_none_'
            time = guiding_file_table[i]['Time Start']
            time_end = guiding_file_table[i]['Time End']

            _, this_step, _ = fn.split('_', maxsplit=2)
            _, next_step, _ = next_fn.split('_', maxsplit=2)

            # Simple logic to check through the flow of activities and see if it looks as it should
            # for nominal successful guiding, or not.
            # CAVEAT: Probably needs more checking and logic for edge cases. Doesn't handle moving targets yet
            if this_step == 'gs-id':
                if next_step == 'gs-acq1':
                    msg = f"FGS ID on GS try {fn[20]} successful"  # TODO update logic for GS ID, actually this will count from 1 to 9
                    current_attitude_state = 'ID'
                else:
                    msg = "FGS ID failed"
            elif this_step == 'gs-acq1':
                if next_step == 'gs-acq2':
                    msg = f"Acq1 at {current_attitude_state} attitude successful"
                else:
                    msg = "Acq1 failed"
            elif this_step == 'gs-acq2':
                if current_attitude_state == 'ID':  # acq2 at ID attitude should be followed by Acq1 at Sci attitude
                    if next_step == 'gs-acq1':
                        msg = f"Acq2 at {current_attitude_state} attitude successful"
                        current_attitude_state = 'Sci'
                    else:
                        msg = "Acq2 failed"
                elif current_attitude_state in ['Sci',
                                                'dither']:  # acq2 at Sci or dither attitude should be followed by Track
                    if next_step == 'gs-track':
                        msg = f"Acq2 at {current_attitude_state} attitude successful"
                    else:
                        msg = "Acq2 failed"

            elif this_step == 'gs-track':
                if next_step == 'gs-fg':
                    msg = f"Track successful"
            elif this_step == 'gs-fg':
                _, prev_step, _ = filenames[i - 1].split('_', maxsplit=2)
                if prev_step != 'gs-fg':
                    msg = 'Fine Guide started'
                else:
                    msg = " ... FG continued"
                if next_step != 'gs-fg' and i != len(filenames) - 1:
                    detected_dither = True
                    current_attitude_state = 'dither'
            else:
                msg = ""

            #----- Annotate FGS exposure times and OSS log messages.
            msgstack = ""
            # Print any OSS log messages that occurred before this image
            while (fgs_log_table[i_time]['Time'].iso < time):
                msgstack += f"{fgs_log_table[i_time]['Time'].iso}    OSS: {fgs_log_table[i_time]['Message']}\n"
                i_time += 1
            msgstack += f"{time.iso} FGS Exposure Start\n"
            if this_step != 'gs-fg':
                # for ID, Acq, Track print the exp end time before the success/fail message
                msgstack += f"{time_end.iso} FGS Exposure End\n"

            msgstack += "\n" + msg + "\n\n"

            if this_step == 'gs-fg':
                # for FG print the exp end time after the success/fail message
                # todo, also do this for moving target visits too, which stay in track
                msgstack += f"{time_end.iso} FGS Exposure End\n"

            if detected_dither:
                msgstack += f"\nFine Guide stopped, for Dither move.\n"
                detected_dither = False
            elif i == len(guiding_file_table) - 1:
                # Print any remaining messages at the end
                while (i_time < len(fgs_log_table)):
                    msgstack += f"{fgs_log_table[i_time]['Time'].iso}   OSS: {fgs_log_table[i_time]['Message']}\n"
                    i_time += 1

            #------ Display the current image
            gskw = {'left': 0.05, 'right': 0.99, 'bottom': 0.1, 'top': 0.95}

            if this_step == 'gs-id':
                fig, axes = plt.subplots(figsize=(16, 9), ncols=2, gridspec_kw=gskw)
                axes[1].set_visible(False)
                display_one_id_image(fn, ax=axes[0], count=i, orientation='raw')

            elif this_step.startswith('gs-acq'):
                fig, axes = plt.subplots(figsize=(16, 9), ncols=2, gridspec_kw=gskw)
                axes[1].set_visible(False)
                display_one_guider_image(fn, ax=axes[0], count=i, orientation='raw')
            else:
                fig, axes = plt.subplots(figsize=(16, 9), ncols=2, nrows=2, gridspec_kw=gskw)
                axes[0, 1].set_visible(False)
                if this_step == 'gs-track':
                    axes[1, 1].set_visible(False)
                elif this_step == 'gs-fg' and HAS_MPL_SCATTER_DENSITY:
                    # special case, replace the axis with one configured to use scatter-density "projection"
                    # can't change the projection of an existing axes, so we have to replace it.
                    axes[1, 1].remove()
                    axes[1, 1] = fig.add_subplot(224, projection='scatter_density')

                display_one_guider_image(fn, ax=axes[0, 0], count=i, orientation='raw', cube_slice=0)
                display_one_guider_image(fn, ax=axes[1, 0], count=i, orientation='raw', cube_slice=-1)

            fig.text(0.5, 0.84, msgstack, verticalalignment='top')
            if i == 0:
                fig.suptitle(f"Guiding Image Sequence during {visitid}", fontsize=20, fontweight='bold')

            #----- Annotate science exposure times and filenames
            #      and accumulate sci exp times for possible use in jitterball plots during FG, below
            already_plotted_exptimes_start = set()
            if exposure_table is not None:
                this_guide_subset = (exposure_table['date_beg_mjd'] > time) & (exposure_table['date_end_mjd'] < time_end)

                sci_file_stack = ""
                already_plotted_exptimes_end = set()
                for row in exposure_table[this_guide_subset]:
                    if row['date_beg_mjd']in already_plotted_exptimes_start:
                        continue
                    sci_file_stack += f"{row['date_beg_mjd'].isot}   {row['filename'][0:25]}    {row['exp_type']}, {row['optical_elements']}, {row['effexptm']:.1f} s\n"
                    already_plotted_exptimes_start.add(row['date_beg_mjd'])
                    already_plotted_exptimes_end.add(row['date_end_mjd'])
                if sci_file_stack != "":
                    sci_file_stack = "Science exposures during this guide:\n\n"+sci_file_stack
                fig.text(0.5, 0.60, sci_file_stack, verticalalignment='top', color='darkgreen')

            # Display jitterball for FG images.
            # Do this after the sci image listing
            if this_step.startswith('gs-fg'):

                print(fn)
                # For some reason this is not working as intended. Problematic t_start /t_end metadata on some files??
                if  len(already_plotted_exptimes_start) >0:
                    jitter_t_beg = min(list(already_plotted_exptimes_start))
                    jitter_t_end = max(list(already_plotted_exptimes_end))
                    # print(f'setting jitterball times for {fn} from sci exp: {jitter_t_beg.mjd}, {jitter_t_end}')
                    jit_title = "LOS measurements during those science exposures"
                else:
                    jitter_t_beg = time
                    jitter_t_end = time_end
                    #print(f'setting jitterball times from entire FG file: {jitter_t_beg}, {jitter_t_end}')
                    jit_title = "LOS measurements during this entire fine guide"
                guiding_performance_jitterball(None, gs_filename=fn, visitid=visitid, t_beg=jitter_t_beg, t_end=jitter_t_end, ax=axes[1,1])
                axes[1,1].set_title(jit_title)


            pdf.savefig(fig)
            plt.close(fig)

            prev_step = this_step

        if include_performance and exposure_table is not None:
            guiding_performance_plot(visitid=visitid)
            pdf.savefig(plt.gcf())
            # pdf.savefig(plt.gcf())
            # guiding_performance_dithers_plot(visitid=visitid)
            # pdf.savefig(plt.gcf())

    print("Output to " + outname)


def retrieve_visit_dither_sams(visitid):
    """ Retrieve a table of dither SAMs in a given visit

    Parameters
    ----------
    visitid : str
        Visit ID, like 'V01234005006' or '1234:5:6'

    Returns astropy Table with fields TIME, SAM_DX, SAM_DY.
    The SAMs are given in units of arcseconds, specified in the FGSx_FULL_OSS frame for
    whichever guider was used in that visit. Call which_guider_used() to check that if needed.
    """
    MSGID_DITHER_SAM = 8232

    msg_table = engdb.get_oss_log_messages(visitid)
    msg_table_sams = engdb.filter_oss_log_messages_by_id(msg_table, MSGID_DITHER_SAM)

    def get_sam_xy(message):
        """ Given an OSS log message like 'TA SAM = 1.234, 5.679' extract the 2 numeric values as floats

        Returns a tuple with the x, y values
        """
        # take the last 2 entries in the line. Strip any punctuation in 'x, y' or '(x, y)'. Cast to floats
        return tuple( [float(m.strip(',()')) for m in message.split()[-2:] ])

    sams = np.asarray([get_sam_xy(row['EVENT_MSG']) for row in msg_table_sams])

    sam_table = Table([msg_table_sams['TIME'], sams.transpose()[0]*astropy.units.arcsec, sams.transpose()[1]*astropy.units.arcsec],
                      names = ['TIME', 'SAM_DX', 'SAM_DY'])

    return sam_table

#-------- Guide star catalog queries

def query_gsc_by_id(gsid, gscversion='GSC32'):
    """ Query Guide Star Catalog, by GS ID

    See https://outerspace.stsci.edu/display/MASTDATA/Catalog+Access

    Returns astropy table
    """

    query_gsc_url = f'https://gsss.stsci.edu/webservices/vo/CatalogSearch.aspx?CATALOG={gscversion}&id={gsid}&FORMAT=CSV'
    with urlopen(query_gsc_url) as u:
        s = BytesIO(u.read())
    return  astropy.table.Table.read(s, format='csv', comment='#')

def query_gsc_conesearch(ra_deg, dec_deg, radius=1*astropy.units.arcsec, gscversion='GSC32'):
    """ Query Guide Star Catalog, by position on the sky

    See https://outerspace.stsci.edu/display/MASTDATA/Catalog+Access

    Returns astropy table
    """

    query_gsc_url = f'https://gsss.stsci.edu/webservices/vo/CatalogSearch.aspx?RA={ra_deg}&DEC={dec_deg}&SR={radius.to_value(astropy.units.deg)}&FORMAT=CSV'
    with urlopen(query_gsc_url) as u:
        s = BytesIO(u.read())
    return  astropy.table.Table.read(s, format='csv', comment='#')
