import functools
import os

import numpy as np

import astropy, astropy.table
import astropy.units as u

import astroquery
from astroquery.mast import Mast
from astroquery.mast import Observations
import requests

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

from tqdm import tqdm

from jwql.instrument_monitors.common_monitors.ta_monitor import utils


__all__ = ['jwst_keywords_query']

def set_params(parameters):
    """
    Utility function for making dicts used in MAST queries.

    """
    return [{'paramName': p, 'values': v} for p, v in parameters.items()]


def jwst_keywords_query(instrument, columns=None, all_columns=False, verbose=False,  **kwargs):
    """JWST keyword query

    See https://mast.stsci.edu/api/v0/_jwst_inst_keywd.html for keyword field reference

    For more examples of using this API, see also:
      https://spacetelescope.github.io/mast_notebooks/notebooks/JWST/SI_keyword_exoplanet_search/SI_keyword_exoplanet_search.html

    Parameters
    ----------
    instrument : str
        Instrument name like "NIRCam" or "MIRI"
    columns : str
        single string with comma-separated list of columns to include in the query, like "filename, program, observtn, apername"


    Query Syntax Guide
    ------------------
    To set a SET of values, set some parameter to a list
        filter = ['F200W', 'F212N']
    To set a RANGE of values, set some parameter to a dict with min and max
        date_obs_mjd = {'min': 60000.1, 'max': 61000.5}

    """
    svc_table = {'MIRI':'Mast.Jwst.Filtered.Miri',
                 'NIRCAM': 'Mast.Jwst.Filtered.NIRCam',
                 'NIRSPEC': 'Mast.Jwst.Filtered.NIRSpec',
                 'NIRISS': 'Mast.Jwst.Filtered.NIRISS',
                }

    service = svc_table[instrument.upper()]

    if columns is None:
        columns = 'filename, program, observtn, visit_id, category, template, exp_type, vststart_mjd, visitend_mjd, bstrtime, dataURI'

    keywords = dict()

    for kw in kwargs:
        val = kwargs[kw]
        if isinstance(kwargs[kw], list):
            # query parameters must be of string type, not ints or other numeric types
            query_val = [str(v) for v in kwargs[kw]]
        elif isinstance(kwargs[kw], dict):
            # some queries, e.g. ranges with min and max, must be specified as a dict, inside a list
            query_val = [kwargs[kw],]
        else:
            # and any scalar parameters should be implicitly wrapped into a list
            query_val = [str(kwargs[kw]),]

        keywords[kw] = query_val

    parameters = {'columns': '*' if all_columns else columns,
                  'filters': set_params(keywords)}
    if verbose:
        print("MAST query parameters:")
        print(parameters)

    responsetable = Mast.service_request(service, parameters)
    if verbose:
        print(f"Query returned {len(responsetable)} rows")
    if 'bstrtime' in columns:
        responsetable.sort(keys='bstrtime')


    # Some date fields are returned (for database format reasons) as strings, containing 'Date' then an integer
    # giving Unix time in milliseconds. Convert these to astropy times.
    # This format is not clearly documented, but was reported by MAST archive help desk.
    date_fields = ['date_beg', 'date_end', 'date_obs', 'publicReleaseDate', 'vststart']   # This is probably not a complete list of which fields to apply this to
    for field_name in date_fields:
        if field_name in responsetable.colnames :
            unix_date_strings = [s[6:-2] for s in responsetable[field_name].value] #  these are strings like '/Date(1679095623534)/'; extract just the numeric part
            times = astropy.time.Time(np.asarray(unix_date_strings, float)/1000, format='unix')
            times.format = 'iso'
            responsetable[field_name] = astropy.table.Column(times)


    # Add the initial V to visit ID.
    if 'visit_id' in columns:
        responsetable['visit_id'] = astropy.table.Column(responsetable['visit_id'], dtype=np.dtype('<U12'))

    if 'vststart_mjd' in columns:
        try:
            responsetable.add_column(astropy.table.Column(astropy.time.Time(responsetable['vststart_mjd'], format='mjd').iso, dtype=np.dtype('<U16')),
                            # index=1,
                            name='visit start time')
        except ValueError:
            pass # For some reason something in that column couldn't be cast to an astropy.Time object

    return responsetable


