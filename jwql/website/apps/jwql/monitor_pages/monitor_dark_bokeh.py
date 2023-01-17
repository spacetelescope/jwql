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
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from bokeh.models import ColorBar, ColumnDataSource, DatetimeTickFormatter, HoverTool,  Legend, LinearAxis, LinearColorMapper, Range1d, Whisker
from bokeh.models.tickers import LogTicker
from bokeh.plotting import figure, show
from bokeh.transform import linear_cmap
from datetime import datetime, timedelta
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamDarkQueryHistory, NIRCamDarkPixelStats, NIRCamDarkDarkCurrent
from jwql.database.database_interface import NIRISSDarkQueryHistory, NIRISSDarkPixelStats, NIRISSDarkDarkCurrent
from jwql.database.database_interface import MIRIDarkQueryHistory, MIRIDarkPixelStats, MIRIDarkDarkCurrent
from jwql.database.database_interface import NIRSpecDarkQueryHistory, NIRSpecDarkPixelStats, NIRSpecDarkDarkCurrent
from jwql.database.database_interface import FGSDarkQueryHistory, FGSDarkPixelStats, FGSDarkDarkCurrent
from jwql.utils.constants import FULL_FRAME_APERTURES, JWST_INSTRUMENT_NAMES_MIXEDCASE, RAPID_READPATTERNS
from jwql.utils.utils import get_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = get_config()['outputs']


class DarkMonitorPlots():
    """This is the top-level class, which will call and use results from
    DarkMonitorData and AperturePlots.
    """
    def __init__(self, instrument):
        self.mean_slope_dir = os.path.join(OUTPUTS_DIR, 'dark_monitor', 'mean_slope_images')
        self.instrument = instrument
        self.hist_plots = {}
        self.trending_plots = {}
        self.dark_image_data = {}

        # Get the data from the database
        self.db = DarkMonitorData(self.instrument)

        # Now we need to loop over the available apertures and create plots for each
        available_apertures = self.db.get_unique_stats_column_vals('aperture')
        #available_apertures = np.unique(np.array(self.db.stats_table.apertures))

        # List of full frame aperture names
        full_apertures = FULL_FRAME_APERTURES[instrument.upper()]

        for aperture in available_apertures:
            self.aperture = aperture

            # Retrieve data from database. Retrieve bad pixel data (which is
            # associated with the detector rather than the aperture) only if
            # the aperture is a full frame aperture.
            if self.aperture in full_apertures:
                self.db.retrieve_data(self.aperture, get_pixtable_for_detector=True)

                # Convert query results for the bad pixel data to a series of arrays
                self.pixel_data_to_lists()

                # Organize the information that will be used to show the mean dark images
                # and possible bad pixels
                self.get_mean_dark_images()

                # Create the mean dark image fiugure
                self.dark_image_data[self.aperture] = DarkImagePlot(self.db.detector, self.image_data).plot

            else:
                # For apertures that are not full frame, we retrieve only the histogram
                # and trending data. No mean dark image nor bad pixel lists
                self.db.retrieve_data(self.aperture, get_pixtable_for_detector=False)

            # In all cases, full frame as well as subarray apertures, we create dark
            # current histogram and trending plots.

            # Convert the columns we are interested in to lists
            self.stats_data_to_lists()

            # Organize the data to create the histogram plot
            self.get_latest_histogram_data()

            # Organize the data to create the trending plot
            self.get_trending_data()

            # Now that we have all the data, create the acutal plots
            self.hist_plots[aperture] = DarkHistPlot(self.aperture, self.hist_data).plot
            self.trending_plots[aperture] = DarkTrendPlot(self.aperture, self.mean_dark, self.stdev_dark, self.obstime).plot


    def get_mean_dark_images(self):
        """Organize data for the tab of the dark monitor plots that shows
        the mean dark current images. In this case there are only images
        for full frame apertures. There will be three entries with the same
        detector/mean dark file/obstimes/basefile, one each for bad pixel
        types 'hot', 'dead', 'noisy'. Make sure to get all three.
        """
        # Use the most recent entry for each of the three bad pixel types
        hot_idx = np.where(self._types == 'hot')[0][-1]
        dead_idx = np.where(self._types == 'dead')[0][-1]
        noisy_idx = np.where(self._types == 'noisy')[0][-1]

        # Store the bad pixel data in a dictionary where the keys are the
        # type of bad pixel ('hot', 'dead', or 'noisy'), and the
        # values are tuples of (x, y) lists
        image_path = os.path.join(self.mean_slope_dir, self._mean_dark_image_files[hot_idx])
        mean_dark_image = fits.getdata(image_path, 1)

        self.image_data = {"image_array": mean_dark_image,
                           "hot_pixels": (self._x_coords[hot_idx],
                                          self._y_coords[hot_idx]
                                          ),
                           "dead_pixels": (self._x_coords[dead_idx],
                                           self._y_coords[dead_idx]
                                           ),
                           "noisy_pixels": (self._x_coords[noisy_idx],
                                            self._y_coords[noisy_idx]
                                            ),
                           "baseline_file": self._baseline_files[hot_idx]
                           }

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
            self.hist_data[self.db.stats_data[idx].amplifier] = (self.db.stats_data[idx].hist_dark_values,
                                                                 self.db.stats_data[idx].hist_amplitudes)

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

    def pixel_data_to_lists(self):
        """Convert db query results to arrays
        """
        self._pixel_entry_dates = np.array([e.entry_date for e in self.db.pixel_data])#[self._det_idx]])
        self._detectors = np.array([e.detector for e in self.db.pixel_data])
        self._x_coords = np.array([e.x_coord for e in self.db.pixel_data])#[self._det_idx]])
        self._y_coords = np.array([e.y_coord for e in self.db.pixel_data])#[self._det_idx]])
        self._types = np.array([e.type for e in self.db.pixel_data])#[self._det_idx]])
        self._mean_dark_image_files = np.array([e.mean_dark_image_file for e in self.db.pixel_data])#[self._det_idx]])
        self._baseline_files = np.array([e.baseline_file for e in self.db.pixel_data])#[self._det_idx]])

    def stats_data_to_lists(self):
        """Create arrays from some of the stats database columns that are
        used by multiple plot types
        """
        apertures = np.array([e.aperture for e in self.db.stats_data])
        self._amplifiers = np.array([e.amplifier for e in self.db.stats_data])#[self._ap_idx]])
        self._entry_dates = np.array([e.entry_date for e in self.db.stats_data])#[self._ap_idx]])
        self._mean = np.array([e.mean for e in self.db.stats_data])#[self._ap_idx]])
        self._stdev = np.array([e.stdev for e in self.db.stats_data])#[self._ap_idx]])
        self._obs_mid_time = np.array([e.obs_mid_time for e in self.db.stats_data])#[self._ap_idx]])



