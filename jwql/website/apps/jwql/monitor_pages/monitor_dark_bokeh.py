"""This module contains code for the dark current monitor Bokeh plots.

Author
------

    - Bryan Hilbert
    - Gray Kanarek
    - Lauren Chambers

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.DarkMonitor('NIRCam', 'NRCA3_FULL')
        script, div = monitor_template.embed("dark_current_time_figure")
"""

import os

from astropy.io import fits
from astropy.time import Time
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool,  LinearAxis, Range1d
from bokeh.models.tickers import LogTicker
from bokeh.plotting import figure, show
from datetime import datetime, timedelta
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamDarkQueryHistory, NIRCamDarkPixelStats, NIRCamDarkDarkCurrent
from jwql.database.database_interface import NIRISSDarkQueryHistory, NIRISSDarkPixelStats, NIRISSDarkDarkCurrent
from jwql.database.database_interface import MIRIDarkQueryHistory, MIRIDarkPixelStats, MIRIDarkDarkCurrent
from jwql.database.database_interface import NIRSpecDarkQueryHistory, NIRSpecDarkPixelStats, NIRSpecDarkDarkCurrent
from jwql.database.database_interface import FGSDarkQueryHistory, FGSDarkPixelStats, FGSDarkDarkCurrent
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE, RAPID_READPATTERNS
from jwql.utils.utils import get_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = get_config()['outputs']


class DarkMonitorPlots():
    """This is the top-level class, which will call and use results from
    DarkMonitorData and AperturePlots.
    """
    def __init__(self, instrument):
        self.instrument = instrument
        self.hist_plots = {}
        self.trending_plots = {}

        # Get the data from the database
        self.db = DarkMonitorData(self.instrument)

        # Now we need to loop over the available apertures and create plots for each
        available_apertures = np.unique(np.array(self.db.stats_table.apertures))

        # List of full frame aperture names
        full_apertures = FULL_FRAME_APERTURES[instrument.upper()]

        for aperture in available_apertures:
            self.aperture = aperture
            self.stats_data_to_lists()

            # Organize the data to create the histogram plot
            self.get_latest_histogram_data()

            # Organize the data to create the trending plot
            self.get_trending_data()

            # Now that we have all the data, create the acutal plots
            self.hist_plots[aperture] = DarkHistPlot(self.hist_data, self.aperture)
            self.trending_plots[aperture] = DarkTrendPlot(self.mean_dark, self.stdev_dark, self.obstime)
            dark_image = DarkImagePlot(self.mean_dark_image)

            self.hist_plots[aperture] = hist.plot



    def stats_data_to_lists(self):
        """Create lists from some of the stats database columns that are
        used by multiple plot types

        Parameters
        ----------
        aperture : str
            Aperture name (e.g. NRCA1_FULL)
        """
        # Locate the entries corresponding to the given aperture
        apertures = np.array([e.aperture for e in self.db.stats_data])
        self._ap_idx = np.where((apertures == self.aperture))[0]

        self._apertures = np.array([e.aperture for e in self.db.stats_data[self._ap_idx]])
        self._amplifiers = np.array([e.amplifier for e in self.db.stats_data[self._ap_idx]])
        self._entry_dates = np.array([e.entry_date for e in self.db.stats_data[self._ap_idx]])
        self._mean = np.array([e.mean for e in self.db.stats_data[self._ap_idx]])
        self._stdev = np.array([e.stdev for e in self.db.stats_data[self._ap_idx]])
        self._obs_mid_time = np.array([e.obs_mid_time for e in self.db.stats_data[self._ap_idx]])
        self._mean_dark_file = np.array([e.mean_dark_image_file for e in self.db.stats_data[self._ap_idx]])

    def get_latest_histogram_data(self):
        """Organize data for histogram plot. In this case, we only need the
        most recent entry for the aperture. Note that for full frame data,
        there will be one entry per amplifier, e.g. '1', '2', '3', '4', for
        the four quadrants, as well as a '5' entry, which covers the entire
        detector. For subarray data, there will be a single entry with an
        amplifier value of '1'.

        This function assumes that the data from the database have already
        been filtered such that all entries are for the aperture of interest.

        """

        # Find the index of the most recent entry
        #self._aperture_entries = np.where((self._apertures == aperture))[0]
        latest_date = np.max(self._entry_dates) #[self._aperture_entries])

        # Get indexes of entries for all amps that were added in the
        # most recent run of the monitor for the aperture. All entries
        # for a given run are added to the database within a fraction of
        # a second, so using a time range of a few seconds should be fine.
        delta_time = timedelta(seconds=10)
        most_recent_idx = np.where(self._entry_dates > (latest_date - delta_time))[0]

        # Store the histogram data in a dictionary where the keys are the
        # amplifier values (note that these are strings e.g. '1''), and the
        # values are tuples of (x, y) lists
        self.hist_data = {}
        for idx in most_recent_idx:
            self.hist_data[db.stats_data[idx].amplifier] = (db.stats_data[idx].hist_dark_values,
                                                            db.stats_data[idx].hist_amplitudes)

        # If the we are working with a full frame aperture, collect the name of
        # the mean dark image file that is associated with the aperture. In this
        # case, we only need one filename, since it will cover all amplifiers.
        # And we're only interested in the latest entry.
        if self.aperture in FULL_FRAME_APERTURES:
            mean_slope_dir = os.path.join(OUTPUTS_DIR, 'dark_monitor', 'mean_slope_images')
            self.mean_dark_image_file = db.stats_data[most_recent_idx[0]].mean_dark_image_file
            mean_dark_image_path = os.path.join(mean_slope_dir, mean_dark_image_file)
            with fits.open(mean_dark_image_path) as hdulist:
                self.mean_dark_image = hdulist[1].data
        else:
            self.mean_dark_image = None

    def get_trending_data(self):
        """Organize data for the trending plot. Here we need all the data for
        the aperture. Keep amplifier-specific data separated.
        """
        # Separate the trending data by amplifier
        amp_vals = np.unique(np.array(self._amplifiers))
        self.mean_dark = {}
        self.stdev_dark = {}
        self.obstime = {}
        for amp in amp_vals:
            amp_rows = np.where(self._amplifiers == amp)[0]
            self.mean_dark[amp] = self._mean[amp_rows]
            self.stdev_dark[amp] = self._stdev[amp_rows]
            self.obstime[amp] = self._obs_mid_time[amp_rows]