def visit_which_instrument(visitid):
    """Which instrument did a visit use?

    Note, does not (yet?) handle parallels in a good way. Just returns at most 1 instrument
    """
    visitid = utils.get_visitid(visitid)  # handle either input format
    program = visitid[1:6]

    from astroquery.mast import Observations
    obs = Observations.query_criteria(obs_collection=["JWST"], proposal_id=[program])
    # Annoyingly, that query interface doesn't return start/end times
    instruments = [val.split('/')[0] for val in set(obs['instrument_name'])]

    # TODO - check more carefully for cases with multiple instruments in parallel
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')  # Because we expect at least some of these may have a warning about no results found
        for inst in instruments:
            if len(jwst_keywords_query(inst, visit_id=visitid[1:])) > 0:
                return inst


def query_visit_time(visitid, verbose=False):
    """ Find start and end time of a visit

    Input: string visit id, like 'V01234005001' or '1234:5:1'
    Returns start and end time as astropy.time.Time instances, or Nones.
    """

    visitid = utils.get_visitid(visitid)  # Handle either allowed format of visit ID

    # Get table of times for all visits in that program
    program = visitid[1:6]
    visit_times = query_program_visit_times(program, verbose=verbose)

    #  Scan through the table for a row matching that visit id
    for vid, vstart, vend, inst in visit_times:
        if verbose:
            print(vid, visitid, vid==visitid, inst)
        if vid==visitid:
            # Return times as astropy Time objects
            t0 = astropy.time.Time(vstart, format='mjd')
            t1 = astropy.time.Time(vend, format='mjd')
            t0.format = 'iso'
            t1.format = 'iso'
            return t0, t1
    else:
        return None, None


def get_visit_exposure_times(visitid, extra_columns=""):
    """ Return a table with start and end times for all exposures within a visit"""
    visitid = utils.get_visitid(visitid)  # handle either input format
    inst = visit_which_instrument(visitid)

    if inst is None:
        print(f"warning, no science data in MAST for visit {visitid}")
        return None

    # Set some extra keywords per instrument
    if extra_columns:
        inst_mode_columns = {'NIRCAM': "filter,pupil",
                             'NIRISS': "filter,pupil",
                             'NIRSPEC': 'filter,grating',
                             'MIRI': 'filter,detector,band'}
        extra_query_columns = ", "+inst_mode_columns[inst]
    else:
        extra_query_columns = ""

    res = jwst_keywords_query(inst, visit_id=visitid[1:],
                                       columns = 'filename, visit_id, date_beg_mjd, date_end_mjd, vststart_mjd, visitend_mjd, productLevel, exp_type, effexptm' + extra_query_columns)
    for colname in ['date_beg_mjd', 'date_end_mjd', 'vststart_mjd', 'visitend_mjd']:
        times = astropy.time.Time(res[colname], format='mjd')
        times.format='iso'
        res[colname] = times
    res.sort('date_beg_mjd')

    exps_level2 = res[np.asarray(res['productLevel'].value) != '3']
    # mask out some redundant files
    fns = exps_level2['filename']
    ignore_derived_products_mask = [('s3d' not in fn) and ('x1d' not in fn) and ('i2d' not in fn) for fn in fns]
    exps_level2  = exps_level2[ignore_derived_products_mask]

    if extra_columns:
        keys = inst_mode_columns[inst].split(',')
        exps_level2['optical_elements'] = ["+".join([str(row[k]) for k in keys])  for row in exps_level2]

        # improve handling for MIRI MRS & imager exps, each of which has some missing masked field
        if inst=='MIRI':
            exps_level2['optical_elements'] = [v.replace('+MIRIMAGE+--', '').replace('--+', '') for v in exps_level2['optical_elements']]


    return exps_level2


get_visit_start_end_times = query_visit_time # synonym, for API consistency


def query_program_visit_times(program,  verbose=False):
    """ Get the start and end times of all completed visits in a program.

    See also visit_start_end_times for a specifc named visit..

    Parameters
    ----------
    program : int or str
        Program ID
    verbose : bool
        be more verbose in output?

    Returns astropy Table with columns for visit ID and start and end times.
    """

    # use Observations query interface to find all observations
    from astroquery.mast import Observations
    obs = Observations.query_criteria(obs_collection=["JWST"], proposal_id=[program])

    # Annoyingly, that query interface doesn't return start/end times,
    # therefore we have to separately call a different query interface for those, per instrument
    instruments = [val.split('/')[0] for val in set(obs['instrument_name'])]
    visit_times = []
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')  # Because we expect at least some of these may have a warning about no results found
        for inst in instruments:
            if verbose:
                print(f"querying for visits using {inst}")
            visit_times += _query_program_visit_times_by_inst(program, inst)

    # Format outputs
    vids = [v[0] for v in visit_times]
    starts =astropy.time.Time([float(v[1]) for v in visit_times], format='mjd')
    ends = astropy.time.Time([float(v[2]) for v in visit_times], format='mjd')
    insts = [v[3] for v in visit_times]
    vis_table =  astropy.table.Table([vids, starts, ends, insts],
                                     names=('visit_id', 'start_mjd', 'end_mjd', 'instrument'))
    vis_table.sort(keys='start_mjd')
    return vis_table

