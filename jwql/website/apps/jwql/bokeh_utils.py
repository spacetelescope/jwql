"""Various Bokeh-related utility functions for the ``jwql`` project.

Authors
-------

    - Bryan Hilbert

Use
---

    This module can be imported as such:

    >>> from jwql.website.apps.jwql.bokeh_utils import PlaceholderPlot

 """
from bokeh.models import ColumnDataSource, Text
from bokeh.plotting import figure


class PlaceholderPlot():
    def __init__(self, title, x_label, y_label):
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.create()

    def create(self):
        self.plot = figure(title=self.title, tools='', background_fill_color="#fafafa")
        self.plot.x_range.start = 0
        self.plot.x_range.end = 1
        self.plot.y_range.start = 0
        self.plot.y_range.end = 1

        source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
        glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
        self.plot.add_glyph(source, glyph)
        self.plot.xaxis.axis_label = self.x_label
        self.plot.yaxis.axis_label = self.y_label

