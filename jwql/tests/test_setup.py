#! /usr/bin/env python

"""Tests for the ``setup.py`` module.

Authors
-------

    - Bryan Hilbert


Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_setup_info.py
"""

import jwql


def test_version_number():
    """Test that the JWQL version number is retrieved from
    ``setup.py``
    """

    assert isinstance(jwql.__version__, str)
    version_parts = jwql.__version__.split('.')
    assert len(version_parts) == 3