def visit_start_end_times(visit):
    """Get start and end times for a specified visit, from MAST metadata.

    See also query_program_visit_times for all visits in a program.

    Parameters
    ----------
    visit : str
       Visit ID. either like 'V01234001001' or '1234:1:1'

    Returns
    --------
    tuple of  (start_time, end_time) as astropy.Time objects
    """

    # Method 1: Try querying science exposures, then get visit start and end metadata
    # THis handles the typical case for guided science obs, and also internal unguided obs such as flats

    exps = mast.get_visit_exposure_times(visit)
    if exps is not None:
        return exps[0]['vststart_mjd'], exps[0]['visitend_mjd']

    # Method 2: No science instrument data taken, therefore try guider exposures
    # This handles the case of observations which failed guider ID and took no science image data.

    visitid = utils.get_visitid(visit)  # handle either input format, VPPPPPOOOVVV or PPPP:O:V
    progid = visitid[1:6]
    obs = visitid[6:9]
    exp_type = 'FGS_ID-IMAGE'

    # Set up the query
    keywords = {'program': [progid] ,'observtn': [obs]}
    params = {
        'columns': 'filename, vststart_mjd, visitend_mjd',
        'filters': set_params(keywords)
    }

    # Run the web service query. This uses the specialized, lower-level webservice for the
    # guidestar queries: https://mast.stsci.edu/api/v0/_services.html#MastScienceInstrumentKeywordsGuideStar
    service = 'Mast.Jwst.Filtered.GuideStar'
    t = Mast.service_request(service, params)

    tstart, tend = astropy.time.Time(t[0]['vststart_mjd'], format='mjd'), astropy.time.Time(t[0]['visitend_mjd'], format='mjd')
    tstart.format = tend.format = 'iso'
    return tstart, tend



def _query_program_visit_times_by_inst(program, instrument, verbose=False):
    """ Get the start and end times of all completed visits in a program, per instrument.
    Not intended for general use; this is mostly a helper to query_program_visit_times.

    Getting the vststart_mjd and visitend_mjd fields requires using the instrument keywords
    interface, so one has to specify which instrument ahead of time.

    Parameters
    ----------
    program : int or str
        Program ID
    instrument : str
        instrument name
    verbose : bool
        be more verbose in output?

    returns list of (visitid, start, end) tuples.

    """

    from astroquery.mast import Mast
    svc_table = {'MIRI':'Mast.Jwst.Filtered.Miri',
                 'NIRCAM': 'Mast.Jwst.Filtered.NIRCam',
                 'NIRSPEC': 'Mast.Jwst.Filtered.NIRSpec',
                 'NIRISS': 'Mast.Jwst.Filtered.NIRISS',
                 'FGS': 'Mast.Jwst.Filtered.FGS',
                }

    service = svc_table[instrument.upper()]

    collist = 'filename, program, observtn, visit_id, vststart_mjd, visitend_mjd, bstrtime'
    all_columns = False

    def set_params(parameters):
        return [{"paramName" : p, "values" : v} for p, v in parameters.items()]


    keywords = {'program': [str(program),]}
    parameters = {'columns': '*' if all_columns else collist,
                  'filters': set_params(keywords)}

    if verbose:
        print("MAST query parameters:")
        print(parameters)

    responsetable = Mast.service_request(service, parameters)
    if 'bstrtime' in collist:
        responsetable.sort(keys='bstrtime')

    visit_times = []
    for row in responsetable:
        visit_times.append( ('V'+row['visit_id'], row['vststart_mjd'], row['visitend_mjd'], instrument))

    visit_times= set(visit_times)
    return list(visit_times)


def summarize_jwst_observations(targname, radius='30s', exclude_ta=True):
    """Search MAST for JWST obs of a target, in all modes, including upcoming approved planned observations

    Returns a nested dictionary, ordered by instrument_mode, then program ID, then filter

    Parameters
    ----------
    targname : str
        target name, for SIMBAD coords query
    radius : str
        cone search radius, as a string with units parsable by astropy.coordinates
    exclude_ta : bool
        should Target Acquisition exposures be excluded from the results?
    """

    obstable = Observations.query_criteria(
            obs_collection='JWST',
            objectname=targname,
            radius=radius
            )

    has_obs = dict()

    for row in obstable:
        mode = row['instrument_name']
        filters = str(row['filters'])
        proposal = row['proposal_id']
        if exclude_ta and '/TA' in mode:
            continue

        if mode not in has_obs:
            has_obs[mode] = dict()
        if proposal not in has_obs[mode]:
            has_obs[mode][proposal] = set()
        has_obs[mode][proposal].add(filters)

    sorted_results_dict = dict(sorted(has_obs.items()))
    return sorted_results_dict


