
"""This module contains code for the bias monitor Bokeh plots.

Author
------

    - Ben Sunnquist
    - Maria A. Pena-Guerrero
    - Bryan Hilbert

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

from bokeh.embed import components, file_html
from bokeh.layouts import layout
from bokeh.models import ColorBar, ColumnDataSource, DatetimeTickFormatter, HoverTool, Legend, LinearAxis
from bokeh.models.widgets import Tabs, Panel
from bokeh.plotting import figure, output_file, save
from bokeh.resources import CDN
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from PIL import Image
from sqlalchemy import func

from jwql.bokeh_templating import BokehTemplate
from jwql.database.database_interface import get_unique_values_per_column, NIRCamBiasStats, NIRISSBiasStats, NIRSpecBiasStats, session
from jwql.utils.constants import FULL_FRAME_APERTURES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import read_png
from jwql.website.apps.jwql.bokeh_utils import PlaceholderPlot


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, '../templates')


class BiasMonitorData():
    """Class to hold bias data to be plotted

    Parameters
    ----------
    instrument : str
        Instrument name (e.g. nircam)

    Attributes
    ----------

    instrument : str
        Instrument name (e.g. nircam)

    latest_data : pandas.DataFrame
        Latest bias data for a particular aperture, from the
        stats_table

    stats_table : sqlalchemy.orm.decl_api.DeclarativeMeta
        Bias stats sqlalchemy table

    trending_data : pandas.DataFrame
        Data from the stats table to be used for the trending plot
    """
    def __init__(self, instrument):
        self.instrument = instrument
        self.identify_tables()

    def identify_tables(self):
        """Determine which database tables to use for the given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.stats_table = eval('{}BiasStats'.format(mixed_case_name))

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
        tmp_trending_data = session.query(self.stats_table.amp1_even_med,
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
        self.trending_data = pd.DataFrame(tmp_trending_data, columns=['amp1_even_med', 'amp1_odd_med',
                                                                      'amp2_even_med', 'amp2_odd_med',
                                                                      'amp3_even_med', 'amp3_odd_med',
                                                                      'amp4_even_med', 'amp4_odd_med',
                                                                      'expstart_str'])
        # Add a column of expstart values that are datetime objects
        format_data = "%Y-%m-%dT%H:%M:%S.%f"
        datetimes = [datetime.strptime(entry, format_data) for entry in self.trending_data['expstart_str']]
        self.trending_data['expstart'] = datetimes

    def retrieve_latest_data(self, aperture):
        """Query the database table to get the data needed for the non-trending
        plots. In this case, we need only the most recent entry.

        Parameters
        ----------
        aperture : str
            Aperture name (e.g. NRCA1_FULL)
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
                               self.stats_table.bin_centers,
                               self.stats_table.entry_date)
                     .order_by(self.stats_table.entry_date) \
                     .join(subq, self.stats_table.expstart == subq.c.max_created)
                     )

        latest_data = query.all()
        session.close()

        # Put the returned data in a dataframe. Include only the most recent entry.
        # The query has already filtered to include only entries using the latest
        # expstart value.
        self.latest_data = pd.DataFrame(latest_data[-1:], columns=['uncal_filename', 'cal_filename',
                                                                  'cal_image', 'expstart_str', 'collapsed_rows',
                                                                  'collapsed_columns', 'counts', 'bin_centers',
                                                                  'entry_date'])
        # Add a column of expstart values that are datetime objects
        format_data = "%Y-%m-%dT%H:%M:%S.%f"
        datetimes = [datetime.strptime(entry, format_data) for entry in self.latest_data['expstart_str']]
        self.latest_data['expstart'] = datetimes



class BiasMonitorPlots():
    """This is the top-level class, which will call the BiasMonitorData
    class to get results from the bias monitor, and use the plotting
    classes to create figures from the data.

    Paramters
    ---------
    instrument : str
        Instrument name (e.g. nircam)

    Attributes
    ----------

    aperture : str
        Aperture name (e.g. NRCA1_FULL)

    available_apertures : list
        List of apertures present in the data from the database

    div : str
        html div output by bokeh.components

    db : jwql.website.apps.jwql.monitor_bias_bokeh.BiasMonitorData
        Object containing data retrieved from the bias stats database table

    instrument : str
        Instrument name (e.g. nircam)

    histograms : dict
        Keys are aperture names, and values are corresponding Bokeh figures
        showing histograms of the signal in the dark exposure

    html_file: str
        Name of html file to save plots into

    rowcol_plots : dict
        Keys are aperture names, and values are corresponding Bokeh figures
        showing the mean row and column signal in the dark exposure

    script : str
        html script output by bokeh.components

    tabs: bokeh.models.widgets.Tabs
        Tabs object containing one Tab for each aperture's plots

    trending_plots : dict
        Keys are aperture names, and values are corresponding Bokeh figures
        of the bias level versus time

    zerothgroup_plots : dict
        Keys are aperture names, and values are corresponding Bokeh images
        of the zeroth frames from dark exposures
    """
    def __init__(self, instrument):
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

        for aperture in self.available_apertures:
            self.aperture = aperture

            # Retrieve data from database.
            self.db.retrieve_trending_data(self.aperture)
            self.db.retrieve_latest_data(self.aperture)

            # Create trending plots. One for each amplifier.
            self.trending_plots[self.aperture] = TrendingPlot(self.db.trending_data).plots

            # Create a figure showing the zeroth group image
            self.zerothgroup_plots[self.aperture] = ZerothGroupImage(self.db.latest_data).figure

            # Create plots showing median row and column values
            self.rowcol_plots[self.aperture] = MedianRowColPlot(self.db.latest_data).plots

            # Create a plot of the histogram of the latest calibrated image
            self.histograms[self.aperture] = HistogramPlot(self.db.latest_data).plot

        # Organize plots into tabs
        self.create_tabs()

        # Save the tabbed plots using bokeh
        self.save_tabs()

        # Modify the saved html file such that it works in our Django ecosystem
        self.modify_bokeh_saved_html()

    def create_tabs(self):
        """Organize the plots into a separate tab for each aperture
        """
        tabs = []
        for aperture in FULL_FRAME_APERTURES[self.instrument.upper()]:

            bias_layout = layout([[self.trending_plots[aperture][1], self.trending_plots[aperture][2]],
                                  [self.trending_plots[aperture][3], self.trending_plots[aperture][4]],
                                  [self.zerothgroup_plots[aperture], self.histograms[aperture]],
                                  [self.rowcol_plots[aperture]['collapsed_rows'], self.rowcol_plots[aperture]['collapsed_columns']]
                                  ]
                                 )
            bias_layout.sizing_mode = 'scale_width'
            bias_tab = Panel(child=bias_layout, title=aperture)
            tabs.append(bias_tab)

        # Build tabs
        self.tabs = Tabs(tabs=tabs)
        self.script, self.div = components(self.tabs)

    def ensure_all_full_frame_apertures(self):
        """Be sure that self.available_apertures contains entires for all
        full frame apertures. These are needed to make sure the plot layout
        is consistent later
        """
        full_apertures = FULL_FRAME_APERTURES[self.instrument.upper()]
        for ap in full_apertures:
            if ap not in self.available_apertures:
                self.available_apertures.append(ap)

    def modify_bokeh_saved_html(self):
        """Given an html string produced by Bokeh when saving bad pixel monitor plots,
        make tweaks such that the page follows the general JWQL page formatting.
        """
        # Insert into our html template and save
        temp_vars = {'inst': self.instrument, 'plot_script': self.script, 'plot_div': self.div}
        html_lines = file_html(self.tabs, CDN, f'{self.instrument} bias monitor', self.html_file, temp_vars)

        lines = html_lines.split('\n')

        # List of lines that Bokeh likes to save in the file, but we don't want
        lines_to_remove = ["<!DOCTYPE html>",
                           '<html lang="en">',
                           '  </body>',
                           '</html>']

        # Our Django-related lines that need to be at the top of the file
        hstring = """href="{{'/jwqldb/%s_bias_stats'%inst.lower()}}" name=test_link class="btn btn-primary my-2" type="submit">Go to JWQLDB page</a>"""
        newlines = ['{% extends "base.html" %}\n', "\n",
                    "{% block preamble %}\n", "\n",
                    f"<title>{JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bias Monitor- JWQL</title>\n", "\n",
                    "{% endblock %}\n", "\n",
                    "{% block content %}\n", "\n",
                    '  <main role="main" class="container">\n', "\n",
                    f"  <h1>{JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bias Monitor</h1>\n",
                    "  <hr>\n",
                    f"  <b>View or Download {JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bias Stats Table:</b>&emsp; <a " + hstring,
                    "  <hr>\n"
                    ]

        # More lines that we want to have in the html file, at the bottom
        endlines = ["\n",
                    "</main>\n", "\n",
                    "{% endblock %}"
                    ]

        for line in lines:
            if line not in lines_to_remove:
                newlines.append(line + '\n')
        newlines = newlines + endlines

        html_lines = "".join(newlines)

        # Save the modified html
        with open(self.html_file, "w") as file:
            file.write(html_lines)
        set_permissions(self.html_file)

    def save_tabs(self):
        """Save the Bokeh tabs to an html file
        """
        self.html_file = os.path.join(TEMPLATE_DIR, f'{self.instrument.lower()}_bias_plots.html')
        output_file(self.html_file)
        save(self.tabs)
        set_permissions(self.html_file)


class HistogramPlot():
    """Class to create histogram plots of bias data

    Parameters
    ----------
    data : pandas.DataFrame
        Data to be plotted. Required columns include bin_right, bin_left,
        counts, expstart_str

    Attributes
    ----------
    data : pandas.DataFrame
        Data to be plotted. Required columns include bin_right, bin_left,
        counts, expstart_str

    plot : bokeh.plotting.figure
        Figure containing the histogram plot
    """
    def __init__(self, data):
        self.data = data
        self.create_plot()

    def create_plot(self):
        """Create figure of data histogram
        """
        x_label = 'Signal (DN)'
        y_label = '# Pixels'
        if len(self.data['counts'].iloc[0]) > 0:

            # In order to use Bokeh's quad, we need left and right bin edges, rather than bin centers
            bin_centers = np.array(self.data['bin_centers'][0])
            half_widths = (bin_centers[1:] - bin_centers[0:-1]) / 2
            half_widths = np.insert(half_widths, 0, half_widths[0])
            self.data['bin_left'] = [bin_centers - half_widths]
            self.data['bin_right'] = [bin_centers + half_widths]

            datestr = self.data['expstart_str'].iloc[0]
            self.plot = figure(title=f'Calibrated data: Histogram, {datestr}', tools='pan,box_zoom,reset,wheel_zoom,save',
                               background_fill_color="#fafafa")

            # Keep only the columns where the data are a list
            series = self.data.iloc[0]
            series = series[['counts', 'bin_left', 'bin_right', 'bin_centers']]
            source = ColumnDataSource(dict(series))
            self.plot.quad(top='counts', bottom=0, left='bin_left', right='bin_right',
                           fill_color="#C85108", line_color="#C85108", alpha=0.75, source=source)

            hover_tool = HoverTool(tooltips=f'@bin_centers DN: @counts')
            self.plot.tools.append(hover_tool)
            self.plot.xaxis.axis_label = x_label
            self.plot.yaxis.axis_label = y_label

        else:
            self.plot = PlaceholderPlot('Calibrated data: Histogram', x_label, y_label).plot



class MedianRowColPlot():
    """Class to create a plot of the median signal across rows
    or columns

    Parameters
    ----------
    data : pandas.DataFrame
        Data to be plotted. Required columns include bin_right, bin_left,
        counts, expstart_str

    Attributes
    ----------
    data : pandas.DataFrame
        Data to be plotted. Required columns include bin_right, bin_left,
        counts, expstart_str

    plots : dict
        Dictionary containing plots. Keys are 'collapsed_rows' and 'collapsed_columns',
        and the values are the Bokeh figures
    """
    def __init__(self, data):
        self.data = data
        self.create_plots()

    def create_plots(self):
        """Create plots of median rows and columns
        """
        self.plots = {}
        for colname in ['collapsed_rows', 'collapsed_columns']:
            self.plots[colname] = self.create_plot(colname)

    def create_plot(self, colname):
        """Create a plot showing either the collapsed row or column info

        Parameters
        ----------
        frame : pandas.DataFrame
            Single column, containing the data to be plotted

        colname : str
            Column name from DataFrame containing data to be plotted

        Returns
        -------
        plot : bokeh.plotting.figure
            Plot of the data contained in ``frame``
        """
        if 'row' in colname.lower():
            title_text = 'Row'
            axis_text = 'Column Number'
        elif 'column' in colname.lower():
            title_text = 'Column'
            axis_text = 'Row Number'

        #datestr = self.data['expstart'][0].strftime("%m/%d/%Y")
        datestr = self.data['expstart_str'].iloc[0]
        title_str = f'Calibrated data: Collapsed {title_text}, {datestr}'

        if len(self.data[colname].iloc[0]) > 0:
            plot = figure(title=title_str, tools='pan,box_zoom,reset,wheel_zoom,save',
                          background_fill_color="#fafafa")

            # Add a column containing pixel numbers to plot against
            pix_num = np.arange(len(self.data[colname].iloc[0]))
            self.data['pixel'] = [pix_num]

            series = self.data.iloc[0]
            series = series[['pixel', colname]]
            source = ColumnDataSource(dict(series))
            plot.scatter(x='pixel', y=colname, fill_color="#C85108", line_color="#C85108",
                         alpha=0.75, source=source)

            hover_text = axis_text.split(' ')[0]
            hover_tool = HoverTool(tooltips=f'{hover_text} @pixel: @{colname}')
            plot.tools.append(hover_tool)
            plot.xaxis.axis_label = axis_text
            plot.yaxis.axis_label = 'Median Signal (DN)'
        else:
            # If there are no data, then create an empty placeholder plot
            plot = PlaceholderPlot(title_str, axis_text, 'Median Signal (DN)').plot

        return plot



class TrendingPlot():
    """Class to create trending plots of bias level over time. There should be
    4 plots produced: 1 for each amplifier (with even and odd columns plotted in each).

    Parameters
    ----------
    data : pandas.DataFrame
        Data to be plotted

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
        title_str = f'Uncal data: Amp {amp_num}'
        x_label = 'Date'
        y_label = 'Bias Level (DN)'

        if len(amp_data["expstart"]) > 0:
            plot = figure(title=title_str, tools='pan,box_zoom,reset,wheel_zoom,save',
                      background_fill_color="#fafafa")
            source = ColumnDataSource(amp_data)
            even_col = f'amp{amp_num}_even_med'
            odd_col = f'amp{amp_num}_odd_med'

            plot.scatter(x='expstart', y=even_col, fill_color="#C85108", line_color="#C85108",
                         alpha=0.75, source=source, legend_label='Even cols')
            plot.scatter(x='expstart', y=odd_col, fill_color="#355C7D", line_color="#355C7D",
                         alpha=0.75, source=source, legend_label='Odd cols')

            # Make the x axis tick labels look nice
            plot.xaxis.formatter = DatetimeTickFormatter(microseconds=["%d %b %H:%M:%S.%3N"],
                                                         seconds=["%d %b %H:%M:%S.%3N"],
                                                         hours=["%d %b %H:%M"],
                                                         days=["%d %b %H:%M"],
                                                         months=["%d %b %Y %H:%M"],
                                                         years=["%d %b %Y"]
                                                         )
            plot.xaxis.major_label_orientation = np.pi / 4

            # Use the string representation of the time in the hover tool, rather than the
            # datetime version. If you use the datetime version, and save this information
            # to the html file, when trying to read and display the html file, jinja will
            # interpret the format codes as html tags and crash with errors such as:
            # "Encountered unknown tag 'd'. Jinja was looking for the following tags: 'endblock'.
            # The innermost block that needs to be closed is 'block'"
            hover_tool = HoverTool(tooltips=[('Even col bias:', f'@{even_col}'),
                                             ('Odd col bias:', f'@{odd_col}'),
                                             ('Date:', '@expstart_str')
                                             ]
                                   )
            hover_tool.formatters = {'@expstart': 'datetime'}
            plot.tools.append(hover_tool)
            plot.xaxis.axis_label = x_label
            plot.yaxis.axis_label = y_label
        else:
            # If there are no data, then create an empty placeholder plot
            plot = PlaceholderPlot(title_str, x_label, y_label).plot

        return plot

    def create_plots(self):
        """Create the 4 plots
        """
        self.plots = {}
        # Either all amps will have data, or all amps will be empty. No need to
        # worry about some amps having data but others not.
        # Create one plot per amplifier
        for amp_num in range(1, 5):
            cols_to_use = [col for col in self.data.columns if str(amp_num) in col]
            cols_to_use.append('expstart')
            subframe = self.data[cols_to_use]
            self.plots[amp_num] = self.create_amp_plot(amp_num, subframe)


class ZerothGroupImage():
    """Class to create an image to show the zeroth group of a
    calibrated dark file

    Parameters
    ----------
    data : pandas.DataFrame
        Data to be plotted. Required columns include bin_right, bin_left,
        counts, expstart_str

    Attributes
    ----------
    data : pandas.DataFrame
        Data to be plotted. Required columns include bin_right, bin_left,
        counts, expstart_str

    figure : bokeh.plotting.figure
        Figure containing an image
    """
    def __init__(self, data):
        self.data = data
        self.create_figure()

    def create_figure(self):
        """Create the Bokeh figure
        """
        if len(self.data['cal_image']) > 0 and os.path.isfile(self.data['cal_image'].iloc[0]):
            image = read_png(self.data['cal_image'].iloc[0])

            datestr = self.data['expstart_str'].iloc[0]

            # Display the 32-bit RGBA image
            ydim, xdim = image.shape
            dim = max(xdim, ydim)
            self.figure = figure(title=f'Calibrated Zeroth Group of Most Recent Dark: {datestr}', x_range=(0, xdim), y_range=(0, ydim),
                                 tools='pan,box_zoom,reset,wheel_zoom,save')
            self.figure.image_rgba(image=[image], x=0, y=0, dw=xdim, dh=ydim)
            self.figure.xaxis.visible = False
            self.figure.yaxis.visible = False

        else:
            # If the given file is missing, create an empty plot
            self.figure = PlaceholderPlot('Calibrated Zeroth Group of Most Recent Dark', '', '').plot
            self.figure.xaxis.visible = False
            self.figure.yaxis.visible = False