class DarkHistPlot():
    """
    """
    def __init__(self, data, aperture):
        """
        Parameters
        ----------
        data : dict
            Histogram data. Keys are amplifier values (e.g. '1'). Values are
            tuples of (x values, y values)
        """
        self.data = data
        self.aperture = aperture
        self.create_plot()

    def calc_bin_edges(self, centers):
        """Given an array of values corresponding to the center of a series
        of histogram bars, calculate the bar edges

        Parameters
        ----------
        centers : numpy.ndarray
            Array of central values
        """
        deltax = (centers[1:] - centers[0:-1])
        deltax_left = np.insert(deltax, 0, deltax[0])
        deltax_right = np.append(deltax, deltax[-1])
        left = centers - 0.5 * deltax_left
        right = centers + 0.5 * deltax_right
        return left, right

    def create_plot(self):
        """
        """
        # Specify which keycontains the entire-aperture set of data
        if len(self.data) > 1:
            use_amp = '5'
            # Looks like the histogram data for the individual amps is not being saved
            # correctly. The data are identical for the full aperture and all amps. So
            # for the moment, show only the full aperture data.
            per_amp = False
            main_label = 'Full Aperture'

            # Colors to use for the amp-dpendent plots
            colors = []
        else:
            use_amp = '1'
            per_amp = False

        mainx, mainy = self.data[use_amp]
        mainx = np.array(mainx)
        mainy = np.array(mainy)

        # Calculate edge values
        left_edges, right_edges = self.calc_bin_edges(mainx)

        # Create the CDF
        pdf = mainy / sum(mainy)
        cdf = np.cumsum(pdf)

        # Create ColumnDataSource for main plot and CDF line
        source = ColumnDataSource(data=dict(dark_rate=mainx,
                                            num_pix=mainy,
                                            cdf=cdf,
                                            left_edges=left_edges,
                                            right_edges=right_edges
                                            )
                                  )

        self.plot = figure(title=self.aperture, tools='pan,box_zoom,reset,wheel_zoom,save', background_fill_color="#fafafa")

        # Plot the histogram for the "main" amp
        self.plot.quad(top='num_pix', bottom=0, left='left_edges', right='right_edges',
                       fill_color="navy", line_color="white", alpha=0.5, source=source)
        hover_tool = HoverTool(tooltips=[('Dark rate:', '@dark_rate'),
                                         ('Num Pix:', '@num_pix'),
                                         ('CDF:', '@cdf')
                                        ])
        self.plot.tools.append(hover_tool)

        # If there are multiple amps to be plotted, do that here
        if per_amp:
            self.plot.quad(top=mainy, bottom=0, left=left_edges, right=right_edges,
                           fill_color="navy", line_color="white", alpha=0.5, legend_label='Full Aperture')
            # Repeat for all amps. Be sure to skip the amp that's already completed
            for amp, color in zip(self.data, colors):
                if amp != use_amp:
                    x, y = self.data[amp]
                    x = np.array(x)
                    y = np.array(y)
                    amp_left_edges, amp_right_edges = self.calc_bin_edges(x)
                    self.plot.quad(top=y, bottom=0, left=amp_left_edges, right=amp_right_edges,
                                   fill_color=color, line_color="white", alpha=0.25, legend_label=f'Amp {amp}')

        # Set labels and ranges
        self.plot.xaxis.axis_label = 'Dark Rate (DN/sec)'
        self.plot.yaxis.axis_label = 'Number of Pixels'
        self.plot.extra_y_ranges = {"cdf_line": Range1d(0,1)}
        self.plot.add_layout(LinearAxis(y_range_name='cdf_line', axis_label="Cumulative Distribution"), "right")

        # Add cumulative distribution function
        self.plot.line('dark_rate', 'cdf', source=source, line_color="orange", line_width=2, alpha=0.7,
                       y_range_name='cdf_line', color="red", legend_label="CDF")

        # Set the initial x range to include 99.8% of the distribution
        disp_index = np.where((cdf > 0.001) & (cdf < 0.999))[0]

        self.plot.y_range.start = 0
        self.plot.y_range.end = np.max(mainy) * 1.1
        self.plot.x_range.start = mainx[disp_index[0]]
        self.plot.x_range.end = mainx[disp_index[-1]]
        self.plot.legend.location = "top_right"
        self.plot.legend.background_fill_color = "#fefefe"
        self.plot.grid.grid_line_color="white"