def retrieve_files(filenames, out_dir='.', verbose=True):
    """Download one or more JWST data products from MAST, by filename

    If the file is already present in the specified local directory, it's not downloaded again.

    Note, this function DOES support using a MAST_API_TOKEN to retrieve proprietary data

    """

    mast_url='https://mast.stsci.edu/api/v0.1/Download/file'
    uri_prefix = 'mast:JWST/product/'

    outputs = []

    mast_api_token = os.environ.get('MAST_API_TOKEN')
    if mast_api_token is not None:
        headers=dict(Authorization=f"token {mast_api_token}")
    else:
        headers=None

    for p in tqdm(filenames):
        outfile = os.path.join(out_dir, p)

        if os.path.isfile(outfile):
            if verbose:
                print("ALREADY DOWNLOADED: ", outfile)
            outputs.append(outfile)
            continue

        r = requests.get(mast_url, params=dict(uri=uri_prefix+p), stream=True,
                    # include the following argument if authentication is needed
                    #headers=dict(Authorization=f"token {mast_api_token}"))
                         headers=headers,
                        )
        r.raise_for_status()
        with open(outfile, 'wb') as fd:
            for data in r.iter_content(chunk_size=1024000):
                fd.write(data)

        if not os.path.isfile(outfile):
            if verbose:
                print("ERROR: " + outfile + " failed to download.")
        else:
            if verbose:
                print("COMPLETE: ", outfile)
            outputs.append(outfile)
    return outputs

mast_retrieve_files = retrieve_files # back compatibility
download_files = retrieve_files # Name alias for convenience



def get_mast_filename(filename, outputdir='.',
                      overwrite=False, exists_ok=True,
                      progress=False, verbose=True,
                      return_in_memory=False,
                      mast_api_token=None):
    """Download any specified filename from MAST, writing to outputdir

    If a file exists already, default is to not download.
    Set overwrite=True to overwrite existing output file.
    or set exists_ok=False to raise ValueError.

    Set progress=True to show a progress bar.

    verbose toggles on/off minor informative text output

    return_in_memory returns the file directly as a variable, without writing to disk at all.

    Other parameters are less likely to be useful:
    Default mast_api_token comes from MAST_API_TOKEN environment variable.

    Adapted from example code originally by Rick White, STScI, via archive help desk.
    """

    if not mast_api_token:
        mast_api_token = os.environ.get('MAST_API_TOKEN')
        if mast_api_token is None:
            raise ValueError("Must define MAST_API_TOKEN env variable or specify mast_api_token parameter")
    assert '/' not in filename, "Filename cannot include directories"

    mast_url = "https://mast.stsci.edu/api/v0.1/Download/file"

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
    elif not os.path.isdir(outputdir):
        raise ValueError(f"Output location {outputdir} is not a directory")
    elif not os.access(outputdir, os.W_OK):
        raise ValueError(f"Output directory {outputdir} is not writable")

    if return_in_memory:
        import tempfile
        file_open_func = functools.partial(tempfile.NamedTemporaryFile, mode='wb', delete=False )
        outfile = 'temporary file in memory'
    else:
        outfile = os.path.join(outputdir, filename)
        file_open_func = functools.partial(open, outfile, mode='wb')
    if (not overwrite) and os.path.exists(outfile):
        if exists_ok:
            if verbose:
                print(" ALREADY DOWNLOADED: "+outfile)
            return
        else:
            raise ValueError(f"{outfile} exists, not overwritten")

    r = requests.get(mast_url, params=dict(uri=f"mast:JWST/product/{filename}"),
                     headers=dict(Authorization=f"token {mast_api_token}"), stream=True)
    r.raise_for_status()

    total_size_in_bytes = int(r.headers.get('content-length', 0))
    block_size = 1024000
    if progress:
        progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
        csize = 0
    with file_open_func() as fd:
        for data in r.iter_content(chunk_size=block_size):
            fd.write(data)
            if progress:
                # use the size before uncompression
                dsize = r.raw.tell()-csize
                progress_bar.update(dsize)
                csize += dsize
    if progress:
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")
    if verbose:
        print(" DOWNLOAD SUCCESSFUL: "+outfile)
    return fd


