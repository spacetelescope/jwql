"""This module contains code for the readnoise monitor Bokeh plots.

Author
------

    - Ben Sunnquist

Use
---

    This module can be used from the command line as such:

    ::

        .
        monitor_template = monitor_pages.ReadnoiseMonitor()
        monitor_template.input_parameters = ('NIRCam', 'NRCA1_FULL')
"""

from datetime import datetime, timedelta
import os

from bokeh.embed import components
from bokeh.layouts import column, row
from bokeh.models import Panel, Tabs  # bokeh <= 3.0
from bokeh.models import ColumnDataSource, HoverTool
# from bokeh.models import TabPanel, Tabs  # bokeh >= 3.0
from bokeh.plotting import figure
from django.templatetags.static import static
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import FGSReadnoiseStats, MIRIReadnoiseStats, NIRCamReadnoiseStats, NIRISSReadnoiseStats, NIRSpecReadnoiseStats
from jwql.utils.constants import FULL_FRAME_APERTURES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config

OUTPUTS_DIR = get_config()['outputs']


class ReadnoiseMonitorData():
    """Class to hold bias data to be plotted

    Parameters
    ----------

    instrument : str
        Instrument name (e.g. nircam)
    aperture : str
        Aperture name (e.g. apername)

    Attributes
    ----------

    instrument : str
        Instrument name (e.g. nircam)
    aperture : str
        Aperture name (e.g. apername)
    query_results : list
        Results from read noise statistics table based on
        instrument, aperture and exposure start time
    stats_table : sqlalchemy.orm.decl_api.DeclarativeMeta
        Statistics table object to query based on instrument
        and aperture
    """

    def __init__(self, instrument, aperture):
        self.instrument = instrument
        self.aperture = aperture
        self.load_data()

    def identify_tables(self):
        """Determine which database tables to use for the given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.stats_table = eval('{}ReadnoiseStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get all of the relevant readnoise data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in readnoise stats with a matching aperture,
        # and sort the data by exposure start time.
        self.query_results = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self.aperture) \
            .order_by(self.stats_table.expstart) \
            .all()

        session.close()


class ReadNoiseFigure():
    """Generate tabbed plot displayed in JWQL web application
    """
    def __init__(self, instrument):
        instrument_apertures = FULL_FRAME_APERTURES[instrument.upper()]

        self.tabs = []
        for aperture in instrument_apertures:
            readnoise_tab = ReadNoisePlotTab(instrument, aperture)
            self.tabs.append(readnoise_tab.tab)

        self.plot = Tabs(tabs=self.tabs)
        self.tab_components = components(self.plot)


class ReadNoisePlotTab():
    """Class to make instrument/aperture panels
    """
    def __init__(self, instrument, aperture):
        self.instrument = instrument
        self.aperture = aperture
        self.ins_ap = "{}_{}".format(self.instrument.lower(), self.aperture.lower())

        self.db = ReadnoiseMonitorData(self.instrument, self.aperture)

        self.file_path = static(os.path.join("outputs", "readnoise_monitor", "data", self.ins_ap))

        self.plot_readnoise_amplifers()
        self.plot_readnoise_difference_image()
        self.plot_readnoise_histogram()

        self.tab = Panel(child=column(row(*self.amp_plots),
                                      self.diff_image_plot,
                                      self.readnoise_histogram),
                         title=self.aperture)

    def plot_readnoise_amplifers(self):
        """Class to create readnoise scatter plots per amplifier.
        """
        self.amp_plots = []
        for amp in ['1', '2', '3', '4']:

            amp_plot = figure(title='Amp {}'.format(amp), width=280, height=280, x_axis_type='datetime')
            amp_plot.xaxis[0].ticker.desired_num_ticks = 4

            if self.db.query_results:
                readnoise_vals = np.array([getattr(result, 'amp{}_mean'.format(amp)) for result in self.db.query_results])
            else:
                readnoise_vals = np.array(list())

            filenames = [result.uncal_filename.replace('_uncal.fits', '') for result in self.db.query_results]
            expstarts_iso = np.array([result.expstart for result in self.db.query_results])
            expstarts = np.array([datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f') for date in expstarts_iso])
            nints = [result.nints for result in self.db.query_results]
            ngroups = [result.ngroups for result in self.db.query_results]

            source = ColumnDataSource(data=dict(
                                      file=filenames,
                                      expstarts=expstarts,
                                      nints=nints,
                                      ngroups=ngroups,
                                      readnoise=readnoise_vals))

            amp_plot.add_tools(HoverTool(tooltips=[("file", "@file"),
                                                   ("time", "@expstarts"),
                                                   ("nints", "@nints"),
                                                   ("ngroups", "@ngroups"),
                                                   ("readnoise", "@readnoise")]))

            amp_plot.circle(x='expstarts', y='readnoise', source=source)

            amp_plot.xaxis.axis_label = 'Date'
            amp_plot.yaxis.axis_label = 'Mean Readnoise [DN]'

            self.amp_plots.append(amp_plot)

    def plot_readnoise_difference_image(self):
        """Updates the readnoise difference image"""

        # Update the readnoise difference image and histogram, if data exists

        self.diff_image_plot = figure(title='Readnoise Difference (most recent dark - pipeline reffile)',
                                      height=500, width=500, sizing_mode='scale_width')

        if len(self.db.query_results) != 0:
            diff_image_png = os.path.join(self.file_path, self.db.query_results[-1].readnoise_diff_image)
            self.diff_image_plot.image_url(url=[diff_image_png], x=0, y=0, w=2048, h=2048, anchor="bottom_left")

        self.diff_image_plot.xaxis.visible = False
        self.diff_image_plot.yaxis.visible = False
        self.diff_image_plot.xgrid.grid_line_color = None
        self.diff_image_plot.ygrid.grid_line_color = None
        self.diff_image_plot.title.text_font_size = '22px'
        self.diff_image_plot.title.align = 'center'

    def plot_readnoise_histogram(self):
        """Updates the readnoise histogram"""

        if len(self.db.query_results) != 0:
            diff_image_n = np.array(self.db.query_results[-1].diff_image_n)
            diff_image_bin_centers = np.array(self.db.query_results[-1].diff_image_bin_centers)
        else:
            diff_image_n = np.array(list())
            diff_image_bin_centers = np.array(list())

        hist_xr_start = diff_image_bin_centers.min()
        hist_xr_end = diff_image_bin_centers.max()
        hist_yr_start = diff_image_n.min()
        hist_yr_end = diff_image_n.max() + diff_image_n.max() * 0.05

        self.readnoise_histogram = figure(height=500, width=500,
                                          x_range=(hist_xr_start, hist_xr_end),
                                          y_range=(hist_yr_start, hist_yr_end),
                                          sizing_mode='scale_width')

        source = ColumnDataSource(data=dict(x=diff_image_bin_centers, y=diff_image_n, ))

        self.readnoise_histogram.add_tools(HoverTool(tooltips=[("Data (x, y)", "(@x, @y)"), ]))

        self.readnoise_histogram.circle(x='x', y='y', source=source)

        self.readnoise_histogram.xaxis.axis_label = 'Readnoise Difference [DN]'
        self.readnoise_histogram.yaxis.axis_label = 'Number of Pixels'
        self.readnoise_histogram.xaxis.axis_label_text_font_size = "15pt"
        self.readnoise_histogram.yaxis.axis_label_text_font_size = "15pt"