class DarkTrendPlot():
    """
    """
    def __init__(self, aperture, mean_dark, stdev_dark, obstime):
        self.aperture = aperture
        self.mean_dark = mean_dark
        self.stdev_dark = stdev_dark
        self.obstime = obstime
        self.create_plot()

    def create_plot(self):
        """
        """
        # Specify which keycontains the entire-aperture set of data
        if len(self.mean_dark) > 1:
            use_amp = '5'
            # Looks like the histogram data for the individual amps is not being saved
            # correctly. The data are identical for the full aperture and all amps. So
            # for the moment, show only the full aperture data.
            per_amp = False
            main_label = 'Full Aperture'

            # Colors to use for the amp-dpendent plots
            colors = []
        else:
            use_amp = '1'
            per_amp = False

        # Create a ColumnDataSource for the main amp to use
        source = ColumnDataSource(data=dict(mean_dark=self.mean_dark[use_amp],
                                            stdev_dark=self.stdev_dark[use_amp],
                                            time=self.obstime[use_amp]
                                            )
                                  )
        self.plot = figure(title=self.aperture, tools='pan,box_zoom,reset,wheel_zoom,save', background_fill_color="#fafafa")

        # Plot the "main" amp data
        self.plot.scatter(x='time', y='mean_dark', fill_color="navy", alpha=0.75, source=source, legend_label='Full Aperture')
        hover_tool = HoverTool(tooltips=[('Dark rate:', '@mean_dark'),
                                         ('Date:', '@time{%d %b %Y}')
                                        ])
        hover_tool.formatters = {'@time': 'datetime'}
        self.plot.tools.append(hover_tool)

        # If there are multiple amps to plot, do that here
        if per_amp:
            amp_source = {}
            # Repeat for all amps. Be sure to skip the amp that's already completed
            for amp, color in zip(self.mean_dark, colors):
                if amp != use_amp:
                    amp_source[amp] = ColumnDataSource(data=dict(mean_dark=self.mean_dark[amp],
                                                                 stdev_dark=self.stdev_dark[amp],
                                                                 time=self.obstime[amp]
                                                                 )
                                                       )
                    self.plot.scatter(x='time', y='mean_dark', fill_color=color, alpha=0.5, source=amp_source[amp],
                                      alpha=0.25, legend_label=f'Amp {amp}')

        # Make the x axis tick labels look nice
        self.plot.xaxis.formatter = DatetimeTickFormatter(microseconds=["%d %b %H:%M:%S.%3N"],
                                                seconds=["%d %b %H:%M:%S.%3N"],
                                                hours=["%d %b %H:%M"],
                                                days=["%d %b %H:%M"],
                                                months=["%d %b %Y %H:%M"],
                                                years=["%d %b %Y"]
                                                )
        self.plot.xaxis.major_label_orientation = np.pi / 4

        # Set x range
        time_pad = (max(self.obstime[use_amp]) - min(self.obstime[use_amp])) * 0.05
        self.plot.x_range.start = min(self.obstime[use_amp]) - time_pad
        self.plot.x_range.end = max(self.obstime[use_amp]) + time_pad

        # Set y range
        max_val = -99999.
        min_val = 99999.
        for key in mean_dark:
            mx = np.max(mean_dark[key])
            mn = np.min(mean_dark[key])
            if mx > max_val:
                max_val = mx
            if mn < min_val:
                min_val = mn
        self.plot.y_range.start = min_val * 0.95
        self.plot.y_range.end = max_val * 1.05
        self.plot.legend.location = "top_right"
        self.plot.legend.background_fill_color = "#fefefe"
        self.plot.grid.grid_line_color="white"


