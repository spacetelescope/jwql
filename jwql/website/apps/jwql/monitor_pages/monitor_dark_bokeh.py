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
        monitor_template = monitor_pages.DarkMonitor('nircam')
"""

import os

from astropy.time import Time
from bokeh.models import ColorBar, ColumnDataSource, DatetimeTickFormatter, HoverTool, Legend, LinearAxis
from bokeh.models import Range1d, Text, Whisker
from bokeh.plotting import figure
from datetime import datetime, timedelta
import numpy as np
from PIL import Image
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamDarkPixelStats, NIRCamDarkDarkCurrent
from jwql.database.database_interface import NIRISSDarkPixelStats, NIRISSDarkDarkCurrent
from jwql.database.database_interface import MIRIDarkPixelStats, MIRIDarkDarkCurrent
from jwql.database.database_interface import NIRSpecDarkPixelStats, NIRSpecDarkDarkCurrent
from jwql.database.database_interface import FGSDarkPixelStats, FGSDarkDarkCurrent
from jwql.utils.constants import FULL_FRAME_APERTURES
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = get_config()['outputs']


class DarkHistPlot():
    """Create a histogram plot of dark current values for a given aperture

    Attributes
    ----------
    aperture: str
        Aperture name (e.g. NRCA1_FULL)

    data : dict
        Dictionary of histogram data. Keys are amplifier values.
        Values are tuples of (x values, y values)

    plot : bokeh.figure
        Figure containing the histogram plot
    """
    def __init__(self, aperture, data):
        """Create the plot

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
        """Place the data in a CoumnDataSource and create the plot
        """
        if len(self.data) > 0:
            # Specify which key ("amplifier") to show. If there is data for amp='5',
            # show that, as it will be the data for the entire detector. If not then
            # we have subarray data and should use amp='1'.
            # A bug in the dark monitor means that for NIRISS, there is no amp = '5'
            # entry at the moment. So we set amp=1. Normally this would only plot the
            # histogram for amp 1, but since the dark_monitor output at the moment is
            # wrong and the histogram for the entire detector is being saved in the entries
            # for each amp, we can get away with using use_amp=1 at the moment.
            if '5' in self.data:
                use_amp = '5'
            else:
                use_amp = '1'

            # If there are histogram data for multiple amps, then we can plot each histogram.
            if len(self.data) > 1:
                # Looks like the histogram data for the individual amps is not being saved
                # correctly. The data are identical for the full aperture and all amps. So
                # for the moment, show only the full aperture data (by setting per_amp=False).
                per_amp = False
                main_label = 'Full Aperture'

                # Colors to use for the amp-dpendent plots
                colors = ['red', 'orange', 'green', 'gray']
            else:
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

            self.plot = figure(title=f'{self.aperture}: Dark Rate Histogram',
                               tools='pan,box_zoom,reset,wheel_zoom,save', background_fill_color="#fafafa")

            # Plot the histogram for the "main" amp
            self.plot.quad(top='num_pix', bottom=0, left='left_edges', right='right_edges',
                           fill_color="navy", line_color="white", alpha=0.5, source=source)
            hover_tool = HoverTool(tooltips=[('Dark rate:', '@dark_rate'),
                                             ('Num Pix:', '@num_pix'),
                                             ('CDF:', '@cdf')
                                             ],
                                   mode='mouse')
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

            # Set ranges
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
            self.plot.legend.location = "top_left"
            self.plot.legend.background_fill_color = "#fefefe"
            self.plot.grid.grid_line_color="white"
        else:
            # If self.data is empty, then make a placeholder plot
            self.plot = figure(title=f'{self.aperture}: Dark Rate Histogram',
                               tools='pan,box_zoom,reset,wheel_zoom,save', background_fill_color="#fafafa")
            self.plot.y_range.start = 0
            self.plot.y_range.end = 1
            self.plot.x_range.start = 0
            self.plot.x_range.end = 1

            source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
            glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
            self.plot.add_glyph(source, glyph)

        # Set labels and ranges
        self.plot.xaxis.axis_label = 'Dark Rate (DN/sec)'
        self.plot.yaxis.axis_label = 'Number of Pixels'