#----- Summarizing available & planned JWST observations from metadata:


@functools.cache
def summarize_jwst_observations(targname, radius='10s', exclude_ta=True):
    """Search MAST for JWST obs of a target, in all modes, including upcoming approved planned observations

    Returns a nested dictionary, ordered by instrument_mode, then program ID, then filter

    Parameters
    ----------
    targname : str
        target name, for SIMBAD coords query
    radius : str
        cone search radius, as a string with units parsable by astropy.coordinates
    exclude_ta : bool
        should Target Acquisition exposures be excluded from the results?
    """

    obstable = Observations.query_criteria(
            obs_collection='JWST',
            objectname=targname,
            radius=radius
            )

    has_obs = dict()

    for row in obstable:
        mode = row['instrument_name']
        filters = str(row['filters'])
        proposal = row['proposal_id']
        if row['provenance_name'] == 'APT':
            proposal  = proposal+"-planned"
        if exclude_ta and '/TA' in mode:
            continue

        if mode not in has_obs:
            has_obs[mode] = dict()
        if proposal not in has_obs[mode]:
            has_obs[mode][proposal] = set()
        has_obs[mode][proposal].add(filters)

    sorted_results_dict = dict(sorted(has_obs.items()))
    return sorted_results_dict



def report_jwst_highcontrast_observations(targname, verbose=True):
    """ Summarize the available and planned JWST observations of a target using high contrast modes

    Returns astropy table of the observations, organized by mode

    Parameters
    ----------
    targname : str
        SIMBAD-resolvable target name
    verbose : bool
        be more verbose in output

    """
    modes = ['NIRCAM/CORON', #'NIRCAM/IMAGE',
              'NIRSPEC/IFU', #'NIRSPEC/SLIT',
              'MIRI/CORON', 'MIRI/IFU',
                      'NIRISS/AMI',
        ]

    obsinfo = summarize_jwst_observations(targname)

    result_table = astropy.table.Table(names=['Target_Name', ]+modes, dtype=['U30']+['U400',]*len(modes))
    result_table.add_row()
    result_table[0]['Target_Name'] = targname
    for k in modes:
        if k not in obsinfo:
            continue
        if verbose:
            print(k)
        program_keys = list(obsinfo[k].keys())
        program_keys.sort()
        text = ""

        if k == 'MIRI/CORON' or k =='NIRISS/AMI':
            # truncate off the uninteresting/redundant 2nd component in these filter;mask pairs.
            # just report the filter
            for prog in program_keys:
                 text+=  ','.join([v.split(';')[0] for v in obsinfo[k][prog]]) + f" ({prog})\n"
        elif k == "NIRSPEC/IFU":
            for prog in program_keys:
                text += ", ".join(g for g in obsinfo[k][prog]) + f" ({prog})\n"
        elif k == "NIRCAM/CORON":

            for prog in program_keys:
                maskbar_filts = set()
                maskrnd_filts = set()
                planned_filts = set()
                for j in obsinfo[k][prog]:
                    parts = j.split(';')
                    if parts[1]=='MASKRND':
                        maskrnd_filts.add(parts[0])
                    elif parts[1]=='MASKBAR':
                        maskbar_filts.add(parts[0])
                    else:
                        planned_filts.add(parts[0])
                        planned_filts.add(parts[1])
                maskbar_filts = list(maskbar_filts)
                maskrnd_filts = list(maskrnd_filts)
                planned_filts = list(planned_filts)

                maskbar_filts.sort()
                maskrnd_filts.sort()
                planned_filts.sort()
                if len(maskbar_filts):
                    text += "MASKBAR: "+ ",".join(maskbar_filts) + f" ({prog})\n"
                if len(maskrnd_filts):
                    text += "MASKRND: "+ ",".join(maskrnd_filts) + f" ({prog})\n"
                if len(planned_filts):
                    text += "         "+ ",".join(planned_filts) + f" ({prog})\n"
        elif k=='MIRI/IFU':
            for prog in program_keys:
                subbands = list(obsinfo[k][prog])
                subbands.sort()
                if len(subbands)==12:
                    summary = "ALL_CHANNELS"
                else:
                    summary = ",".join(subbands)
                text += f"{summary}  ({prog})\n"

        else:
           for prog in program_keys:
                text += ", ".join(g for g in obsinfo[k][prog]) + f" ({prog})\n"
        if verbose:
            print("\t" + text)
        result_table[0][k] = text
    return result_table