class DarkImagePlot():
    """
    """
    def __init__(self):
        ...









class AperturePlots():


Assume that this class is used for a single instrument/aperture. The calling
module will need to filter the data and supply just the data for the particular
aperture

    def __init__(instrument, aperture):
        self._instrument = instrument
        self._aperture_list = aperture_list

        # Get data from database
        #self.retrieve_data()

        # Create histogram plots
        self.create_histograms()

        # Create trending plots
        self.create_trending_plots()

        # Get mean dark images
        self.get_mean_dark_images()

        mean image tab:
        show the mean dark image (with good scaling)
        show the ratio image of mean dark / baseline
        on the mean dark image, scatter plot the new hot pixels (from db table)


    def create_histograms(self):
        """
        """

        # Get a list of all possible apertures from pysiaf
        #possible_apertures = list(Siaf(self.instrument).apernames)
        #possible_apertures = [ap for ap in possible_apertures if ap not in apertures_to_skip]

        # Get a list of all possible readout patterns associated with the aperture
        #possible_readpatts = RAPID_READPATTERNS[instrument]

        apertures = np.unique(np.array(self.dark_table.aperture))
        for aperture in apertures:
            # We plot the histogram of the most recent entry for each aperture
            latest =


        # Return dummy data if the database was empty
        if len(datetime_stamps) == 0:
            datetime_stamps = [datetime(2014, 1, 1, 12, 0, 0), datetime(2014, 1, 2, 12, 0, 0)]
            self.dark_current = [0., 0.1]
            self.full_dark_bin_center = np.array([0., 0.01, 0.02])
            self.full_dark_amplitude = [0., 1., 0.]
        else:
            self.dark_current = [row.mean for row in self.dark_table]
            #self.full_dark_bin_center = np.array([np.array(row.hist_dark_values) for
            #                                     row in self.dark_table])[last_hist_index]
            self.full_dark_bin_center = np.array(self.dark_table[last_hist_index].hist_dark_values)
            #self.full_dark_amplitude = [row.hist_amplitudes for
            #                            row in self.dark_table][last_hist_index]
            self.full_dark_amplitude = self.dark_table[last_hist_index].hist_amplitudes

        times = Time(datetime_stamps, format='datetime', scale='utc')  # Convert to MJD
        self.timestamps = times.mjd
        self.last_timestamp = datetime_stamps[last_hist_index].isoformat()
        self.full_dark_bottom = np.zeros(len(self.full_dark_amplitude))
        deltas = self.full_dark_bin_center[1:] - self.full_dark_bin_center[0: -1]
        self.full_dark_bin_width = np.append(deltas[0], deltas)



    def _dark_mean_image(self):
        """Update bokeh objects with mean dark image data."""

        # Open the mean dark current file and get the data
        if len(self.pixel_table) != 0:
            mean_dark_image_file = self.pixel_table[-1].mean_dark_image_file  - do not use -1. grab the entry for each aperture
            mean_slope_dir = os.path.join(OUTPUTS_DIR, 'dark_monitor', 'mean_slope_images')
            mean_dark_image_path = os.path.join(mean_slope_dir, mean_dark_image_file)
            with fits.open(mean_dark_image_path) as hdulist:
                data = hdulist[1].data
        else:
            # Cover the case where the database is empty
            data = np.zeros((10, 10))






