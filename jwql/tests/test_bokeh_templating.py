#! /usr/bin/env python

"""
"""

from jwql.bokeh_templating import BokehTemplate


class TestTemplate(BokehTemplate):
    """
    """

    def pre_init(self):
        """
        """

        self.interface_file = 'test_interface.yaml'  # Some basic plot(s)

    def post_init(self):
        """
        """

def test_bokeh_templating():
    """
    """

    test_template = TestTemplate()

    tabs = 'Some collection of plot(s)'
    script, div = components(tabs)

    assert script is script obj
    assert div is div obj