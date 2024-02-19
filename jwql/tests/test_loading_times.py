#!/usr/bin/env python

"""Tests various webpages of the ``jwql`` web application to make sure
that loading times are not too long

Authors
-------

    - Matthew Bourque

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_loading_times.py
"""

import os
import pytest
import time
import urllib.request

from jwql.utils.constants import MONITORS
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.utils import get_base_url

TIME_CONSTRAINT = 30  # seconds

urls = []

# Generic URLs
urls.append('')
urls.append('about/')
urls.append('edb/')

# Instrument monitor URLs
for instrument in MONITORS:
    for monitor, monitor_url in MONITORS[instrument]:
        if monitor_url != '#':
            urls.append(monitor_url[1:])

# Specific URLs
test_mappings = [('fgs', '86700', 'jw86600007001_02101_00001_guider2'),
                 ('miri', '98012', 'jw98012001001_02102_00001_mirimage'),
                 ('nircam', '93025', 'jw93065002001_02101_00001_nrcb2'),
                 ('niriss', '00308', 'jw00308001001_02101_00001_nis'),
                 ('nirspec', '96213', 'jw96213001001_02101_00001_nrs1')]
for mapping in test_mappings:
    (instrument, proposal, rootname) = mapping
    urls.append('{}/'.format(instrument))
    urls.append('{}/archive/'.format(instrument))
    urls.append('{}/archive/{}/'.format(instrument, proposal))
    urls.append('{}/{}/'.format(instrument, rootname))


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason="Can't access webpage without VPN access")  # Can be removed once public-facing server exists
@pytest.mark.parametrize('url', urls)
def test_loading_times(url):
    """Test to see if the given ``url`` returns a webpage successfully
    within a reasonable time.

    Parameters
    ----------
    url : str
        The url to the webpage of interest (e.g.
        ``http://127.0.0.1:8000/fgs/archive/'``).
    """

    # Build full URL
    base_url = get_base_url()
    url = '{}/{}'.format(base_url, url)
    print('Testing {}'.format(url))

    t1 = time.time()
    try:
        urllib.request.urlopen(url)
    except (urllib.error.HTTPError, urllib.error.URLError):
        # may be missing data or no running server
        pytest.skip("Server problem")

    t2 = time.time()

    assert (t2 - t1) <= TIME_CONSTRAINT
