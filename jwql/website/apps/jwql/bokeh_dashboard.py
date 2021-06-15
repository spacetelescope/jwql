"""Bokeh based dashboard to monitor the status of the JWQL Application.
The dashboard tracks a variety of metrics including number of total
files per day, number of files per instrument, filesystem storage space,
etc.

The dashboard also includes a timestamp parameter. This allows users to
narrow metrics displayed by the dashboard to within a specific date
range.

Authors
-------

    - Mees B. Fix

Use
---

    The dashboard can be called from a python environment via the
    following import statements:
    ::

      from bokeh_dashboard impoer GeneralDashboard
      from monitor_template import secondary_function

Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``jwql`` directory.
"""

from datetime import datetime as dt
from math import pi

from bokeh.models import ColumnDataSource, DatetimeTickFormatter, OpenURL, TapTool
from bokeh.models.widgets import Panel, Tabs
from bokeh.plotting import figure
from bokeh.transform import cumsum
import numpy as np
import pandas as pd

from jwql.utils.constants import FILTERS_PER_INSTRUMENT
from jwql.utils.utils import get_base_url
from jwql.website.apps.jwql.data_containers import build_table


class GeneralDashboard:

    def __init__(self, delta_t=None):
        self.name = 'jwqldb_general_dashboard'
        self.delta_t = delta_t

        now = dt.now()
        self.date = pd.Timestamp('{}-{}-{}'.format(now.year, now.month, now.day))

    def dashboard_filetype_bar_chart(self):
        """Build bar chart of files based off of type

        Parameters
        ----------
        None

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each instrument.

        """

        # Make Pandas DF for filesystem_instrument
        # If time delta exists, filter data based on that.
        data = build_table('filesystem_instrument')
        if not pd.isnull(self.delta_t):
            data = data[(data['date'] >= (self.date - self.delta_t)) & (data['date'] <= self.date)]

        # Set title and figures list to make panels
        title = 'File Types per Instrument'
        figures = []

        # Group by instrument/filetype and sum the number of files that have that specific combination
        data_by_filetype = data.groupby(["instrument", "filetype"]).size().reset_index(name="count")

        # For unique instrument values, loop through data
        # Find all entries for instrument/filetype combo
        # Make figure and append it to list.
        for instrument in data.instrument.unique():
            index = data_by_filetype["instrument"] == instrument
            figures.append(self.make_panel(data_by_filetype['filetype'][index], data_by_filetype['count'][index], instrument, title, 'File Type'))

        tabs = Tabs(tabs=figures)

        return tabs

    def dashboard_instrument_pie_chart(self):
        """Create piechart showing number of files per instrument

        Parameters
        ----------
        None

        Returns
        -------
        plot : bokeh.plotting.figure
            Pie chart figure
        """

        # Replace with jwql.website.apps.jwql.data_containers.build_table
        data = build_table('filesystem_instrument')
        if not pd.isnull(self.delta_t):
            data = data[(data['date'] >= self.date - self.delta_t) & (data['date'] <= self.date)]

        try:
            file_counts = {'nircam': data.instrument.str.count('nircam').sum(),
                           'nirspec': data.instrument.str.count('nirspec').sum(),
                           'niriss': data.instrument.str.count('niriss').sum(),
                           'miri': data.instrument.str.count('miri').sum(),
                           'fgs': data.instrument.str.count('fgs').sum()}
        except AttributeError:
            file_counts = {'nircam': 0,
                           'nirspec': 0,
                           'niriss': 0,
                           'miri': 0,
                           'fgs': 0}

        data = pd.Series(file_counts).reset_index(name='value').rename(columns={'index': 'instrument'})
        data['angle'] = data['value'] / data['value'].sum() * 2 * pi
        data['color'] = ['#F8B195', '#F67280', '#C06C84', '#6C5B7B', '#355C7D']
        plot = figure(title="Number of Files Per Instruments", toolbar_location=None,
                      tools="hover,tap", tooltips="@instrument: @value", x_range=(-0.5, 1.0))

        plot.wedge(x=0, y=1, radius=0.4,
                   start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                   line_color="white", color='color', legend='instrument', source=data)

        url = "{}/@instrument".format(get_base_url())
        taptool = plot.select(type=TapTool)
        taptool.callback = OpenURL(url=url)

        plot.axis.axis_label = None
        plot.axis.visible = False
        plot.grid.grid_line_color = None

        return plot

    def dashboard_files_per_day(self):
        """Scatter of number of files per day added to ``JWQLDB``

        Parameters
        ----------
        None

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each instrument.
        """

        source = build_table('filesystem_general')
        if not pd.isnull(self.delta_t):
            source = source[(source['date'] >= self.date - self.delta_t) & (source['date'] <= self.date)]

        date_times = [pd.to_datetime(datetime).date() for datetime in source['date'].values]
        source['datestr'] = [date_time.strftime("%Y-%m-%d") for date_time in date_times]

        p1 = figure(title="Number of Files Added by Day", tools="reset,hover,box_zoom,wheel_zoom", tooltips="@datestr: @total_file_count", plot_width=1700, x_axis_label='Date', y_axis_label='Number of Files Added')
        p1.line(x='date', y='total_file_count', source=source, color='#6C5B7B', line_dash='dashed', line_width=3)
        tab1 = Panel(child=p1, title='Files Per Day')

        p2 = figure(title="Available & Used Storage", tools="reset,hover,box_zoom,wheel_zoom", tooltips="@datestr: @total_file_count", plot_width=1700, x_axis_label='Date', y_axis_label='Storage Space [Terabytes?]')
        p2.line(x='date', y='available', source=source, color='#F8B195', line_dash='dashed', line_width=3, legend='Available Storage')
        p2.line(x='date', y='used', source=source, color='#355C7D', line_dash='dashed', line_width=3, legend='Used Storage')
        tab2 = Panel(child=p2, title='Storage')

        p1.xaxis.formatter = DatetimeTickFormatter(hours=["%d %B %Y"],
                                                   days=["%d %B %Y"],
                                                   months=["%d %B %Y"],
                                                   years=["%d %B %Y"],
                                                   )
        p1.xaxis.major_label_orientation = pi / 4

        p2.xaxis.formatter = DatetimeTickFormatter(hours=["%d %B %Y"],
                                                   days=["%d %B %Y"],
                                                   months=["%d %B %Y"],
                                                   years=["%d %B %Y"],
                                                   )
        p2.xaxis.major_label_orientation = pi / 4

        tabs = Tabs(tabs=[tab1, tab2])

        return tabs

    def dashboard_monitor_tracking(self):
        """Build bokeh table to show status and when monitors were
        run.

        Parameters
        ----------
        None

        Returns
        -------
        table_columns : numpy.ndarray
            Numpy array of column names from monitor table.

        table_values : numpy.ndarray
            Numpy array of column values from monitor table.
        """

        data = build_table('monitor')

        if not pd.isnull(self.delta_t):
            data = data[(data['start_time'] >= self.date - self.delta_t) & (data['start_time'] <= self.date)]

        # data = data.drop(columns='affected_tables')
        table_values = data.sort_values(by='start_time', ascending=False).values
        table_columns = data.columns.values

        return table_columns, table_values

    def make_panel(self, x_value, top, instrument, title, x_axis_label):
        """Make tab panel for tablulated figure.

        Parameters
        ----------
        x_value : str
            Name of value for bar chart.
        top : int
            Sum associated with x_label
        instrument : str
            Title for the tab
        title : str
            Figure title
        x_axis_label : str
            Name of the x axis.

        Returns
        -------
        tab : bokeh.models.widgets.widget.Widget
            Return single instrument panel
        """
        # filetypes = data.filetype.unique()
        data = pd.Series(dict(zip(x_value, top))).reset_index(name='top').rename(columns={'index': 'x'})
        source = ColumnDataSource(data)
        plot = figure(x_range=x_value, title=title, plot_width=850, tools="hover", tooltips="@x: @top", x_axis_label=x_axis_label)
        plot.vbar(x='x', top='top', source=source, width=0.9, color='#6C5B7B')
        plot.xaxis.major_label_orientation = pi / 4
        tab = Panel(child=plot, title=instrument)

        return tab

    def dashboard_exposure_count_by_filter(self):
        """Create figure for number of files per filter for each JWST instrument.

        Parameters
        ----------
        None

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each instrument.
        """
        # for instrument in data.instrument.unique():
        title = 'File Counts Per Filter'
        figures = [self.make_panel(FILTERS_PER_INSTRUMENT[instrument], np.random.rand(len(FILTERS_PER_INSTRUMENT[instrument])) * 10e7, instrument, title, 'Filters') for instrument in FILTERS_PER_INSTRUMENT]

        tabs = Tabs(tabs=figures)

        return tabs

    def dashboard_anomaly_per_instrument(self):
        """Create figure for number of anamolies for each JWST instrument.

        Parameters
        ----------
        None

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each instrument.
        """
        from jwql.utils.constants import ANOMALY_CHOICES_PER_INSTRUMENT
        # Set title and figures list to make panels
        title = 'Anamoly Types per Instrument'
        figures = []

        # For unique instrument values, loop through data
        # Find all entries for instrument/filetype combo
        # Make figure and append it to list.
        for instrument in ANOMALY_CHOICES_PER_INSTRUMENT.keys():
            data = build_table('{}_anomaly'.format(instrument))
            data = data.drop(columns=['id', 'rootname', 'user'])
            if not pd.isnull(self.delta_t) and not data.empty:
                data = data[(data['flag_date'] >= (self.date - self.delta_t)) & (data['flag_date'] <= self.date)]
            summed_anamoly_columns = data.sum(axis=0).to_frame(name='counts')
            figures.append(self.make_panel(summed_anamoly_columns.index.values, summed_anamoly_columns['counts'], instrument, title, 'Anomaly Type'))

        tabs = Tabs(tabs=figures)

        return tabs
