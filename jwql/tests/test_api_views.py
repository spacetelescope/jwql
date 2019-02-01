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


urls = [
    'api/proposals/',  # all_proposals
    'api/86700/filenames/',  # filenames_by_proposal
    'api/jw86700005001_02101_00001_guider1/filenames/',  # filenames_by_rootname
    'api/fgs/proposals/',  # instrument_proposals
    'api/fgs/preview_images/',  # preview_images_by_instrument
    'api/86700/preview_images/',  # preview_images_by_proposal
    'api/jw86700005001_02101_00001_guider1/preview_images/',  # preview_images_by_rootname
    'api/fgs/thumbnails/',  # thumbnails_by_instrument
    'api/86700/thumbnails/',  # thumbnails_by_proposal
    'api/jw86700005001_02101_00001_guider1/thumbnails/']  # thumbnails_by_rootname


@pytest.mark.xfail
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

    # Determine the type of data to check for based on the url
    data_type = url.split('/')[-2]

    url = urllib.request.urlopen(url)
    data = json.loads(url.read().decode())

    assert len(data[data_type]) > 0
