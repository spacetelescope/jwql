"""
This is a minimal example demonstrating how to create a Bokeh app using
the ``bokeh-templating`` package and the associated YAML template files.

Author
-------

    - Graham Kanarek

Dependencies
------------

    The user must have PyYAML, Bokeh, and the ``bokeh-templating``
    packages installed.
"""

import os
import numpy as np

from jwql.bokeh_templating import BokehTemplate

file_dir = os.path.dirname(os.path.realpath(__file__))


class TestBokehApp(BokehTemplate):
    """This is a minimal ``BokehTemplate`` app."""

    _embed = True

    def pre_init(self):
        """Before creating the Bokeh interface (by parsing the interface
        file), we must initialize our ``a`` and ``b`` variables, and set
        the path to the interface file.
        """

        self.a, self.b = 4, 2

        self.format_string = None
        self.interface_file = os.path.join(file_dir, "example_interface.yaml")

    # No post-initialization tasks are required.
    post_init = None

    @property
    def x(self):
        """The x-value of the Lissajous curves."""
        return 4. * np.sin(self.a * np.linspace(0, 2 * np.pi, 500))

    @property
    def y(self):
        """The y-value of the Lissajous curves."""
        return 3. * np.sin(self.b * np.linspace(0, 2 * np.pi, 500))

    def controller(self, attr, old, new):
        """This is the controller function which is used to update the
        curves when the sliders are adjusted. Note the use of the
        ``self.refs`` dictionary for accessing the Bokeh object
        attributes."""
        self.a = self.refs["a_slider"].value
        self.b = self.refs["b_slider"].value

        self.refs["figure_source"].data = {'x': self.x, 'y': self.y}


TestBokehApp()
