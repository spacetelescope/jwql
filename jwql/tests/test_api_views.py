#!/usr/bin/env python

"""Tests for the ``api_views`` module in the ``jwql`` web application.

Authors
-------

    - Matthew Bourque

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

# Determine if tests are being run on jenkins
ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')

# Determine if the local server is running
try:
    url = request.urlopen('http://127.0.0.1:8000')
    LOCAL_SERVER = True
except error.URLError:
    LOCAL_SERVER = False

urls = []

# Generic URLs
urls.append('api/proposals/')  # all_proposals

# Instrument-specific URLs
for instrument in JWST_INSTRUMENT_NAMES:
    urls.append('api/{}/proposals/'.format(instrument))  # instrument_proposals
    urls.append('api/{}/preview_images/'.format(instrument))  # preview_images_by_instrument
    urls.append('api/{}/thumbnails/'.format(instrument))  # thumbnails_by_instrument

# Proposal-specific URLs
proposals = ['86700',  # FGS
             '98012',  # MIRI
             '93025',  # NIRCam
             '00308',  # NIRISS
             '308',  # NIRISS
             '96213']  # NIRSpec
for proposal in proposals:
    urls.append('api/{}/filenames/'.format(proposal))  # filenames_by_proposal
    urls.append('api/{}/preview_images/'.format(proposal))  # preview_images_by_proposal
    urls.append('api/{}/thumbnails/'.format(proposal))  # thumbnails_by_proposal

# Filename-specific URLs
rootnames = ['jw86600007001_02101_00001_guider2',  # FGS
             'jw98012001001_02102_00001_mirimage',  # MIRI
             'jw93025001001_02102_00001_nrca2',  # NIRCam
             'jw00308001001_02103_00001_nis',  # NIRISS
             'jw96213001001_02101_00001_nrs1']  # NIRSpec
for rootname in rootnames:
    urls.append('api/{}/filenames/'.format(rootname))  # filenames_by_rootname
    urls.append('api/{}/preview_images/'.format(rootname))  # preview_images_by_rootname
    urls.append('api/{}/thumbnails/'.format(rootname))  # thumbnails_by_rootname


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
    if not ON_JENKINS:
        base_url = get_base_url()
    else:
        base_url = 'https://dljwql.stsci.edu'

    if base_url == 'http://127.0.0.1:8000' and not LOCAL_SERVER:
        pytest.skip("Local server not running")

    url = '{}/{}'.format(base_url, url)

    # Determine the type of data to check for based on the url
    data_type = url.split('/')[-2]

    try:
        url = request.urlopen(url)
    except error.HTTPError as e:
        if e.code == 502:
            pytest.skip("Dev server problem")
        raise(e)

    try:
        data = json.loads(url.read().decode())
        assert len(data[data_type]) > 0
    except (http.client.IncompleteRead) as e:
        data = e.partial
        assert len(data) > 0
