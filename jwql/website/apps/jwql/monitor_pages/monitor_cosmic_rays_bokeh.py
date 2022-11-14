"""This module contains code for the cosmic ray monitor Bokeh plots.

Authors
-------

    - Bryan Hilbert

Use
---

    This module is intended to be imported and use as such:
    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.CosmicRayMonitor('nircam', 'NRCA1_FULL')

Bokeh figures will then be in:
        monitor_template.history_figure
        monitor_template.histogram_figure
"""

from datetime import datetime, timedelta
import os

from bokeh.models import BasicTickFormatter, ColumnDataSource, DatetimeTickFormatter, HoverTool, Range1d
from bokeh.plotting import figure
import matplotlib.pyplot as plt
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import MIRICosmicRayQueryHistory, MIRICosmicRayStats
from jwql.database.database_interface import NIRCamCosmicRayQueryHistory, NIRCamCosmicRayStats
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class CosmicRayMonitor():
    def __init__(self, instrument, aperture):
        """Create instance

        Parameters
        ----------
        instrument : str
            Name of JWST instrument. e.g. 'nircam'

        aperture : str
            Name of aperture. e.g. 'NRCA1_FULL'
        """
        self._instrument = instrument
        self._aperture = aperture
        self.create_figures()

    def create_figures(self):
        """Wrapper function to create both the history and histogram plots
        for a given instrument/aperture.
        """
        # Get the data
        self.load_data()

        # Create the history plot
        self.history_figure = self.history_plot()

        # Create the histogram plot
        self.histogram_figure = self.histogram_plot()

    def get_histogram_data(self):
        """Get data required to create cosmic ray histogram from the
        database query.
        """
        
        self.mags_hist = [row.magnitude for row in self.cosmic_ray_table]
        self.mags_outliers = [row.outliers for row in self.cosmic_ray_table]
        
        self.mags = np.zeros((65536*2+1), dtype=np.int64)
        for mag_histogram in self.mags_hist:
            self.mags += mag_histogram
        
        # If there are no data, then create something reasonable
        if len(self.mags_hist) == 0:
            self.mags[65527] = 1
            self.mags[65528] = 2
            self.mags[65529] = 3
            self.mags[65530] = 4
            self.mags[65531] = 5
            self.mags[65532] = 6
            self.mags[65533] = 7
            self.mags[65534] = 8
            self.mags[65535] = 9
            self.mags[65536] = 10
            self.mags[65537] = 9
            self.mags[65538] = 8
            self.mags[65539] = 7
            self.mags[65540] = 6
            self.mags[65541] = 5
            self.mags[65542] = 4
            self.mags[65543] = 3
            self.mags[65544] = 2
            self.mags[65545] = 1
        
        # For the moment, we're using a single bin per cosmic ray magnitude, between
        # -65536 and +65536.
        # Previous comment:
        #   We'll never see CRs with magnitudes above 65535.
        # Note by BQ on 2022-11-11: Yes, we will. They're not physical, but we'll sure
        # see them.
        self.bin_left = np.arange(65536*2+1, dtype=np.int32) - 65536
        self.amplitude = self.mags
        self.bottomn = np.zeros((65536*2+1,), dtype=np.int32)
        self.bin_width = np.ones((65536*2+1,), dtype=np.int32)

    def get_history_data(self):
        """Extract data on the history of cosmic ray numbers from the
        database query result
        """
        self.times = [row.obs_end_time for row in self.cosmic_ray_table]
        self.rate = [row.jump_rate for row in self.cosmic_ray_table]

    def histogram_plot(self):
        """Create the histogram figure of CR magnitudes.
        """
        self.get_histogram_data()

        title = f'Magnitudes: {self._instrument}, {self._aperture}'
        fig = figure(title=title, tools='zoom_in, zoom_out, box_zoom, pan, reset, save', background_fill_color="#fafafa")
        fig.quad(top=self.amplitude, bottom=0, left=self.bin_left, right=self.bin_left + self.bin_width,
                 fill_color="navy", line_color="black", alpha=0.5)

        fig.y_range.start = 0
        fig.xaxis.formatter.use_scientific = False
        fig.xaxis.major_label_orientation = np.pi / 4

        hover_tool = HoverTool(tooltips=[('Num CRs: ', '@top{int}')])
        fig.tools.append(hover_tool)

        fig.xaxis.axis_label = 'Cosmic Ray Magnitude (DN)'
        fig.yaxis.axis_label = 'Number of Cosmic Rays'
        fig.grid.grid_line_color = "white"
        fig.sizing_mode = "scale_width"
        return fig

    def history_plot(self):
        """Create the plot of CR rates versus time
        """
        self.get_history_data()

        # If there are no data, create a reasonable looking empty plot
        if len(self.times) == 0:
            self.times = [datetime(2021, 12, 25), datetime(2021, 12, 26)]
            self.rate = [0, 0]

        source = ColumnDataSource(data={'x': self.times, 'y': self.rate})

        # Create a useful plot title
        title = f'CR Rates: {self._instrument}, {self._aperture}'

        # Create figure
        fig = figure(tools='zoom_in, zoom_out, box_zoom, pan, reset, save', x_axis_type='datetime',
                     title=title, x_axis_label='Date', y_axis_label='CR rate (per pix per sec)')

        # For cases where the plot contains only a single point, force the
        # plot range to something reasonable
        if len(self.times) < 2:
            fig.x_range = Range1d(self.times[0] - timedelta(days=1), self.times[0] + timedelta(days=1))
            fig.y_range = Range1d(self.rate[0] - 0.5 * self.rate[0], self.rate[0] + 0.5 * self.rate[0])

        data = fig.scatter(x='x', y='y', line_width=5, line_color='blue', source=source)

        # Make the x axis tick labels look nice
        fig.xaxis.formatter = DatetimeTickFormatter(microseconds=["%d %b %H:%M:%S.%3N"],
                                                    seconds=["%d %b %H:%M:%S.%3N"],
                                                    hours=["%d %b %H:%M"],
                                                    days=["%d %b %H:%M"],
                                                    months=["%d %b %Y %H:%M"],
                                                    years=["%d %b %Y"]
                                                    )
        fig.xaxis.major_label_orientation = np.pi / 4
        fig.yaxis[0].formatter = BasicTickFormatter(use_scientific=True, precision=2)

        hover_tool = HoverTool(tooltips=[('Value', '@y'),
                                         ('Date', '@x{%d %b %Y %H:%M:%S}')
                                         ], mode='mouse', renderers=[data])
        hover_tool.formatters = {'@x': 'datetime'}
        fig.tools.append(hover_tool)
        fig.sizing_mode = "scale_width"
        return fig

    def identify_tables(self):
        """Determine which database tables as associated with
        a given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.query_table = eval('{}CosmicRayQueryHistory'.format(mixed_case_name))
        self.stats_table = eval('{}CosmicRayStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data with a matching aperture
        self.cosmic_ray_table = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self._aperture) \
            .all()