class DarkMonitorData():

    def __init__(self, instrument_name):
        self.instrument = instrument_name

    def identify_tables(self):
        """Determine which dark current database tables as associated with
        a given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument_name.lower()]
        self.query_table = eval('{}DarkQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
        self.stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))

        # Get a list of column names for each
        self.stats_table_columns = self.stats_table.metadata.tables[f'{instrument_name.lower()}_dark_dark_current'].columns.keys()
        self.pixel_table_columns = self.pixel_table.metadata.tables[f'{instrument_name.lower()}_dark_pixel_stats'].columns.keys()
        self.query_table_columns = self.query_table.metadata.tables[f'{instrument_name.lower()}_dark_query_history'].columns.keys()

    def retrieve_data(self):
        """Get all nedded data from the database
        """
        # Determine which database tables to use
        self.identify_tables()

        # Query database for all data in <instrument>DarkDarkCurrent with a matching aperture
        self.stats_data = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self._aperture) \
            .all()

        self.pixel_data = session.query(self.pixel_table) \
            .filter(self.pixel_table.detector == self.detector) \
            .all()

        session.close()



























class DarkMonitor(BokehTemplate):

    # Combine instrument and aperture into a single property because we
    # do not want to invoke the setter unless both are updated
    @property
    def aperture_info(self):
        return (self._instrument, self._aperture)

    @aperture_info.setter
    def aperture_info(self, info):
        self._instrument, self._aperture = info
        self.pre_init()
        self.post_init()

    def _dark_mean_image(self):
        """Update bokeh objects with mean dark image data."""

        # Open the mean dark current file and get the data
        if len(self.pixel_table) != 0:
            mean_dark_image_file = self.pixel_table[-1].mean_dark_image_file
            mean_slope_dir = os.path.join(OUTPUTS_DIR, 'dark_monitor', 'mean_slope_images')
            mean_dark_image_path = os.path.join(mean_slope_dir, mean_dark_image_file)
            with fits.open(mean_dark_image_path) as hdulist:
                data = hdulist[1].data
        else:
            # Cover the case where the database is empty
            data = np.zeros((10, 10))

        # Update the plot with the data and boundaries
        y_size, x_size = np.shape(data)
        self.refs["mean_dark_source"].data['image'] = [data]
        self.refs["stamp_xr"].end = x_size
        self.refs["stamp_yr"].end = y_size
        self.refs["mean_dark_source"].data['dw'] = [x_size]
        self.refs["mean_dark_source"].data['dh'] = [x_size]

        # Set the image color scale
        self.refs["log_mapper"].high = 0
        self.refs["log_mapper"].low = -.2

        # This should add ticks to the colorbar, but it doesn't
        self.refs["mean_dark_cbar"].ticker = LogTicker()

        # Add a title
        self.refs['mean_dark_image_figure'].title.text = self._aperture
        self.refs['mean_dark_image_figure'].title.align = "center"
        self.refs['mean_dark_image_figure'].title.text_font_size = "20px"

    def pre_init(self):
        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        try:
            dummy_instrument = self._instrument
            dummy_aperture = self._aperture
        except AttributeError:
            self._instrument = 'NIRCam'
            self._aperture = 'NRCA1_FULL'

        self._embed = True

        # Fix aperture/detector name discrepency
        if self._aperture in ['NRCA5_FULL', 'NRCB5_FULL']:
            self.detector = '{}LONG'.format(self._aperture[0:4])
        else:
            self.detector = self._aperture.split('_')[0]

        # App design
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, "yaml", "dark_monitor_interface.yaml")

        # Load data tables
        self.load_data()

        # Data for mean dark versus time plot
        datetime_stamps = [row.obs_mid_time for row in self.dark_table]

        # Data for dark current histogram plot (full detector)
        # Just show the last histogram, which is the one most recently
        # added to the database
        last_hist_index = -1

        # Return dummy data if the database was empty
        if len(datetime_stamps) == 0:
            datetime_stamps = [datetime(2014, 1, 1, 12, 0, 0), datetime(2014, 1, 2, 12, 0, 0)]
            self.dark_current = [0., 0.1]
            self.full_dark_bin_center = np.array([0., 0.01, 0.02])
            self.full_dark_amplitude = [0., 1., 0.]
        else:
            self.dark_current = [row.mean for row in self.dark_table]
            #self.full_dark_bin_center = np.array([np.array(row.hist_dark_values) for
            #                                     row in self.dark_table])[last_hist_index]
            self.full_dark_bin_center = np.array(self.dark_table[last_hist_index].hist_dark_values)
            #self.full_dark_amplitude = [row.hist_amplitudes for
            #                            row in self.dark_table][last_hist_index]
            self.full_dark_amplitude = self.dark_table[last_hist_index].hist_amplitudes

        times = Time(datetime_stamps, format='datetime', scale='utc')  # Convert to MJD
        self.timestamps = times.mjd
        self.last_timestamp = datetime_stamps[last_hist_index].isoformat()
        self.full_dark_bottom = np.zeros(len(self.full_dark_amplitude))
        deltas = self.full_dark_bin_center[1:] - self.full_dark_bin_center[0: -1]
        self.full_dark_bin_width = np.append(deltas[0], deltas)

    def post_init(self):

        self._update_dark_v_time()
        self._update_hist()
        self._dark_mean_image()

    def identify_tables(self):
        """Determine which dark current database tables as associated with
        a given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.query_table = eval('{}DarkQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
        self.stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in NIRCamDarkDarkCurrent with a matching aperture
        self.dark_table = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self._aperture) \
            .all()

        self.pixel_table = session.query(self.pixel_table) \
            .filter(self.pixel_table.detector == self.detector) \
            .all()

        session.close()

    def _update_dark_v_time(self):

        # Define y range of dark current v. time plot
        buffer_size = 0.05 * (max(self.dark_current) - min(self.dark_current))
        self.refs['dark_current_yrange'].start = min(self.dark_current) - buffer_size
        self.refs['dark_current_yrange'].end = max(self.dark_current) + buffer_size

        # Define x range of dark current v. time plot
        horizontal_half_buffer = (max(self.timestamps) - min(self.timestamps)) * 0.05
        if horizontal_half_buffer == 0:
            horizontal_half_buffer = 1.  # day
        self.refs['dark_current_xrange'].start = min(self.timestamps) - horizontal_half_buffer
        self.refs['dark_current_xrange'].end = max(self.timestamps) + horizontal_half_buffer

        # Add a title
        self.refs['dark_current_time_figure'].title.text = self._aperture
        self.refs['dark_current_time_figure'].title.align = "center"
        self.refs['dark_current_time_figure'].title.text_font_size = "20px"

    def _update_hist(self):

        # Define y range of dark current histogram
        buffer_size = 0.05 * (max(self.full_dark_amplitude) - min(self.full_dark_bottom))
        self.refs['dark_histogram_yrange'].start = min(self.full_dark_bottom)
        self.refs['dark_histogram_yrange'].end = max(self.full_dark_amplitude) + buffer_size

        # Define x range of dark current histogram
        self.refs['dark_histogram_xrange'].start = min(self.full_dark_bin_center)
        self.refs['dark_histogram_xrange'].end = max(self.full_dark_bin_center)

        # Add a title
        self.refs['dark_full_histogram_figure'].title.text = self._aperture
        self.refs['dark_full_histogram_figure'].title.align = "center"
        self.refs['dark_full_histogram_figure'].title.text_font_size = "20px"