class DarkHistPlot():
    """
    """
    def __init__(self, aperture, data):
        """
        Parameters
        ----------
        aperture : str
            Name of the aperture (e.g. 'NRCA1_FULL')

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
    """Create the dark current trending plot (mean dark rate vs time) for
    the given aperture.
    """
    def __init__(self, aperture, mean_dark, stdev_dark, obstime):
        """
        Parameters
        ----------
        aperture : str
            Name of the aperture (e.g. 'NRCA1_FULL')

        mean_dark : dict
            Trending data. Keys are amplifier values (e.g. '1'). Values are
            lists of mean dark rates

        stdev_dark : dict
            Standard deviation of the dark rate data. Keys are amplifier values
            (e.g. '1'). Values are lists of dark rate standard deviations

        obstime : dict
            Observation time associated with the dark rates. Keys are amplifier
            values (e.g. '1'). Values are lists of datetime objects
        """
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

        error_lower = self.mean_dark[use_amp] - self.stdev_dark[use_amp]
        error_upper = self.mean_dark[use_amp] + self.stdev_dark[use_amp]

        # Create a ColumnDataSource for the main amp to use
        source = ColumnDataSource(data=dict(mean_dark=self.mean_dark[use_amp],
                                            stdev_dark=self.stdev_dark[use_amp],
                                            error_lower=error_lower,
                                            error_upper=error_upper,
                                            time=self.obstime[use_amp]
                                            )
                                  )
        self.plot = figure(title=self.aperture, tools='pan,box_zoom,reset,wheel_zoom,save', background_fill_color="#fafafa")

        # Plot the "main" amp data along with error bars
        self.plot.scatter(x='time', y='mean_dark', fill_color="navy", alpha=0.75, source=source, legend_label='Full Aperture')
        self.plot.add_layout(Whisker(source=source, base="mean_dark", upper="error_upper", lower="error_lower", line_color='navy'))
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
                                      legend_label=f'Amp {amp}')

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
        for key in self.mean_dark:
            mx = np.max(self.mean_dark[key])
            mn = np.min(self.mean_dark[key])
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
    def __init__(self, detector, data):
        self.detector = detector
        self.image_data = data

        self.create_plot()

    def create_plot(self):
        """
        """

        """
        #working example
        from bokeh.plotting import show
        image = np.random.random((2048,2048)) * 0.5 + 0.2
        ny, nx = image.shape

        hot_pixels_x=[500,500, 500, 500]
        hot_pixels_y=[500,501, 502, 503]
        dead_pixels_x=[450,450,450,450]
        dead_pixels_y=[450,451,452,453]
        noisy_pixels_x=[400,400,400,400]
        noisy_pixels_y=[400,401,402,403]

        hot_vals = []
        for x,y in zip(hot_pixels_x, hot_pixels_y):
            hot_vals.append(image[y, x])
        dead_vals = []
        for x,y in zip(dead_pixels_x, dead_pixels_y):
            dead_vals.append(image[y, x])
        noisy_vals = []
        for x,y in zip(noisy_pixels_x, noisy_pixels_y):
            noisy_vals.append(image[y, x])

        img_mn, img_med, img_dev = sigma_clipped_stats(image[4:2044,4:2044])
        mapper = LinearColorMapper(palette='Viridis256', low=(img_med-5*img_dev) ,high=(img_med+5*img_dev))
        plot = figure(title='something', tools='pan,box_zoom,reset,wheel_zoom,save')
        imgplot = plot.image(image=[image], x=0, y=0, dw=nx, dh=ny,
                                  color_mapper=mapper, level="image")
        color_bar = ColorBar(color_mapper=mapper, width=8, title='DN/sec')
        plot.add_layout(color_bar, 'right')

        hover_tool = HoverTool(tooltips=[('(x, y):', '($x{int}, $y{int})'),
                                 ('value:', '@image')
                                ],
                      renderers=[imgplot])
        plot.tools.append(hover_tool)

        source = ColumnDataSource(data=dict(hot_pixels_x=[500,500, 500, 500],
                                            hot_pixels_y=[500,501, 502, 503],
                                            hot_values=hot_vals,
                                            dead_pixels_x=[450,450,450,450],
                                            dead_pixels_y=[450,451,452,453],
                                            dead_values=dead_vals,
                                            noisy_pixels_x=[400,400,400,400],
                                            noisy_pixels_y=[400,401,402,403],
                                            noisy_values=noisy_vals
                                            )
                                  )
        hot = plot.circle(x='hot_pixels_x', y='hot_pixels_y', source=source, color='red')
        dead = plot.circle(x='dead_pixels_x', y='dead_pixels_y', source=source, color='blue')
        noisy = plot.circle(x='noisy_pixels_x', y='noisy_pixels_y', source=source, color='pink')

        hover_tool_hot = HoverTool(tooltips=[
                                             ('hot (x, y):', '(@hot_pixels_x, @hot_pixels_y)'),
                                             ('value:', '@hot_values'),
                                            ],
                                   renderers=[hot])

        hover_tool_dead = HoverTool(tooltips=[
                                        ('dead (x, y):', '(@dead_pixels_x, @dead_pixels_y)'),
                                             ],
                                    renderers=[dead])

        hover_tool_noisy = HoverTool(tooltips=[('noisy (x, y):', '(@noisy_pixels_x, @noisy_pixels_y)'),
                                              ],
                                     renderers=[noisy])
        plot.tools.append(hover_tool_hot)
        plot.tools.append(hover_tool_dead)
        plot.tools.append(hover_tool_noisy)

        legend = Legend(items=[("Hotter than baseline"   , [hot]),
                               ("Lower than baseline" , [dead]),
                               ("Noisier than baseline" , [noisy]),
                              ], location="center", orientation='horizontal')

        plot.add_layout(legend, 'below')

        show(plot)

        """



        # Get info on image for better display later
        ny, nx = self.image_data["image_array"].shape
        img_mn, img_med, img_dev = sigma_clipped_stats(self.image_data["image_array"][4: ny - 4, 4: nx - 4])

        # Create figure
        self.plot = figure(title=self.detector, tools='pan,box_zoom,reset,wheel_zoom,save')
        self.plot.x_range.range_padding = self.plot.y_range.range_padding = 0

        # Create the color mapper that will be used to scale the image
        mapper = LinearColorMapper(palette='Viridis256', low=(img_med-5*img_dev) ,high=(img_med+5*img_dev))

        # Plot image and add color bar
        imgplot = self.plot.image(image=[self.image_data["image_array"]], x=0, y=0, dw=nx, dh=ny,
                                  color_mapper=mapper, level="image")

        color_bar = ColorBar(color_mapper=mapper, width=8, title='DN/sec')
        self.plot.add_layout(color_bar, 'right')

        # Add hover tool for all pixel values
        hover_tool = HoverTool(tooltips=[('(x, y):', '($x{int}, $y{int})'),
                                         ('value:', '@image')
                                        ],
                               renderers=[imgplot])
        self.plot.tools.append(hover_tool)

        # Create lists of hot/dead/noisy pixel values
        hot_vals = []
        for x, y in zip(self.image_data["hot_pixels"][0], self.image_data["hot_pixels"][1]):
            hot_vals.append(self.image_data["image_array"][y, x])
        dead_vals = []
        for x, y in zip(self.image_data["dead_pixels"][0], self.image_data["dead_pixels"][1]):
            dead_vals.append(self.image_data["image_array"][y, x])
        noisy_vals = []
        for x, y in zip(self.image_data["noisy_pixels"][0], self.image_data["noisy_pixels"][1]):
            noisy_vals.append(self.image_data["image_array"][y, x])

        source = ColumnDataSource(data=dict(hot_pixels_x=self.image_data["hot_pixels"][0],
                                            hot_pixels_y=self.image_data["hot_pixels"][1],
                                            hot_values=hot_vals,
                                            dead_pixels_x=self.image_data["dead_pixels"][0],
                                            dead_pixels_y=self.image_data["dead_pixels"][1],
                                            dead_values=dead_vals,
                                            noisy_pixels_x=self.image_data["noisy_pixels"][0],
                                            noisy_pixels_y=self.image_data["noisy_pixels"][1],
                                            noisy_values=noisy_vals,
                                            )
                                  )

        # Overplot the bad pixel locations
        hot = self.plot.circle(x='hot_pixels_x', y='hot_pixels_y', source=source, color='red')
        dead = self.plot.circle(x='dead_pixels_x', y='dead_pixels_y', source=source, color='blue')
        noisy = self.plot.circle(x='noisy_pixels_x', y='noisy_pixels_y', source=source, color='pink')

        # Create hover tools for the bad pixel types
        hover_tool_hot = HoverTool(tooltips=[('hot (x, y):', '(@hot_pixels_x, @hot_pixels_y)'),
                                             ('value:', '@hot_values'),
                                             ],
                                   renderers=[hot])

        hover_tool_dead = HoverTool(tooltips=[('dead (x, y):', '(@dead_pixels_x, @dead_pixels_y)'),
                                              ('value:', '@dead_values'),
                                              ],
                                    renderers=[dead])

        hover_tool_noisy = HoverTool(tooltips=[('noisy (x, y):', '(@noisy_pixels_x, @noisy_pixels_y)'),
                                               ('value:', '@noisy_values'),
                                               ],
                                     renderers=[noisy])

        self.plot.tools.append(hover_tool_hot)
        self.plot.tools.append(hover_tool_dead)
        self.plot.tools.append(hover_tool_noisy)

        # Add the legend
        legend = Legend(items=[("Higher than baseline"   , [hot]),
                               ("Lower than baseline" , [dead]),
                               ("Noisier than baseline" , [noisy]),
                               ],
                        location="center",
                        orientation='horizontal')

        self.plot.add_layout(legend, 'below')











"""
class AperturePlots():


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


    def create_histograms(self):

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
        Update bokeh objects with mean dark image data.

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
"""





class DarkMonitorData():

    def __init__(self, instrument_name):
        self.instrument = instrument_name
        self.identify_tables()

    def identify_tables(self):
        """Determine which dark current database tables as associated with
        a given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.query_table = eval('{}DarkQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
        self.stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))

        # Get a list of column names for each
        self.stats_table_columns = self.stats_table.metadata.tables[f'{self.instrument.lower()}_dark_dark_current'].columns.keys()
        self.pixel_table_columns = self.pixel_table.metadata.tables[f'{self.instrument.lower()}_dark_pixel_stats'].columns.keys()
        self.query_table_columns = self.query_table.metadata.tables[f'{self.instrument.lower()}_dark_query_history'].columns.keys()

    def get_unique_stats_column_vals(self, column_name):
        """Return a list of the unique values from a particular column in the
        <Instrument>DarkDarkCurrent table (self.stats_table)

        Parameters
        ----------
        column_name : str
            Table column name to query
        """
        colvals = session.query(eval(f'self.stats_table.{column_name}')).distinct()
        distinct_colvals = [eval(f'x.{column_name}') for x in colvals]
        return distinct_colvals

    def retrieve_data(self, aperture, get_pixtable_for_detector=False):
        """Get all nedded data from the database

        Parameters
        ----------
        aperture : str
            Name of aperture for which data are retrieved (e.g. NRCA1_FULL)

        get_pixtable_for_detector : bool
            If True, query self.pixel_table (e.g. NIRCamDarkPixelStats) for the
            detector associated with the given aperture.
        """
        # Query database for all data in <instrument>DarkDarkCurrent with a matching aperture
        self.stats_data = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == aperture) \
            .all()

        if get_pixtable_for_detector:
            self.detector = aperture.split('_')[0].upper()
            self.pixel_data = session.query(self.pixel_table) \
                .filter(self.pixel_table.detector == self.detector) \
                .all()

        session.close()
