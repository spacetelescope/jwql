"""Containers for Bokeh Dashboard
"""
from datetime import date
from datetime import datetime as dt
from math import pi
from operator import itemgetter
from random import randint

import pandas as pd
from pandas._libs.tslibs.timestamps import Timestamp, Timedelta

from bokeh.embed import components
from bokeh.io import output_file, show
from bokeh.plotting import figure
from bokeh.transform import cumsum
from bokeh.layouts import widgetbox
from bokeh.models import ColumnDataSource
from bokeh.models import DatetimeTickFormatter
from bokeh.models import TapTool, OpenURL
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn, Panel, Tabs
from bokeh.layouts import grid, column, row, layout

from jwql.database.database_interface import load_connection
from jwql.utils.utils import get_config
from jwql.database.database_interface import Monitor, FilesystemInstrument
from jwql.website.apps.jwql.data_containers import build_table


class generalDashboard:

    def __init__(self, date=None):
        self.name = 'jwqldb_general_dashboard'
        self.date = Timestamp(date)


    def dashboard_filetype_bar_chart(self):
        """Build bar chart of files based off of type
        """

        import numpy as np
        from jwql.utils.constants import GENERIC_SUFFIX_TYPES, GUIDER_SUFFIX_TYPES
        # Query filesystem_instrument
        # Get unique file types (Science, Cal, Dark, etc)
        # Get number of files per type
        # Make histogram/bar chart

        data = build_table('filesystem_instrument')
        if not pd.isnull(self.date):
            dt = Timedelta(1, unit='d')
            print(self.date, dt, self.date+dt)
            data = data[(data['date']>=self.date) & (data['date']<=self.date+dt)]


        # for instrument in data.instrument.unique():
        title = 'File Types per Instrument'
        figures = []

        data = data.groupby(['instrument', 'filetype', 'count']).size().reset_index(name='group_count')
        print(data)
        for instrument in ['fgs', 'miri', 'nircam', 'niriss', 'nirspec']:
            instrument_data = data[data['instrument'] == instrument]
            figures.append(self.make_panel(instrument_data['filetype'], instrument_data['count'], instrument, title, 'Filetypes'))

        tabs = Tabs(tabs=figures)

        return tabs


    def dashboard_instrument_pie_chart(self):
        """Create piechart showing number of files per instrument
        """

        # Replace with jwql.website.apps.jwql.data_containers.build_table
        # data = build_table('filesystem_instrument')
        # if not pd.isnull(self.date):
        #     dt = Timedelta(1, units='day')
        #     data = data[(data['start_time']>=self.date) & (data['start_time']<=self.date+dt)]
        # x = {'nircam': data.instrument.str.count('nircam').sum(),
        #      'nirspec': data.instrument.str.count('nirspec').sum(),
        #      'niriss': data.instrument.str.count('niriss').sum(),
        #      'miri': data.instrument.str.count('miri').sum(),
        #      'fgs': data.instrument.str.count('fgs').sum()}

        x = {'nircam': 400,
             'nirspec': 250,
             'miri': 160,
             'niriss': 110,
             'fgs': 90}

        data = pd.Series(x).reset_index(name='value').rename(columns={'index':'instrument'})
        data['angle'] = data['value']/data['value'].sum() * 2*pi
        data['color'] = ['#F8B195', '#F67280', '#C06C84', '#6C5B7B', '#355C7D']
        p = figure(title="Number of Files Per Instruments", toolbar_location=None,
                tools="hover,tap", tooltips="@instrument: @value", x_range=(-0.5, 1.0))

        p.wedge(x=0, y=1, radius=0.4,
                start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                line_color="white", color='color', legend='instrument', source=data)

        url = "http://127.0.0.1:8000/@instrument"
        taptool = p.select(type=TapTool)
        taptool.callback = OpenURL(url=url)
        
        p.axis.axis_label=None
        p.axis.visible=False
        p.grid.grid_line_color = None

        return p


    def dashboard_files_per_day(self):
        """Scatter of number of files per day added to JWQLDB
        """

        source = build_table('filesystem_general')
        date_times = [pd.to_datetime(datetime).date() for datetime in source['date'].values]
        source['datestr'] = [date_time.strftime("%Y-%m-%d") for date_time in date_times]

        p1 = figure(title="Number of Files Added by Day", tools="hover,tap", tooltips="@datestr: @total_file_count", plot_width=1700, x_axis_label='Date', y_axis_label='Number of Files Added')
        p1.line(x='date', y='total_file_count', source=source, color='#6C5B7B', line_dash='dashed', line_width=3)
        tab1 = Panel(child=p1, title='Files Per Day')

        p2 = figure(title="Available & Used Storage", tools="hover,tap", tooltips="@datestr: @total_file_count", plot_width=1700, x_axis_label='Date', y_axis_label='Storage Space [Terabytes?]')
        p2.line(x='date', y='available', source=source, color='#F8B195', line_dash='dashed', line_width=3, legend='Available Storage')
        p2.line(x='date', y='used', source=source, color='#355C7D', line_dash='dashed', line_width=3, legend='Used Storage')
        tab2 = Panel(child=p2, title='Storage')

        url = "http://127.0.0.1:8000/daily_trending/@datestr"
        taptool = p1.select(type=TapTool)
        taptool.callback = OpenURL(url=url)

        p1.xaxis.formatter=DatetimeTickFormatter(
                hours=["%d %B %Y"],
                days=["%d %B %Y"],
                months=["%d %B %Y"],
                years=["%d %B %Y"],
            )
        p1.xaxis.major_label_orientation = pi/4

        p2.xaxis.formatter=DatetimeTickFormatter(
                hours=["%d %B %Y"],
                days=["%d %B %Y"],
                months=["%d %B %Y"],
                years=["%d %B %Y"],
            )
        p2.xaxis.major_label_orientation = pi/4

        tabs = Tabs(tabs=[tab1, tab2]) 
        return tabs


    def dashboard_monitor_tracking(self):
        """Build bokeh table to show status and when monitors were run.
        """

        data = build_table('monitor')

        if not pd.isnull(self.date):
            dt = self.date + Timedelta(1, unit='D')
            data = data[(data['start_time']>=self.date) & (data['start_time']<=dt)]

        data = data.drop(columns='affected_tables')
        table_values = data.sort_values(by='start_time', ascending=False).values
        table_columns = data.columns.values

        return table_columns, table_values


    def make_panel(self, x, top, instrument, title, x_axis_label):
            # filetypes = data.filetype.unique()
            s = pd.Series(dict(zip(x, top))).reset_index(name='top').rename(columns={'index':'x'})
            source = ColumnDataSource(s)
            p = figure(x_range=x, title=title, plot_width=850, tools="hover", tooltips="@x: @top", x_axis_label=x_axis_label)
            p.vbar(x='x', top='top', source=source, width=0.9, color='#6C5B7B')
            p.xaxis.major_label_orientation = pi/4
            tab = Panel(child=p, title=instrument)

            return tab


    def dashboard_exposure_count_by_filter(self):

        import numpy as np
        from jwql.utils.constants import FILTERS_PER_INSTRUMENT
        # Query filesystem_instrument
        # Get unique file types (Science, Cal, Dark, etc)
        # Get number of files per type
        # Make histogram/bar chart

        def _count_filetypes(data):
            print('count up filetypes')
            # filetypes = data.filetype.unique() # x 
            # filetype_count = [data.filetype.str.count('ft').sum() for ft in filetypes] # top

        # data = build_table('filesystem_instrument')
        # if not pd.isnull(self.date):
            # dt = Timedelta(1, units='days')
            # data = data[(data['start_time']>=self.date) & (data['start_time']<=self.date+dt)]

        # for instrument in data.instrument.unique():
        title = 'File Counts Per Filter'
        figures = [self.make_panel(FILTERS_PER_INSTRUMENT[instrument], np.random.rand(len(FILTERS_PER_INSTRUMENT[instrument]))*10e7, instrument, title, 'Filters') for instrument in FILTERS_PER_INSTRUMENT]

        tabs = Tabs(tabs=figures)

        return tabs


    def dashboard_anomaly_per_instrument(self):

        import numpy as np
        from jwql.utils.constants import ANOMALY_CHOICES_PER_INSTRUMENT
        # Query filesystem_instrument
        # Get unique file types (Science, Cal, Dark, etc)
        # Get number of files per type
        # Make histogram/bar chart

        # query_name = {instrument: list(zip(*ANOMALY_CHOICES_PER_INSTRUMENT[instrument]))[0] for instrument in ANOMALY_CHOICES_PER_INSTRUMENT}
        display_name = {instrument: list(zip(*ANOMALY_CHOICES_PER_INSTRUMENT[instrument]))[1] for instrument in ANOMALY_CHOICES_PER_INSTRUMENT}

        def _count_filetypes(data):
            print('count up filetypes')
            # filetypes = data.filetype.unique() # x 
            # filetype_count = [data.filetype.str.count('ft').sum() for ft in filetypes] # top

        # data = build_table('filesystem_instrument')
        # if not pd.isnull(self.date):
            # dt = Timedelta(1, units='days')
            # data = data[(data['start_time']>=self.date) & (data['start_time']<=self.date+dt)]

        # for instrument in data.instrument.unique():
        title = 'Anomaly Type By Instrument'
        figures = [self.make_panel(display_name[instrument], np.random.rand(len(display_name[instrument]))*10e7, instrument, title, 'Anomaly Type') for instrument in display_name]
        tabs = Tabs(tabs=figures)

        return tabs
