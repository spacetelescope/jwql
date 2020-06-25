#! /usr/bin/env python

"""This module contains functions used to indentify and download
reference files from CRDS and place them in the expected location, for
JWQL to find.

This module uses the ``crds`` software package
(``https://hst-crds.stsci.edu/static/users_guide/index.html``) which is
installed when the JWST calibration pipeline package is installed.
Reference files are identified by supplying some basic metadata from the
exposure being calibrated. See
https://hst-crds.stsci.edu/static/users_guide/library_use.html#crds-getreferences
for a description of the function used for this task.

Author
------

    - Bryan Hilbert

Use
---

    This module can be used as such:
    ::
        from mirage.reference_files import crds
        params = {'INSTRUME': 'NIRCAM', 'DETECTOR': 'NRCA1'}
        reffiles = crds.get_reffiles(params)
"""

import datetime
import os

from jwql.utils.utils import ensure_dir_exists
from jwql.utils.constants import EXPTYPES


def env_variables():
    """Check the values of the CRDS-related environment variables

    Returns
    -------
    crds_data_path : str
        Full path to the location of the CRDS reference files
    """
    crds_data_path = path_check()
    server_check()

    return crds_data_path


def path_check():
    """Check that the ``CRDS_PATH`` environment variable is set. This
    will be the location to which CRDS reference files are downloaded.
    If the env variable is not set, default to use ``$HOME/crds_cache/``

    Returns
    -------
    crds_path : str
        Full path to the location of the CRDS reference files
    """
    crds_path = os.environ.get('CRDS_PATH')
    if crds_path is None:
        reffile_dir = '{}/crds_cache'.format(os.environ.get('HOME'))
        os.environ["CRDS_PATH"] = reffile_dir
        ensure_dir_exists(reffile_dir)
        print('CRDS_PATH environment variable not set. Setting to {}'.format(reffile_dir))
        return reffile_dir
    else:
        return crds_path


def server_check():
    """Check that the ``CRDS_SERVER_URL`` environment variable is set.
    This controls where Mirage will look for CRDS information. If the
    env variable is not set, set it to the JWST CRDS server.
    """
    crds_server = os.environ.get('CRDS_SERVER_URL')
    if crds_server is None:
        os.environ["CRDS_SERVER_URL"] = "https://jwst-crds.stsci.edu"


def dict_from_yaml(yaml_dict):
    """Create a dictionary to be used as input to the CRDS getreferences
    function from the nested dictionary created when a standard Mirage
    input yaml file is read in.

    Parameters
    ----------
    yaml_dict : dict
        Nested dictionary from reading in yaml file
    Returns
    -------
    crds_dict : dict
        Dictionary of information necessary to select refernce files
        via getreferences().
    """
    crds_dict = {}
    instrument = yaml_dict['Inst']['instrument'].upper()
    crds_dict['INSTRUME'] = instrument
    crds_dict['READPATT'] = yaml_dict['Readout']['readpatt'].upper()

    # Currently, all reference files that use SUBARRAY as a selection
    # criteria contain SUBARRAY = 'GENERIC', meaning that SUBARRAY
    # actually isn't important. So let's just set it to FULL here.
    crds_dict['SUBARRAY'] = 'FULL'

    # Use the current date and time in order to get the most recent
    # reference file
    crds_dict['DATE-OBS'] = datetime.date.today().isoformat()
    current_date = datetime.datetime.now()
    crds_dict['TIME-OBS'] = current_date.time().isoformat()

    array_name = yaml_dict['Readout']['array_name']
    crds_dict['DETECTOR'] = array_name.split('_')[0].upper()
    if '5' in crds_dict['DETECTOR']:
        crds_dict['DETECTOR'] = crds_dict['DETECTOR'].replace('5', 'LONG')

    if 'FGS' in crds_dict['DETECTOR']:
        crds_dict['DETECTOR'] = 'GUIDER{}'.format(crds_dict['DETECTOR'][-1])

    if instrument == 'NIRCAM':
        if crds_dict['DETECTOR'] in ['NRCALONG', 'NRCBLONG']:
            crds_dict['CHANNEL'] = 'LONG'
        else:
            crds_dict['CHANNEL'] = 'SHORT'

    # For the purposes of choosing reference files, the exposure type should
    # always be set to imaging, since it is used to locate sources in the
    # seed image, prior to any dispersion.
    crds_dict['EXP_TYPE'] = EXPTYPES[instrument.lower()]["imaging"]

    # This assumes that filter and pupil names match up with reality,
    # as opposed to the more user-friendly scheme of allowing any
    # filter to be in the filter field.
    crds_dict['FILTER'] = yaml_dict['Readout']['filter']
    crds_dict['PUPIL'] = yaml_dict['Readout']['pupil']

    return crds_dict


def get_reffiles(parameter_dict, reffile_types, download=True):
    """Determine CRDS's best reference files to use for a particular
    observation, and download them if they are not already present in
    the ``CRDS_PATH``. The determination is made based on the
    information in the ``parameter_dictionary``.

    Parameters
    ----------
    parameter_dict : dict
        Dictionary of basic metadata from the file to be processed by
        the returned reference files (e.g. ``INSTRUME``, ``DETECTOR``,
        etc)

    reffile_types : list
        List of reference file types to look up and download. These must
        be contained in CRDS's list of reference file types.

    download : bool
        If ``True`` (default), the identified best reference files will
        be downloaded. If ``False``, the dictionary of best reference
        files will still be returned, but the files will not be
        downloaded. The use of ``False`` is primarily intended to
        support testing on Travis.

    Returns
    -------
    reffile_mapping : dict
        Mapping of downloaded CRDS file locations
    """

    # IMPORTANT: Import of crds package must be done AFTER the environment
    # variables are set in the functions above
    import crds
    from crds import CrdsLookupError

    if download:
        try:
            reffile_mapping = crds.getreferences(parameter_dict, reftypes=reffile_types)
        except CrdsLookupError:
            raise ValueError("ERROR: CRDSLookupError when trying to find reference files for parameters: {}".format(parameter_dict))
    else:
        # If the files will not be downloaded, still return the same local
        # paths that are returned when the files are downloaded. Note that
        # this follows the directory structure currently assumed by CRDS.
        crds_path = os.environ.get('CRDS_PATH')
        try:
            reffile_mapping = crds.getrecommendations(parameter_dict, reftypes=reffile_types)
        except CrdsLookupError:
            raise ValueError("ERROR: CRDSLookupError when trying to find reference files for parameters: {}".format(parameter_dict))

        for key, value in reffile_mapping.items():
            # Check for NOT FOUND must be done here because the following
            # line will raise an exception if NOT FOUND is present
            if "NOT FOUND" in value:
                reffile_mapping[key] = "NOT FOUND"
            else:
                instrument = value.split('_')[1]
                reffile_mapping[key] = os.path.join(crds_path, 'references/jwst', instrument, value)

    return reffile_mapping
