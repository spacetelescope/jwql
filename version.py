"""Determine the current version of the ``jwql`` package.

Authors
-------

    - Matthew Bourque

Use
---
    This module is intended to be imported and used as such:
    ::

        from version import get_version
        version = get_version()
"""

import urllib.request
from bs4 import BeautifulSoup


def get_version():
    """Return the current version number of the ``jwql`` package.

    Returns
    -------
    version : str
        The version number (e.g. ``0.16.0``).
    """

    url = urllib.request.urlopen('https://github.com/spacetelescope/jwql/releases.atom')
    data = BeautifulSoup(url, features="lxml")
    tag = str(data.find('entry').find('id'))
    version = tag.split('</id>')[-2].split('/')[-1]

    return version
