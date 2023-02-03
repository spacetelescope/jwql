#!/usr/bin/env python

"""Tests for the ``api_views`` module in the ``jwql`` web application.

Authors
-------

    - Matthew Bourque
    - Bryan Hilbert

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_api_views.py
"""

import http
import json
import os
from urllib import request, error

import pytest

from jwql.utils.utils import get_base_url
from jwql.utils.constants import JWST_INSTRUMENT_NAMES

# Determine if tests are being run on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')

urls = []

# Generic URLs
urls.append('api/proposals/')  # all_proposals

# Instrument-specific URLs
for instrument in JWST_INSTRUMENT_NAMES:
    urls.append('api/{}/proposals/'.format(instrument))  # instrument_proposals

# Proposal-specific URLs

# TODO: currently missing in central storage
# proposals = ['01018',  # FGS
#              '01022',  # MIRI
#              '01068',  # NIRCam
#              '01059',  # NIRISS
#              '1059',  # NIRISS
#              '01106']  # NIRSpec
proposals = ['2640', '02733', '1541', '02589']

for proposal in proposals:
    urls.append('api/{}/filenames/'.format(proposal))  # filenames_by_proposal
    urls.append('api/{}/preview_images/'.format(proposal))  # preview_images_by_proposal
    urls.append('api/{}/thumbnails/'.format(proposal))  # thumbnails_by_proposal

# Filename-specific URLs

# TODO: currently missing in central storage
#rootnames = ['jw01018001004_02101_00001_guider1',  # FGS
#             'Jjw1022017001_03101_00001_mirimage',  # MIRI
#             'jw01068001001_02102_00001_nrcb1',  # NIRCam
#             'jw01059121001_02107_00001_nis',  # NIRISS
#             'jw01106002001_02101_00002_nrs1']
rootnames = ['jw02733002001_02101_00001_mirimage',  # MIRI
             'jw02733001001_02101_00001_nrcb2']  # NIRCam

for rootname in rootnames:
    urls.append('api/{}/filenames/'.format(rootname))  # filenames_by_rootname
    urls.append('api/{}/preview_images/'.format(rootname))  # preview_images_by_rootname
    urls.append('api/{}/thumbnails/'.format(rootname))  # thumbnails_by_rootname


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason="Can't access webpage without VPN access")  # Can be removed once public-facing server exists
@pytest.mark.parametrize('url', urls)
def test_api_views(url):
    """Test to see if the given ``url`` returns a populated JSON object

    Parameters
    ----------
    url : str
        The url to the api view of interest (e.g.
        ``http://127.0.0.1:8000/api/86700/filenames/'``).
    """

    # Build full URL
    if not ON_GITHUB_ACTIONS:
        base_url = get_base_url()  # For running unit tests locally
    else:
        base_url = 'https://jwql.stsci.edu'  # Once this actually exists, remove skipif

    url = '{}/{}'.format(base_url, url)

    # Determine the type of data to check for based on the url
    data_type = url.split('/')[-2]

    try:
        url = request.urlopen(url)
    except error.HTTPError as e:
        if e.code == 502:
            pytest.skip("Server problem")
        raise(e)

    try:
        data = json.loads(url.read().decode())
        assert len(data[data_type]) > 0
    except (http.client.IncompleteRead) as e:
        data = e.partial
        assert len(data) > 0
