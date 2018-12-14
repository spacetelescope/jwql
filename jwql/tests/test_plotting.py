#!/usr/bin/env python

"""Tests for the ``plotting`` module.

Authors
-------

    - Joe Filippazzo

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_plotting.py
"""

from pandas import DataFrame

from jwql.utils.plotting import bar_chart


def test_bar_chart():
    """Make sure some dummy data generates a ``bokeh`` plot"""
    
    # Make a toy dataframe
    data = DataFrame({'meow': {'foo': 12, 'bar': 23, 'baz': 2},
                      'mix': {'foo': 45, 'bar': 31, 'baz': 23},
                      'deliver': {'foo': 62, 'bar': 20, 'baz': 9}})
    data = data.reset_index()

    # And generate a figure
    plt = bar_chart(data, 'index')

    assert str(type(plt)) == "<class 'bokeh.plotting.figure.Figure'>"
