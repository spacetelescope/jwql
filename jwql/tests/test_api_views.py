#!/usr/bin/env python

"""Tests for the ``api_views`` module in the ``jwql`` web application.

Authors
-------

    - Matthew Bourque
    - Bryan Hilbert
    - Melanie Clarke

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_api_views.py
"""

import http
import json
# import os
from urllib import request, error

import pytest

from jwql.utils.utils import get_base_url
from jwql.utils.constants import JWST_INSTRUMENT_NAMES
from jwql.utils.constants import ON_GITHUB_ACTIONS


urls = []

# Generic URLs
urls.append('api/proposals/')  # all_proposals

# Instrument-specific URLs
for instrument in JWST_INSTRUMENT_NAMES:
    urls.append('api/{}/proposals/'.format(instrument))  # instrument_proposals
    urls.append('api/{}/looks/'.format(instrument))  # instrument_looks
    urls.append('api/{}/looks/viewed/'.format(instrument))  # instrument_viewed
    urls.append('api/{}/looks/new/'.format(instrument))  # instrument_new

# Proposal-specific URLs
proposals = ['2640', '02733', '1541', '02589']

for proposal in proposals:
    urls.append('api/{}/filenames/'.format(proposal))  # filenames_by_proposal
    urls.append('api/{}/preview_images/'.format(proposal))  # preview_images_by_proposal
    urls.append('api/{}/thumbnails/'.format(proposal))  # thumbnails_by_proposal

# Filename-specific URLs
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
    except (error.HTTPError, error.URLError):
        pytest.skip("Server problem")

    try:
        data = json.loads(url.read().decode())

        # viewed data depends on local database contents
        # so may return an empty result
        if data_type != 'viewed':
            assert len(data[data_type]) > 0

    except http.client.IncompleteRead as e:
        data = e.partial
        assert len(data) > 0
