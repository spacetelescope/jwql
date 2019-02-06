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

import json
import pytest
import urllib.request

from jwql.utils.utils import get_base_url
from jwql.utils.constants import JWST_INSTRUMENT_NAMES

urls = []

# Generic URLs
urls.append('api/proposals/')  # all_proposals

# Instrument-specific URLs
for instrument in JWST_INSTRUMENT_NAMES:
    urls.append('api/{}/proposals/'.format(instrument))  # instrument_proposals
    urls.append('api/{}/preview_images/'.format(instrument))  # preview_images_by_instrument
    urls.append('api/{}/thumbnails/'.format(instrument))  # thumbnails_by_instrument

# Proposal-specific URLs
proposals = ['86700'  # FGS
            ]
for proposal in proposals:
    urls.append('api/{}/filenames/'.format(proposal))  # filenames_by_proposal
    urls.append('api/{}/preview_images/'.format(proposal))  # preview_images_by_proposal
    urls.append('api/{}/thumbnails/'.format(proposal))  # thumbnails_by_proposal

# Filename-specific URLs
rootnames = ['jw86700005001_02101_00001_guider1'  # FGS
]
for rootname in rootnames:
    urls.append('api/{}/filenames/'.format(rootname))  # filenames_by_rootname
    urls.append('api/{}/preview_images/'.format(rootname))  # preview_images_by_rootname
    urls.append('api/{}/thumbnails'.format(rootname))  # thumbnails_by_rootname


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
    base_url = get_base_url()
    url = '{}/{}'.format(base_url, url)
    print('Testing {}'.format(url))

    # Determine the type of data to check for based on the url
    data_type = url.split('/')[-2]

    url = urllib.request.urlopen(url)
    data = json.loads(url.read().decode())

    assert len(data[data_type]) > 0