class DarkImagePlot():
    """Creates a figure that displays a mean dark current image
    held in a png file

    Attributes
    ----------
    aperture : str
        Name of aperture (e.g. NRCA1_FULL)

    dark_image_picture : str
        Name of png file containing the mean dark current image figure
        created by the dark monitor

    plot : bokeh.figure
        Figure containing the dark current image
    """
    def __init__(self, data, aperture):
        """Create the figure
        """
        self.dark_image_picture = data
        self.aperture = aperture

        self.create_plot()

    def create_plot(self):
        """Takes the input filename, reads it in, and places it in a figure. If
        the given filename doesn't exist, or if no filename is given, it produces
        an empty figure that can be used as a placeholder
        """
        if self.dark_image_picture is not None:
            if os.path.isfile(self.dark_image_picture):

                rgba_img = Image.open(self.dark_image_picture).convert('RGBA')
                xdim, ydim = rgba_img.size

                # Create an array representation for the image `img`, and an 8-bit "4
                # layer/RGBA" version of it `view`.
                img = np.empty((ydim, xdim), dtype=np.uint32)
                view = img.view(dtype=np.uint8).reshape((ydim, xdim, 4))

                # Copy the RGBA image into view, flipping it so it comes right-side up
                # with a lower-left origin
                view[:,:,:] = np.flipud(np.asarray(rgba_img))

                # Display the 32-bit RGBA image
                dim = max(xdim, ydim)
                self.plot = figure(x_range=(0, xdim), y_range=(0, ydim), tools='pan,box_zoom,reset,wheel_zoom,save')
                self.plot.image_rgba(image=[img], x=0, y=0, dw=xdim, dh=ydim)
                self.plot.xaxis.visible = False
                self.plot.yaxis.visible = False

            else:
                # If the given file is missing, create an empty plot
                self.empty_plot()
        else:
            # If no filename is given, then create an empty plot
            self.empty_plot()

    def empty_plot(self):
        # If no mean image is given, create an empty figure
        self.plot = figure(title=self.aperture, tools='')
        self.plot.x_range.start = 0
        self.plot.x_range.end = 1
        self.plot.y_range.start = 0
        self.plot.y_range.end = 1

        source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
        glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
        self.plot.add_glyph(source, glyph)


class DarkMonitorData():
    """Retrive dark monitor data from the database tables

    Attributes
    ----------
    detector : str
        Detector name (e.g. 'NRCA1')

    instrument : str
        Name of JWST instrument e.g. 'nircam'

    pixel_data : list
        Data returned from the pixel_table

    pixel_table : sqlalchemy.orm.decl_api.DeclarativeMeta
        Dark montior bad pixel list table

    pixel_table_columns : list
        List of columns in the pixel_table

    stats_data : list
        Data returned from the stats_table

    stats_table : sqlalchemy.orm.decl_api.DeclarativeMeta
        Dark monitor table giving dark current statistics

    stats_table_columns : list
        List of columns in the stats_table
    """
    def __init__(self, instrument_name):
        """Connect to the correct tables for the given instrument
        """
        self.instrument = instrument_name
        self.identify_tables()

    def identify_tables(self):
        """Determine which dark current database tables as associated with
        a given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.pixel_table = eval('{}DarkPixelStats'.format(mixed_case_name))
        self.stats_table = eval('{}DarkDarkCurrent'.format(mixed_case_name))

        # Get a list of column names for each
        self.stats_table_columns = self.stats_table.metadata.tables[f'{self.instrument.lower()}_dark_dark_current'].columns.keys()
        self.pixel_table_columns = self.pixel_table.metadata.tables[f'{self.instrument.lower()}_dark_pixel_stats'].columns.keys()

    def get_unique_stats_column_vals(self, column_name):
        """Return a list of the unique values from a particular column in the
        <Instrument>DarkDarkCurrent table (self.stats_table)

        Parameters
        ----------
        column_name : str
            Table column name to query

        Returns
        -------
        distinct_colvals : list
            List of unique values in the given column
        """
        colvals = session.query(eval(f'self.stats_table.{column_name}')).distinct()
        distinct_colvals = [eval(f'x.{column_name}') for x in colvals]
        return distinct_colvals

    def retrieve_data(self, aperture, get_pixtable_for_detector=False):
        """Get all nedded data from the database tables.

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
            # The MIRI imaging detector does not line up with the full frame aperture. Fix that here
            if self.detector == 'MIRIM':
                self.detector = 'MIRIMAGE'

            # NIRCam LW detectors use 'LONG' rather than 5 in the pixel_table
            if '5' in self.detector:
                self.detector = self.detector.replace('5', 'LONG')

            # For the given detector, get the latest entry for each bad pixel type, and
            # return the bad pixel type, detector, and mean dark image file
            subq = (session
                    .query(self.pixel_table.type, func.max(self.pixel_table.entry_date).label("max_created"))
                    .filter(self.pixel_table.detector == self.detector)
                    .group_by(self.pixel_table.type)
                    .subquery()
                    )

            query = (session.query(self.pixel_table.type, self.pixel_table.detector, self.pixel_table.mean_dark_image_file)
                     .join(subq, self.pixel_table.entry_date == subq.c.max_created)
                     )

            self.pixel_data = query.all()
        session.close()


