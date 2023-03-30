
"""This module contains code for the bias monitor Bokeh plots.

Author
------

    - Ben Sunnquist
    - Maria A. Pena-Guerrero

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.BiasMonitor()
        monitor_template.input_parameters = ('NIRCam', 'NRCA1_FULL')
"""

from datetime import datetime, timedelta
import os

from astropy.stats import sigma_clip

from bokeh.models import ColorBar, ColumnDataSource, DatetimeTickFormatter, HoverTool, Legend, LinearAxis
from bokeh.models import Range1d, Text, Whisker
from bokeh.plotting import figure
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from PIL import Image
from sqlalchemy import func

from jwql.bokeh_templating import BokehTemplate
from jwql.database.database_interface import get_unique_values_per_column, NIRCamBiasStats, NIRISSBiasStats, NIRSpecBiasStats, session
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import read_png


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class BiasMonitorData():
    """Class to hold bias data to be plotted
    """
    def __init__(self, instrument):
        self.instrument = instrument
        #self.create_aperture_name()
        self.identify_tables()

    def identify_tables(self):
        """Determine which database tables to use for the given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.stats_table = eval('{}BiasStats'.format(mixed_case_name))

    def organize_latest_data(self, data):
        """Convert the latest data, as returned from the database table, from a nested
        list into a dictionary. Keys will be the uncal filenames.

        Parameters
        ----------
        data : list of tuples
            Nested list returned from the database query
        """
        self.latest_data = {}

        for row in data:
            pass



    def retrieve_trending_data(self, aperture):
        """Query the database table to get all of the data needed to create
        the plots of mean bias signals over time

        Parameters
        ----------
        aperture : str
            Name of the aperture whose data are being collected. e.g. 'NRCA1_FULL'
        """

        # Query database for all data in bias stats with a matching aperture,
        # and sort the data by exposure start time.
        self.tmp_trending_data = session.query(self.stats_table.amp1_even_med,
                                      self.stats_table.amp1_odd_med,
                                      self.stats_table.amp2_even_med,
                                      self.stats_table.amp2_odd_med,
                                      self.stats_table.amp3_even_med,
                                      self.stats_table.amp3_odd_med,
                                      self.stats_table.amp4_even_med,
                                      self.stats_table.amp4_odd_med,
                                      self.stats_table.expstart) \
            .filter(self.stats_table.aperture == aperture) \
            .order_by(self.stats_table.expstart) \
            .all()

        session.close()

        # Convert the query results to a pandas dataframe
        self.trending_data = pd.DataFrame(self.tmp_trending_data, columns=['amp1_even_med', 'amp1_odd_med',
                                                                  'amp2_even_med', 'amp2_odd_med',
                                                                  'amp3_even_med', 'amp3_odd_med',
                                                                  'amp4_even_med', 'amp3_odd_med',
                                                                  'expstart'])

    def retrieve_latest_data(self, aperture):
        """Query the database table to get the data needed for the non-trending
        plots. In this case, we need only the most recent entry
        """
        subq = (session.query(func.max(self.stats_table.expstart).label("max_created")) \
        .filter(self.stats_table.aperture == aperture) \
        .subquery()
        )

        query = (session.query(self.stats_table.uncal_filename,
                               self.stats_table.cal_filename,
                               self.stats_table.cal_image,
                               self.stats_table.expstart,
                               self.stats_table.collapsed_rows,
                               self.stats_table.collapsed_columns,
                               self.stats_table.counts,
                               self.stats_table.bin_centers)
                     .join(subq, self.stats_table.expstart == subq.c.max_created)
                     )

        latest_data = query.all()
        session.close()

        # Put the returned data in a dataframe
        self.latest_data = pd.DataFrame(latest_data, columns=['uncal_filename', 'cal_filename',
                                                              'cal_image', 'expstart', 'collapsed_rows',
                                                              'collapsed_columns', 'counts', 'bin_centers'])






class BiasMonitorPlots():
    """This is the top-level class, which will call the BiasMonitorData
    class to get results from the bias monitor, and use the plotting
    classes to create figures from the data.
    """
    def __init__(self, instrument):
        self.output_dir = os.path.join(OUTPUTS_DIR, 'bias_monitor')
        self.instrument = instrument
        self.trending_plots = {}
        self.zerothgroup_plots = {}
        self.rowcol_plots = {}
        self.histograms = {}

        # Get the data from the database
        self.db = BiasMonitorData(self.instrument)

        # Now we need to loop over the available apertures and create plots for each
        self.available_apertures = get_unique_values_per_column(self.db.stats_table, 'aperture')

        # Make sure all full frame apertures are present. If there are no data for a
        # particular full frame entry, then produce an empty plot, in order to
        # keep the plot layout consistent
        self.ensure_all_full_frame_apertures()

        # List of full frame aperture names
        full_apertures = FULL_FRAME_APERTURES[self.instrument.upper()]

        for aperture in self.available_apertures:
            self.aperture = aperture

            # Retrieve data from database.
            self.db.retrieve_trending_data(self.aperture)
            self.db.retrieve_latest_data(self.aperture)

            # Create trending plots. One for each amplifier.
            self.trending_plots[self.aperture] = TrendingPlot(self.db.trending_data).plots

            # Create a figure showing the zeroth group image
            self.zerothgroup_plots[self.apertre] = ZerothGroupImage(self.db.latest_data).figure

            # Create plots showing median row and column values
            self.rowcol_plots[self.aperture] = MedianRowColPlot(self.db.latest_data).plots

            # Create a plot of the histogram of the latest calibrated image
            self.histograms[self.aperture] = HistogramPlot(self.db.latest_data).plot

    def ensure_all_full_frame_apertures(self):
        """Be sure that self.available_apertures contains entires for all
        full frame apertures. These are needed to make sure the plot layout
        is consistent later
        """
        full_apertures = FULL_FRAME_APERTURES[self.instrument.upper()]
        for ap in full_apertures:
            if ap not in self.available_apertures:
                self.available_apertures.append(ap)



class HistogramPlot():
    """Class to create plots of histogram data
    """
    def __init__(self, data):
        self.data = data
        self.create_plot()

    def create_plot(self):
        """Create figure of data histogram
        """
        if len(self.data['expstart']) > 0:

            # In order to use Bokeh's quad, we need left and right bin edges, rather than bin centers
            half_widths = (self.data['bin_centers'][1:] - self.data['bin_centers'][0:-1]) / 2
            self.data['bin_left'] = self.data['bin_centers'] - half_widths
            self.data['bin_right'] = self.data['bin_centers'] + half_widths

            datestr = self.data['expstart'].strftime("%m/%d/%Y")
            self.plot = figure(title=f'Calibrated data: Histogram, {datestr}', tools='pan,box_zoom,reset,wheel_zoom,save',
                               background_fill_color="#fafafa")

            source = ColumnDataSource(self.data)
            self.plot.quad(top='counts', bottom=0, left='bin_left', right='bin_right',
                           fill_color="#C85108", line_color="white", alpha=0.5, source=source)

            ######################################
            # Do some testing and see if you need to set x and y ranges manually, like is done for the dark monitor trending plots

            hover_text = axis_text.split(' ')[0]
            hover_tool = HoverTool(tooltips=[(f'@bin_centers: @counts')])
            self.plot.tools.append(hover_tool)
        else:
            self.plot = figure(title=f'Calibrated data: Histogram', tools='pan,box_zoom,reset,wheel_zoom,save',
                               background_fill_color="#fafafa")

            # If there are no data, then create an empty placeholder plot
            self.plot.x_range.start = 0
            self.plot.x_range.end = 1
            self.plot.y_range.start = 0
            self.plot.y_range.end = 1

            source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
            glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
            self.plot.add_glyph(source, glyph)

        self.plot.xaxis.axis_label = 'Signal (DN)'
        self.plot.yaxis.axis_label = '# Pixels'


class MedianRowColPlot():
    """Class to create a plot of the median signal across rows
    or columns
    """
    def __init(self, data):
        self.data = data
        self.create_plots()

    def create_plots(self):
        """Create plots of median rows and columns
        """
        self.plots = {}
        for colname in ['collapsed_rows', 'collapsed_columns']:
            subframe = self.data[[colname, 'expstart']]
            self.plots[colname] = self.create_plot(subframe)

    def create_plot(self, frame):
        """Create a plot showing either the collapsed row or column info

        Parameters
        ----------
        frame : pandas.DataFrame
            Single column, containing the data to be plotted

        Returns
        -------
        plot : bokeh.plotting.figure
            Plot of the data contained in ``frame``
        """
        col = frame.columns[0]
        if 'row' in col.lower():
            title_text = 'Row'
            axis_text = 'Column Number'
        elif 'column' in col.lower():
            title_text = 'Column'
            axis_text = 'Row Number'

        datestr = frame['expstart'].strftime("%m/%d/%Y")
        plot = figure(title=f'Calibrated data: Collapsed {title_text}, {datestr}', tools='pan,box_zoom,reset,wheel_zoom,save',
                      background_fill_color="#fafafa")

        if len(frame[col]) > 0:

            # Add a column containing pixel numbers to plot against
            pix_num = np.arange(len(frame[col]))
            frame['pixel'] = pix_num

            source = ColumnDataSource(frame)
            plot.scatter(x='pixel', y=col, fill_color="#C85108", alpha=0.75, source=source)

            ######################################
            # Do some testing and see if you need to set x and y ranges manually, like is done for the dark monitor trending plots

            hover_text = axis_text.split(' ')[0]
            hover_tool = HoverTool(tooltips=[(f'{hover_text} @pixel: @col')])
            plot.tools.append(hover_tool)
        else:
            # If there are no data, then create an empty placeholder plot
            plot.x_range.start = 0
            plot.x_range.end = 1
            plot.y_range.start = 0
            plot.y_range.end = 1

            source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
            glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
            plot.add_glyph(source, glyph)

        plot.xaxis.axis_label = axis_text
        plot.yaxis.axis_label = 'Median Signal (DN)'

        return plot


class TrendingPlot():
    """Class to create trending plots of bias level over time. There should be
    4 plots produced: 1 for each amplifier (with even and odd columns plotted in each).

    Attributes
    ----------
    data : pandas.DataFrame
        Data to be plotted

    plots : dict
        Dictionary containing plots. Keys are amplifier numbers (1 - 4), and values are
        Bokeh figures containing the plots.
    """
    def __init__(self, data):
        self.data = data
        self.create_plots()

    def create_plots(self):
        """Create the 4 plots
        """
        self.plots = {}
        # Either all amps will have data, or all amps will be empty. No need to
        # worry about some amps having data but others not.
        # Create one plot per amplifier
        for amp_num in range(1, 5):
            cols_to_use = [col for col in self.data.columns if amp_num in col]
            cols_to_use.append('expstart')
            subframe = self.data[cols_to_use]
            self.plots[amp_num] = self.create_amp_plot(amp_num, subframe)

    def create_amp_plot(self, amp_num, amp_data):
        """Create a trending plot for a single amplifier

        Parameters
        ----------
        amp_num : int
            Amplifier number. 1 through 4

        amp_data : pandas.DataFrame
            DataFrame with trending data and dates for the amplifier

        Returns
        -------
        plot : bokeh.plotting.figure
            Figure containing the plot
        """
        plot = figure(title=f'Uncal data: Amp {amp_num}', tools='pan,box_zoom,reset,wheel_zoom,save',
                      background_fill_color="#fafafa")

        if len(self.data["expstart"]) > 0:
            source = ColumnDataSource(amp_data)
            even_col = f'amp{amp_num}_even_med'
            odd_col = f'amp{amp_num}_odd_med'

            plot.scatter(x='expstart', y=even_col, fill_color="#C85108", alpha=0.75, source=source, label='Even cols')
            plot.scatter(x='expstart', y=odd_col, fill_color="#355C7D", alpha=0.75, source=source, label='Odd cols')

            # Make the x axis tick labels look nice
            plot.xaxis.formatter = DatetimeTickFormatter(microseconds=["%d %b %H:%M:%S.%3N"],
                                                         seconds=["%d %b %H:%M:%S.%3N"],
                                                         hours=["%d %b %H:%M"],
                                                         days=["%d %b %H:%M"],
                                                         months=["%d %b %Y %H:%M"],
                                                         years=["%d %b %Y"]
                                                         )
            plot.xaxis.major_label_orientation = np.pi / 4

            ######################################
            # Do some testing and see if you need to set x and y ranges manually, like is done for the dark monitor trending plots

            hover_tool = HoverTool(tooltips=[('Even col bias:', f'@{even_col}'),
                                             ('Odd col bias:', f'@{odd_col}')
                                             ('Date:', '@expstart{%d %b %Y}')
                                             ]
                                   )
            hover_tool.formatters = {'@expstart': 'datetime'}
            plot.tools.append(hover_tool)
        else:
            # If there are no data, then create an empty placeholder plot
            plot.x_range.start = 0
            plot.x_range.end = 1
            plot.y_range.start = 0
            plot.y_range.end = 1

            source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
            glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
            plot.add_glyph(source, glyph)

        plot.xaxis.axis_label = 'Date'
        plot.yaxis.axis_label = 'Bias Level (DN)'

        return plot


class ZerothGroupImage():
    """Class to create an image to show the zeroth group of a
    calibrated dark file
    """
    def __init__(self, data):
        self.data = data
        self.create_figure()

    def create_figure(self):
        """Create the Bokeh figure
        """
        if os.path.isfile(self.data['cal_image']):
            image = read_png(self.data['cal_image'])

            datestr = self.data['expstart'].strftime("%m/%d/%Y")

            # Display the 32-bit RGBA image
            ydim, xdim = image.shape
            dim = max(xdim, ydim)
            self.figure = figure(title='Calibrated Zeroth Group of Most Recent Dark: {datestr}', x_range=(0, xdim), y_range=(0, ydim),
                                 tools='pan,box_zoom,reset,wheel_zoom,save')
            self.figure.image_rgba(image=[image], x=0, y=0, dw=xdim, dh=ydim)
            self.figure.xaxis.visible = False
            self.figure.yaxis.visible = False

        else:
            # If the given file is missing, create an empty plot
            self.empty_plot()


    def empty_plot(self):
        # If no mean image is given, create an empty figure
        self.figure = figure(title=self.aperture, tools='')
        self.figure.x_range.start = 0
        self.figure.x_range.end = 1
        self.figure.y_range.start = 0
        self.figure.y_range.end = 1

        source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
        glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
        self.figure.add_glyph(source, glyph)
        self.figure.xaxis.visible = False
        self.figure.yaxis.visible = False













class BiasMonitor(BokehTemplate):

    # Combine the input parameters into a single property because we
    # do not want to invoke the setter unless all are updated
    @property
    def input_parameters(self):
        return (self._instrument, self._aperture)

    @input_parameters.setter
    def input_parameters(self, info):
        self._instrument, self._aperture = info
        self.pre_init()
        self.post_init()

    def identify_tables(self):
        """Determine which database tables to use for the given instrument"""

        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.stats_table = eval('{}BiasStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get all of the relevant bias data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data in bias stats with a matching aperture,
        # and sort the data by exposure start time.
        self.query_results = session.query(self.stats_table) \
            .filter(self.stats_table.aperture == self._aperture) \
            .order_by(self.stats_table.expstart) \
            .all()

        session.close()

    def pre_init(self):

        # Start with default values for instrument and aperture because
        # BokehTemplate's __init__ method does not allow input arguments
        try:
            dummy_instrument = self._instrument
            dummy_aperture = self._aperture
        except AttributeError:
            self._instrument = 'NIRCam'
            self._aperture = ''

        self._embed = True
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, 'yaml', 'monitor_bias_interface.yaml')

    def post_init(self):

        # Load the bias data
        self.load_data()

        # Update the mean bias over time figures
        self.update_mean_bias_figures()

        # Update the calibrated 0th group image
        self.update_calibrated_image()

        # Update the histogram of the calibrated 0th group image
        if self._instrument == 'NIRISS':
            self.update_calibrated_histogram()

        # Update the calibrated collapsed values figures
        if self._instrument != 'NIRISS':
            self.update_collapsed_vals_figures()

    def update_calibrated_histogram(self):
        """Updates the calibrated 0th group histogram"""

        if len(self.query_results) != 0:
            # Get the most recent data; the entries were sorted by time when
            # loading the database, so the last entry will always be the most recent.
            counts = np.array(self.query_results[-1].counts)
            bin_centers = np.array(self.query_results[-1].bin_centers)

            # Update the calibrated image histogram
            self.refs['cal_hist_source'].data = {'counts': counts,
                                                 'bin_centers': bin_centers}
            self.refs['cal_hist_xr'].start = bin_centers.min()
            self.refs['cal_hist_xr'].end = bin_centers.max()
            self.refs['cal_hist_yr'].start = counts.min()
            self.refs['cal_hist_yr'].end = counts.max() + counts.max() * 0.05

    def update_calibrated_image(self):
        """Updates the calibrated 0th group image"""

        if len(self.query_results) != 0:
            # Get the most recent data; the entries were sorted by time when
            # loading the database, so the last entry will always be the most recent.
            cal_image_png = self.query_results[-1].cal_image
            cal_image_png = os.path.join('/static', '/'.join(cal_image_png.split('/')[-6:]))

            # Update the image source for the figure
            self.refs['cal_image'].image_url(url=[cal_image_png], x=0, y=0, w=2048, h=2048, anchor="bottom_left")

        # Update the calibrated image style
        self.refs['cal_image'].xaxis.visible = False
        self.refs['cal_image'].yaxis.visible = False
        self.refs['cal_image'].xgrid.grid_line_color = None
        self.refs['cal_image'].ygrid.grid_line_color = None
        self.refs['cal_image'].title.text_font_size = '22px'
        self.refs['cal_image'].title.align = 'center'

    def update_collapsed_vals_figures(self):
        """Updates the calibrated median-collapsed row and column figures"""

        if len(self.query_results) != 0:
            for direction in ['rows', 'columns']:
                # Get most recent data; the entries were sorted by time when
                # loading the database, so the last entry will always be the most recent.
                vals = np.array(self.query_results[-1].__dict__['collapsed_{}'.format(direction)])
                pixels = np.arange(len(vals))
                self.refs['collapsed_{}_source'.format(direction)].data = {'pixel': pixels,
                                                                           'signal': vals}

                # Update the pixel and signal limits
                self.refs['collapsed_{}_pixel_range'.format(direction)].start = pixels.min() - 10
                self.refs['collapsed_{}_pixel_range'.format(direction)].end = pixels.max() + 10
                self.refs['collapsed_{}_signal_range'.format(direction)].start = vals[4:2044].min() - 10  # excluding refpix
                self.refs['collapsed_{}_signal_range'.format(direction)].end = vals[4:2044].max() + 10

    def update_mean_bias_figures(self):
        """Updates the mean bias over time bokeh plots"""

        # Get the dark exposures and their starts times
        filenames = [os.path.basename(result.uncal_filename).replace('_uncal.fits', '') for result in self.query_results]
        expstarts_iso = np.array([result.expstart for result in self.query_results])
        expstarts = np.array([datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f') for date in expstarts_iso])

        # Update the mean bias figures for all amps and odd/even columns
        for amp in ['1', '2', '3', '4']:
            for kind in ['odd', 'even']:
                bias_vals = np.array([getattr(result, 'amp{}_{}_med'.format(amp, kind)) for result in self.query_results])
                self.refs['mean_bias_source_amp{}_{}'.format(amp, kind)].data = {'time': expstarts,
                                                                                 'time_iso': expstarts_iso,
                                                                                 'mean_bias': bias_vals,
                                                                                 'filename': filenames}
                self.refs['mean_bias_figure_amp{}_{}'.format(amp, kind)].title.text = 'Amp {} {}'.format(amp, kind.capitalize())
                self.refs['mean_bias_figure_amp{}_{}'.format(amp, kind)].hover.tooltips = [('file', '@filename'),
                                                                                           ('time', '@time_iso'),
                                                                                           ('bias level', '@mean_bias')]

                # Update plot limits if data exists
                if len(bias_vals) != 0:
                    self.refs['mean_bias_xr_amp{}_{}'.format(amp, kind)].start = expstarts.min() - timedelta(days=3)
                    self.refs['mean_bias_xr_amp{}_{}'.format(amp, kind)].end = expstarts.max() + timedelta(days=3)
                    min_val, max_val = min(x for x in bias_vals if x is not None), max(x for x in bias_vals if x is not None)
                    if min_val == max_val:
                        self.refs['mean_bias_yr_amp{}_{}'.format(amp, kind)].start = min_val - 1
                        self.refs['mean_bias_yr_amp{}_{}'.format(amp, kind)].end = max_val + 1
                    else:
                        offset = (max_val - min_val) * .1
                        self.refs['mean_bias_yr_amp{}_{}'.format(amp, kind)].start = min_val - offset
                        self.refs['mean_bias_yr_amp{}_{}'.format(amp, kind)].end = max_val + offset
