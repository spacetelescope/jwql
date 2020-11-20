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

        # Query filesystem_instrument
        # Get unique file types (Science, Cal, Dark, etc)
        # Get number of files per type
        # Make histogram/bar chart

        def _make_panel(data, filetypes, instrument):
            # filetypes = data.filetype.unique()
            p = figure(x_range=filetypes, title="File Types Counts", plot_width=850)
            p.vbar(x=filetypes, top=data, width=0.9, color='#6C5B7B')
            tab = Panel(child=p, title=instrument)
            
            return tab

        def _count_filetypes(data):
            print('count up filetypes')
            # filetypes = data.filetype.unique() # x 
            # filetype_count = [data.filetype.str.count('ft').sum() for ft in filetypes] # top

        # data = build_table('filesystem_instrument')
        # if not pd.isnull(self.date):
            # dt = Timedelta(1, units='days')
            # data = data[(data['start_time']>=self.date) & (data['start_time']<=self.date+dt)]

        # for instrument in data.instrument.unique():

        filetypes = ['sci', 'cal', 'dark']

        tab1 = _make_panel(np.random.rand(3)*10e7, filetypes, 'All')
        tab2 = _make_panel(np.random.rand(3)*10e7, filetypes, 'NIRCAM')
        tab3 = _make_panel(np.random.rand(3)*10e7, filetypes, 'NIRSPEC')
        tab4 = _make_panel(np.random.rand(3)*10e7, filetypes, 'MIRI')
        tab5 = _make_panel(np.random.rand(3)*10e7, filetypes, 'NIRISS')
        tab6 = _make_panel(np.random.rand(3)*10e7, filetypes, 'FGS')

        tabs = Tabs(tabs=[tab1, tab2, tab3, tab4, tab5, tab6])

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

        data = {'dates':[date(2020, 10, i+1) for i in range(30)],
                'numfiles':[i + randint(40, 150) for i in range(30)]}
        data['datestr'] = [date.strftime("%Y-%m-%d") for date in data['dates']]

        df = pd.DataFrame(data, columns=['dates', 'numfiles', 'datestr'])
        source = ColumnDataSource(df)
        p = figure(title="Number of Files Added by Day", tools="hover,tap", tooltips="@datestr: @numfiles")
        p.line(x='dates', y='numfiles', source=source, color='#6C5B7B', line_dash='dashed', line_width=3)

        url = "http://127.0.0.1:8000/daily_trending/@datestr"
        taptool = p.select(type=TapTool)
        taptool.callback = OpenURL(url=url)

        p.xaxis.formatter=DatetimeTickFormatter(
                hours=["%d %B %Y"],
                days=["%d %B %Y"],
                months=["%d %B %Y"],
                years=["%d %B %Y"],
            )
        p.xaxis.major_label_orientation = pi/4

        return p


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