class DarkMonitorPlots():
    """This is the top-level class, which will call the DarkMonitorData
    class to get results from the dark monitor, and use DarkHistPlot,
    DarkTrendPlot, and DarkImagePlot to create figures from the data.

    Attributes
    ----------
    aperture : str
        Name of the aperture used for the dark current (e.g.
        ``NRCA1_FULL``)

    available_apertures : list
        List of apertures for a given instrument that are present in
        the dark monitor database tables

    dark_image_data : dict
        Dictionary with aperture names as keys, and Bokeh images
        as values.

    dark_image_picture : str
        Filename of the png file containing an image of the mean dark current

    db : DarkMonitorData
        Instance of DarkMonitorData that contians dark monitor data
        retrieved from the database

    data_dir : str
        Path into which new dark files will be copied to be worked on

    hist_data : dict
        Dictionary of histogram data, with amplifier values as keys

    hist_plots : dict
        Dictionary with aperture names as keys, and Bokeh histogram
        plots as values.

    instrument : str
        Name of instrument used to collect the dark current data

    mean_dark : dict
        Mean dark current values, with amplifiers as keys

    mean_slope_dir : str
        Directory containing the mean dark current images output
        by the dark monitor


    obstime : dict
        Observation times associated with mean_dark, with amplifiers as keys

    output_dir : str
        Path into which outputs will be placed

    pixel_table : sqlalchemy table
        Table containing lists of hot/dead/noisy pixels found for each
        instrument/detector

    query_start : float
        MJD start date to use for querying MAST

    stats_table : sqlalchemy table
        Table containing dark current analysis results. Mean/stdev
        values, histogram information, Gaussian fitting results, etc.

    stdev_dark : dict
        Standard deviation of dark current values, with amplifiers as keys

    trending_plots : dict
        Dictionary with aperture names as keys, and Bokeh scatter
        plots as values.

    _amplifiers : numpy.ndarray
        Array of amplifier values from the database table

    _entry_dates : numpy.ndarray
        Array of entry dates from the database table

    _mean : numpy.ndarray
        Array of mean dark current values from the database table

    _obs_mid_time : numpy.ndarray
        Array of observation times from the database table

    _stats_mean_dark_image_files : numpy.ndarray
        Array of mean dark current image filenames from the database table

    _stats_numfiles : numpy.ndarray
        Array of the number of files used to create each mean dark, from the database table

    _stdev : numpy.ndarray
        Array of standard deviation of dark current values from the database table
    """
    def __init__(self, instrument):
        """Query the database, get the data, and create the plots
        """
        self.mean_slope_dir = os.path.join(OUTPUTS_DIR, 'dark_monitor', 'mean_slope_images')
        self.instrument = instrument
        self.hist_plots = {}
        self.trending_plots = {}
        self.dark_image_data = {}

        # Get the data from the database
        self.db = DarkMonitorData(self.instrument)

        # Now we need to loop over the available apertures and create plots for each
        self.available_apertures = self.db.get_unique_stats_column_vals('aperture')

        # Require entries for all full frame apertures. If there are no data for a
        # particular full frame entry, then produce an empty plot, in order to
        # keep the plot layout consistent
        self.ensure_all_full_frame_apertures()

        # List of full frame aperture names
        full_apertures = FULL_FRAME_APERTURES[instrument.upper()]

        for aperture in self.available_apertures:
            self.aperture = aperture

            # Retrieve data from database. Since the mean dark image plots are
            # produced by the dark monitor itself, all we need for that is the
            # name of the file. then we need the histogram and trending data. All
            # of this is in the dark monitor stats table. No need to query the
            # dark monitor pixel table.
            self.db.retrieve_data(self.aperture, get_pixtable_for_detector=False)
            self.stats_data_to_lists()
            self.get_mean_dark_image_from_stats_table()

            # Create the mean dark image figure
            self.dark_image_data[self.aperture] = DarkImagePlot(self.dark_image_picture, self.aperture).plot

            # Organize the data to create the histogram plot
            self.get_latest_histogram_data()

            # Organize the data to create the trending plot
            self.get_trending_data()

            # Now that we have all the data, create the acutal plots
            self.hist_plots[aperture] = DarkHistPlot(self.aperture, self.hist_data).plot
            self.trending_plots[aperture] = DarkTrendPlot(self.aperture, self.mean_dark, self.stdev_dark, self.obstime).plot

    def ensure_all_full_frame_apertures(self):
        """Be sure that self.available_apertures contains entires for all
        full frame apertures. These are needed to make sure the plot layout
        is consistent later
        """
        full_apertures = FULL_FRAME_APERTURES[self.instrument.upper()]
        for ap in full_apertures:
            if ap not in self.available_apertures:
                self.available_apertures.append(ap)

    def extract_times_from_filename(self, filename):
        """Based on the mean dark filename produced by the dark monitor, extract the
        starting and ending times covered by the file.

        Parameters
        ----------
        filename : str
            Name of file to be examined

        Returns
        -------
        starttime : datetime.datetime
            Datetime of the beginning of the range covered by the file

        endtime : datetime.datetime
            Datetime of the end of the range covered by the file
        """
        file_parts = filename.split('_')
        start = Time(file_parts[3], format='mjd')
        end = Time(file_parts[5], format='mjd')
        return start.tt.datetime, end.tt.datetime

    def get_mean_dark_image_from_stats_table(self):
        """Get the name of the mean dark image file to be displayed
        """
        self.dark_image_picture = None
        if len(self._stats_mean_dark_image_files) > 0:
            # Grab the most recent entry
            image_path = os.path.join(self.mean_slope_dir, self._stats_mean_dark_image_files[-1].replace('fits', 'png'))
            if os.path.isfile(image_path):
                self.dark_image_picture = image_path

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
        self.hist_data = {}
        if len(self._entry_dates) > 0:
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
            for idx in most_recent_idx:
                self.hist_data[self.db.stats_data[idx].amplifier] = (self.db.stats_data[idx].hist_dark_values,
                                                                     self.db.stats_data[idx].hist_amplitudes)

    def get_trending_data(self):
        """Organize data for the trending plot. Here we need all the data for
        the aperture. Keep amplifier-specific data separated.
        """
        # Separate the trending data by amplifier
        self.mean_dark = {}
        self.stdev_dark = {}
        self.obstime = {}

        if len(self._amplifiers) > 0:
            amp_vals = np.unique(np.array(self._amplifiers))
            for amp in amp_vals:
                amp_rows = np.where(self._amplifiers == amp)[0]
                self.mean_dark[amp] = self._mean[amp_rows]
                self.stdev_dark[amp] = self._stdev[amp_rows]
                self.obstime[amp] = self._obs_mid_time[amp_rows]

    def stats_data_to_lists(self):
        """Create arrays from some of the stats database columns that are
        used by multiple plot types
        """
        #apertures = np.array([e.aperture for e in self.db.stats_data])
        self._amplifiers = np.array([e.amplifier for e in self.db.stats_data])
        self._entry_dates = np.array([e.entry_date for e in self.db.stats_data])
        self._mean = np.array([e.mean for e in self.db.stats_data])
        self._stdev = np.array([e.stdev for e in self.db.stats_data])
        self._obs_mid_time = np.array([e.obs_mid_time for e in self.db.stats_data])
        self._stats_mean_dark_image_files = np.array([e.mean_dark_image_file for e in self.db.stats_data])
        self._stats_numfiles = np.array([len(e.source_files) for e in self.db.stats_data])


class DarkTrendPlot():
    """Create the dark current trending plot (mean dark rate vs time) for
    the given aperture.

    Attributes
    ----------
    aperture : str
        Name of aperture (e.g. NRCA1_FULL)

    mean_dark : dict
        Trending data. Keys are amplifier values (e.g. '1'). Values are
        lists of mean dark rates

    stdev_dark : dict
        Standard deviation of the dark rate data. Keys are amplifier values
        (e.g. '1'). Values are lists of dark rate standard deviations

    obstime : dict
        Observation time associated with the dark rates. Keys are amplifier
        values (e.g. '1'). Values are lists of datetime objects

    plot : bokeh.figure
        Figure containing trending plot

    """
    def __init__(self, aperture, mean_dark, stdev_dark, obstime):
        """Creates the plot given the input data

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
        """Takes the data, places it in a ColumnDataSource, and creates the figure
        """
        if len(self.mean_dark) > 0:
            # Specify which key ("amplifier") to show. If there is data for amp='5',
            # show that, as it will be the data for the entire detector. If not then
            # we have subarray data and should use amp='1'.
            # A bug in the dark monitor means that for NIRISS, there is no amp = '5'
            # entry at the moment. So we set amp=1. Normally this would only plot the
            # histogram for amp 1, but since the dark_monitor output at the moment is
            # wrong and the histogram for the entire detector is being saved in the entries
            # for each amp, we can get away with using use_amp=1 at the moment.
            if '5' in self.mean_dark:
                use_amp = '5'
            else:
                use_amp = '1'

            # If there are trending data for multiple amps, then we can plot each
            if len(self.mean_dark) > 1:
                # Looks like the histogram data for the individual amps is not being saved
                # correctly. The data are identical for the full aperture and all amps. So
                # for the moment, show only the full aperture data (by setting per_amp=False).
                per_amp = False
                main_label = 'Full Aperture'

                # Colors to use for the amp-dpendent plots
                colors = ['red', 'orange', 'green', 'grey']
            else:
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
            self.plot = figure(title=f'{self.aperture}: Mean +/- 1-sigma Dark Rate', tools='pan,box_zoom,reset,wheel_zoom,save',
                               background_fill_color="#fafafa")

            # Plot the "main" amp data along with error bars
            self.plot.scatter(x='time', y='mean_dark', fill_color="navy", alpha=0.75, source=source)
            self.plot.add_layout(Whisker(source=source, base="time", upper="error_upper", lower="error_lower", line_color='navy'))
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
            if time_pad == timedelta(seconds=0):
                time_pad = timedelta(days=1)
            self.plot.x_range.start = min(self.obstime[use_amp]) - time_pad
            self.plot.x_range.end = max(self.obstime[use_amp]) + time_pad

            # Set y range
            max_val = -99999.
            min_val = 99999.
            for key in self.mean_dark:
                mx = np.max(self.mean_dark[key] + self.stdev_dark[key])
                mn = np.min(self.mean_dark[key] - self.stdev_dark[key])
                if mx > max_val:
                    max_val = mx
                if mn < min_val:
                    min_val = mn
            self.plot.y_range.start = min_val * 0.95
            self.plot.y_range.end = max_val * 1.05
            self.plot.legend.location = "top_right"
            self.plot.legend.background_fill_color = "#fefefe"
            self.plot.grid.grid_line_color="white"
        else:
            # If there are no data, make a placeholder plot
            self.plot = figure(title=f'{self.aperture}: Mean +/- 1-sigma Dark Rate', tools='pan,box_zoom,reset,wheel_zoom,save',
                               background_fill_color="#fafafa")
            self.plot.x_range.start = 0
            self.plot.x_range.end = 1
            self.plot.y_range.start = 0
            self.plot.y_range.end = 1

            source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
            glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
            self.plot.add_glyph(source, glyph)

        self.plot.xaxis.axis_label = 'Date'
        self.plot.yaxis.axis_label = 'Dark Rate (DN/sec)'
