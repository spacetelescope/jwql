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
    - Bryan Hilbert

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
from operator import itemgetter
import os

from bokeh.layouts import column
from bokeh.models import Axis, ColumnDataSource, DatetimeTickFormatter, HoverTool, OpenURL, TapTool
from bokeh.models.layouts import TabPanel, Tabs
from bokeh.plotting import figure
from bokeh.transform import cumsum
import numpy as np
import pandas as pd
from sqlalchemy import func, and_

import jwql.database.database_interface as di
from jwql.database.database_interface import CentralStore
from jwql.utils.constants import ANOMALY_CHOICES_PER_INSTRUMENT, FILTERS_PER_INSTRUMENT, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_base_url, get_config
from jwql.website.apps.jwql.data_containers import build_table
from jwql.website.apps.jwql.models import Anomalies


def build_table_latest_entry(tablename):
    """Create Pandas dataframe from the most recent entry of a JWQLDB table.

    Parameters
    ----------
    tablename : str
        Name of JWQL database table name.

    Returns
    -------
    table_meta_data : pandas.DataFrame
        Pandas data frame version of JWQL database table.
    """
    # Make dictionary of tablename : class object
    # This matches what the user selects in the select element
    # in the webform to the python object on the backend.
    tables_of_interest = {}
    for item in di.__dict__.keys():
        table = getattr(di, item)
        if hasattr(table, '__tablename__'):
            tables_of_interest[table.__tablename__] = table

    session, _, _, _ = di.load_connection(get_config()['connection_string'])
    table_object = tables_of_interest[tablename]  # Select table object

    subq = session.query(table_object.instrument,
                         func.max(table_object.date).label('maxdate')
                         ).group_by(table_object.instrument).subquery('t2')

    result = session.query(table_object).join(
        subq,
        and_(
            table_object.instrument == subq.c.instrument,
            table_object.date == subq.c.maxdate
        )
    )

    # Turn query result into list of dicts
    result_dict = [row.__dict__ for row in result.all()]
    column_names = table_object.__table__.columns.keys()

    # Build list of column data based on column name.
    data = []
    for column in column_names:
        column_data = list(map(itemgetter(column), result_dict))
        data.append(column_data)

    data = dict(zip(column_names, data))

    # Build table.
    table_meta_data = pd.DataFrame(data)

    session.close()
    return table_meta_data


def create_filter_based_pie_chart(title, source):
    """
    """
    pie = figure(height=400, title=title, toolbar_location=None,
                 tools="hover", tooltips="@filter: @value", x_range=(-0.5, 0.5), y_range=(0.5, 1.5))

    pie.wedge(x=0, y=1, radius=0.3,
              start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
              line_color="white", fill_color='colors', source=source)

    pie.axis.axis_label = None
    pie.axis.visible = False
    pie.grid.grid_line_color = None
    return pie


def disable_scientific_notation(figure):
    """Disable y axis scientific notation.

    Parameters
    ----------
    figure: bokeh figure object
    """

    try:
        yaxis = figure.select(dict(type=Axis, layout="left"))[0]
        yaxis.formatter.use_scientific = False
    except IndexError:
        pass


"""
# Currently unused; preserved for reference when moving to bokeh 3
def treemap(df, col, x, y, dx, dy, *, N=100):
    sub_df = df.nlargest(N, col)
    normed = normalize_sizes(sub_df[col], dx, dy)
    blocks = squarify(normed, x, y, dx, dy)
    blocks_df = pd.DataFrame.from_dict(blocks).set_index(sub_df.index)
    return sub_df.join(blocks_df, how='left').reset_index()
"""


class GeneralDashboard:

    def __init__(self, delta_t=None):
        self.name = 'jwqldb_general_dashboard'
        self.delta_t = delta_t

        now = dt.now()
        self.date = pd.Timestamp('{}-{}-{}'.format(now.year, now.month, now.day))

    def dashboard_disk_usage(self):
        """Create trending plot of data volume for various disks. Here we are plotting
        the results of a "df -hk" call for top-level directories. The results (i.e. on
        central store) may contain contributions from non-JWQL files, since JWQL can
        share disks with other projects. These plots are useful for tracking disk usage
        and requesting more disk space if needed.

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            Set of tabs containing plots of the used and available disk space
        """
        # There are two main disks that we want to show usage for. The central store
        # area, and the disk that is internal to the server. Use the logs entry to
        # get the central store information, and the preview_image entry to get
        # server disk information.
        config = get_config()

        log_data = di.session.query(CentralStore.date, CentralStore.size, CentralStore.available) \
            .filter(CentralStore.area == 'logs') \
            .all()

        # Convert to dataframe
        log_data = pd.DataFrame(log_data)

        preview_data = di.session.query(CentralStore.date, CentralStore.size, CentralStore.available) \
            .filter(CentralStore.area == 'preview_images') \
            .all()

        # Convert to dataframe
        preview_data = pd.DataFrame(preview_data)

        # If the user is requesting a certain time range, cut down the entries
        if not pd.isnull(self.delta_t):
            log_data = log_data[(log_data['date'] >= self.date - self.delta_t) & (log_data['date'] <= self.date)]
            preview_data = preview_data[(preview_data['date'] >= self.date - self.delta_t) & (preview_data['date'] <= self.date)]

        log_results = {'dirname': os.path.abspath(os.path.join(config['log_dir'], '../')),
                       'results': log_data,
                       'shortname': 'Central Store'
                       }

        preview_results = {'dirname': os.path.abspath(os.path.join(config['preview_image_filesystem'], '../')),
                           'results': preview_data,
                           'shortname': 'Server'
                           }

        # Plot total data volume and available disk space versus time
        plots = {}
        hover_tool = {}
        tabs = []
        for data in [preview_results, log_results]:

            # Calculate the size of the data
            data['results']['used'] = data['results']['size'] - data['results']['available']
            source = ColumnDataSource(data['results'])

            # Initialize plot
            plots[data['shortname']] = figure(tools='pan,box_zoom,wheel_zoom,reset,save',
                                              width=800,
                                              x_axis_type='datetime',
                                              title=f"Available & Used Storage on {data['shortname']}",
                                              x_axis_label='Date',
                                              y_axis_label='Disk Space (TB)')

            plots[data['shortname']].line(x='date', y='available', source=source, legend_label='Available', line_dash='dashed', line_color='#C85108', line_width=3)
            plots[data['shortname']].circle(x='date', y='available', source=source,color='#C85108', size=10)
            plots[data['shortname']].line(x='date', y='used', source=source, legend_label='Used', line_dash='dashed', line_color='#355C7D', line_width=3)
            plots[data['shortname']].circle(x='date', y='used', source=source,color='#355C7D', size=10)

            plots[data['shortname']].xaxis.formatter = DatetimeTickFormatter(hours="%H:%M %d %B %Y",
                                                                             days="%d %B %Y",
                                                                             months="%d %B %Y",
                                                                             years="%B %Y"
                                                                             )
            plots[data['shortname']].xaxis.major_label_orientation = pi / 4
            plots[data['shortname']].legend.location = 'top_left'

            hover_tool[data['shortname']] = HoverTool(tooltips=[('Available:', '@available'),
                                                                ('Used:', '@used'),
                                                                ('Date:', '@date{%d %b %Y}')
                                                                ])
            hover_tool[data['shortname']].formatters = {'@date': 'datetime'}
            plots[data['shortname']].tools.append(hover_tool[data['shortname']])
            tabs.append(TabPanel(child=plots[data['shortname']], title=f"{data['shortname']} Storage"))

        tabs = Tabs(tabs=tabs)

        di.session.close()
        return tabs


    def dashboard_central_store_data_volume(self):
        """Create trending plot of data volume for various JWQL-related areas on disk.
        These plots show data volumes calculated by walking over subdirectories/files in
        the JWQL-specific directories. So these plots may not include the total used
        disk volume, in the cases where JWQL is sharing a disk with other projects. These
        plots are useful for monitoring the total volume of e.g. our preview images.

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each central store area
        """
        # Initialize plot
        plot = figure(tools='pan,box_zoom,wheel_zoom,reset,save',
                      width=800,
                      x_axis_type='datetime',
                      title='JWQL directory size',
                      x_axis_label='Date',
                      y_axis_label='Disk Space (TB)')

        # This part of the plot should cycle through areas and plot area used values vs. date
        #arealist = ['logs', 'outputs', 'test', 'preview_images', 'thumbnails', 'all']
        arealist = ['logs', 'outputs', 'preview_images', 'thumbnails']
        colors = ['#F8B195', '#F67280', '#6C5B7B', '#355C7D']
        for area, color in zip(arealist, colors):

            # Query for used sizes
            results = di.session.query(CentralStore.date, CentralStore.used).filter(CentralStore.area == area).all()

            if results:
                # Convert to dataframe
                results = pd.DataFrame(results)

                if not pd.isnull(self.delta_t):
                    results = results[(results['date'] >= self.date - self.delta_t) & (results['date'] <= self.date)]

                # Plot the results
                source = ColumnDataSource(results)
                plot.line(x='date', y='used', source=source, line_color=color, line_dash='dashed', legend_label=area, line_width=3)
                plot.circle(x='date', y='used', source=source, color=color, size=10)

                hover_tool = HoverTool(tooltips=[('Used:', f'@used TB'),
                                                 ('Date:', '@date{%d %b %Y}')
                                                 ])
                hover_tool.formatters = {'@date': 'datetime'}
                plot.tools.append(hover_tool)

        plot.xaxis.formatter = DatetimeTickFormatter(hours="%H:%M %d %B %Y",
                                                     days="%d %B %Y",
                                                     months="%d %B %Y",
                                                     years="%B %Y"
                                                     )
        plot.xaxis.major_label_orientation = pi / 4
        plot.legend.location = 'top_left'

        # Put the "all" plot in a separate figure because it will be larger than all the pieces, which would
        # throw off the y range if it were in a single plot
        cen_store_plot = figure(tools='pan,box_zoom,wheel_zoom,reset,save',
                                width=800,
                                x_axis_type='datetime',
                                title='JWQL central store directory, total data volume',
                                x_axis_label='Date',
                                y_axis_label='Disk Space (TB)')

        cen_store_results = di.session.query(CentralStore.date, CentralStore.used).filter(CentralStore.area == 'all').all()

        # Group by date
        if cen_store_results:

            # Convert to dataframe
            cen_store_results = pd.DataFrame(cen_store_results)

            if not pd.isnull(self.delta_t):
                cen_store_results = cen_store_results[(cen_store_results['date'] >= self.date - self.delta_t) & (cen_store_results['date'] <= self.date)]

            # Group by date
            cen_store_source = ColumnDataSource(cen_store_results)

            # Plot the results
            legend_str = 'File volume'
            cen_store_plot.line(x='date', y='used', source=cen_store_source, legend_label=legend_str, line_dash='dashed', line_color='#355C7D', line_width=3)
            cen_store_plot.circle(x='date', y='used', source=cen_store_source, color='#355C7D', size=10)
            cen_store_plot.xaxis.formatter = DatetimeTickFormatter(hours="%H:%M %d %B %Y",
                                                                   days="%d %B %Y",
                                                                   months="%d %B %Y",
                                                                   years="%B %Y"
                                                                   )
            cen_store_plot.xaxis.major_label_orientation = pi / 4
            cen_store_plot.legend.location = 'top_left'

            hover_tool = HoverTool(tooltips=[('Used:', f'@used TB'),
                                             ('Date:', '@date{%d %b %Y}')
                                             ])
            hover_tool.formatters = {'@date': 'datetime'}
            cen_store_plot.tools.append(hover_tool)

        di.session.close()
        return plot, cen_store_plot


    def dashboard_filetype_bar_chart(self):
        """Build bar chart of files based off of type

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each instrument.
        """

        # Make Pandas DF for filesystem_instrument
        # If time delta exists, filter data based on that.
        data = build_table('filesystem_instrument')

        # Keep only the rows containing the most recent timestamp
        data = data[data['date'] == data['date'].max()]
        date_string = data['date'].max().strftime("%d %b %Y")

        # Set title and figures list to make panels
        figures = []

        # For unique instrument values, loop through data
        # Find all entries for instrument/filetype combo
        # Make figure and append it to list.
        for instrument in data.instrument.unique():
            index = data["instrument"] == instrument
            inst_only = data[index].sort_values('filetype')
            title = f'{JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]} files per Filetype: {date_string}'
            figures.append(self.make_panel(inst_only['filetype'], inst_only['count'], instrument, title, 'File Type'))

        tabs = Tabs(tabs=figures)

        return tabs

    def dashboard_instrument_pie_chart(self):
        """Create piechart showing number of files per instrument

        Returns
        -------
        plot : bokeh.plotting.figure
            Pie chart figure
        """
        # Replace with jwql.website.apps.jwql.data_containers.build_table
        data = build_table('filesystem_instrument')

        # Keep only the rows containing the most recent timestamp
        data = data[data['date'] == data['date'].max()]
        date_string = data['date'].max().strftime("%d %b %Y")

        try:
            file_counts = {'nircam': data[data.instrument == 'nircam']['count'].sum(),
                           'nirspec': data[data.instrument == 'nirspec']['count'].sum(),
                           'niriss': data[data.instrument == 'niriss']['count'].sum(),
                           'miri': data[data.instrument == 'miri']['count'].sum(),
                           'fgs': data[data.instrument == 'fgs']['count'].sum()}
        except AttributeError:
            file_counts = {'nircam': 0,
                           'nirspec': 0,
                           'niriss': 0,
                           'miri': 0,
                           'fgs': 0}

        data = pd.Series(file_counts).reset_index(name='value').rename(columns={'index': 'instrument'})
        data['angle'] = data['value'] / data['value'].sum() * 2 * pi
        data['color'] = ['#F8B195', '#F67280', '#C06C84', '#6C5B7B', '#355C7D']
        plot = figure(title=f"Number of Files Per Instrument {date_string}", toolbar_location=None,
                      tools="hover,tap", tooltips="@instrument: @value", x_range=(-0.5, 1.0))

        plot.wedge(x=0, y=1, radius=0.4,
                   start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                   line_color="white", color='color', legend_label='instrument', source=data)

        url = "{}/@instrument".format(get_base_url())
        taptool = plot.select(type=TapTool)
        taptool.callback = OpenURL(url=url)

        plot.axis.axis_label = None
        plot.axis.visible = False
        plot.grid.grid_line_color = None

        return plot

    def dashboard_files_per_day(self):
        """Scatter of number of files per day added to ``JWQLDB``

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

        p1 = figure(title="Number of Files in Filesystem (MAST)", tools="reset,hover,box_zoom,wheel_zoom", tooltips="@datestr: @total_file_count", width=800, x_axis_label='Date', y_axis_label='Number of Files Added')
        p1.line(x='date', y='total_file_count', source=source, color='#6C5B7B', line_dash='dashed', line_width=3)
        p1.scatter(x='date', y='total_file_count', source=source, color='#C85108', size=10)
        disable_scientific_notation(p1)
        tab1 = TabPanel(child=p1, title='Files Per Day')

        # Create separate tooltip for storage plot.
        # Show date and used and available storage together

        p2 = figure(title="Available & Used Storage in Filesystem (MAST)", tools="reset,hover,box_zoom,wheel_zoom", tooltips="@datestr: @total_file_count", width=800, x_axis_label='Date', y_axis_label='Disk Space (TB)')
        p2.line(x='date', y='available', source=source, color='#C85108', line_dash='dashed', line_width=3, legend_label='Available Storage')
        p2.line(x='date', y='used', source=source, color='#355C7D', line_dash='dashed', line_width=3, legend_label='Used Storage')
        p2.scatter(x='date', y='available', source=source, color='#C85108', size=10)
        p2.scatter(x='date', y='used', source=source, color='#355C7D', size=10)
        disable_scientific_notation(p2)
        tab2 = TabPanel(child=p2, title='Storage')

        p1.xaxis.formatter = DatetimeTickFormatter(hours="%H:%M %d %B %Y",
                                                   days="%d %B %Y",
                                                   months="%d %B %Y",
                                                   years="%B %Y"
                                                   )
        p1.xaxis.major_label_orientation = pi / 4

        p2.xaxis.formatter = DatetimeTickFormatter(hours="%H:%M %d %B %Y",
                                                   days="%d %B %Y",
                                                   months="%d %B %Y",
                                                   years="%B %Y"
                                                   )
        p2.xaxis.major_label_orientation = pi / 4
        p2.legend.location = 'top_left'

        tabs = Tabs(tabs=[tab1, tab2])

        return tabs

    def dashboard_monitor_tracking(self):
        """Build bokeh table to show status and when monitors were
        run.

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

        # Sort the data by start_time before translating into strings
        data.sort_values(by='start_time', ascending=False, inplace=True)

        # Now translate times to strings
        data['start_time'] = data['start_time'].map(lambda x: x.strftime('%m-%d-%Y %H:%M:%S'))
        data['end_time'] = data['end_time'].map(lambda x: x.strftime('%m-%d-%Y %H:%M:%S'))

        return data.columns.values, data.values

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

        data = pd.Series(dict(zip(x_value, top))).reset_index(name='top').rename(columns={'index': 'x'})
        source = ColumnDataSource(data)
        plot = figure(x_range=x_value, title=title, width=850, tools="hover", tooltips="@x: @top", x_axis_label=x_axis_label)
        plot.vbar(x='x', top='top', source=source, width=0.9, color='#6C5B7B')
        plot.xaxis.major_label_orientation = pi / 4
        disable_scientific_notation(plot)
        tab = TabPanel(child=plot, title=instrument)

        return tab

    def dashboard_exposure_count_by_filter(self):
        """Create figure for number of files per filter for each JWST instrument.

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each instrument.
        """
        # build_table_latest_query will return only the database entries with the latest date. This should
        # correspond to one row/entry per instrument
        data = build_table_latest_entry('filesystem_characteristics')

        # Sort by instrument name so that the order of the tabs will always be the same
        data = data.sort_values('instrument')

        figures = []
        # This is a loop over instruments
        for i in range(len(data)):
            instrument = data.iloc[i]['instrument']
            filterpupil = np.array(data.iloc[i]['filter_pupil'])
            num_obs = np.array(data.iloc[i]['obs_per_filter_pupil'])

            # Sort by num_obs in order to make the plot more readable
            idx = np.argsort(num_obs)
            num_obs = num_obs[idx]
            filterpupil = filterpupil[idx]

            # Normalize the number of observations using each filter by the total number of observations
            total_obs = sum(num_obs)
            num_obs = num_obs / total_obs * 100.

            data_dict = {}
            for filt, val in zip(filterpupil, num_obs):
                data_dict[filt] = val

            inst_data = pd.Series(data_dict).reset_index(name='value').rename(columns={'index': 'filter'})

            if instrument != 'nircam':
                # Calculate the angle covered by each filter
                inst_data['angle'] = inst_data['value'] / inst_data['value'].sum() * 2 * np.pi

                # Keep all wedges the same color, except for those that are a very
                # small fraction, and will be covered in the second pie chart. Make
                # those wedges grey in the primary pie chart.
                inst_data['colors'] = ['#c85108'] * len(inst_data)
                inst_data.loc[inst_data['value'] < 0.5, 'colors'] = '#bec4d4'

                # Make a dataframe containing only the filters that are used in less
                # than some threshold percentage of observations
                small = inst_data.loc[inst_data['value'] < 0.5].copy()

                # Recompute the angles for these, and make them all the same color.
                small['angle'] = small['value'] / small['value'].sum() * 2 * np.pi
                small['colors'] = ['#bec4d4'] * len(small)

                # Create two pie charts
                pie_fig = create_filter_based_pie_chart("Percentage of observations using filter/pupil combinations: All Filters", inst_data)
                small_pie_fig = create_filter_based_pie_chart("Low Percentage Filters (gray wedges from above)", small)

                # Place the pie charts in a column/Panel, and append to the figure
                colplots = column(pie_fig, small_pie_fig)
                tab = TabPanel(child=colplots, title=f'{instrument}')
                figures.append(tab)

            else:
                # For NIRCam, we split the SW and LW channels and put each in its own tab.
                # This will cut down on the number of entries in each and make the pie
                # charts more readable.

                # Add a column designating the channel. Exclude darks.
                channel = []
                for f in filterpupil:
                    if 'FLAT' in f:
                        channel.append('Dark')
                    elif f[0] == 'F':
                        wav = int(f[1:4])
                        if wav < 220:
                            channel.append('SW')
                        else:
                            channel.append('LW')
                    else:
                        channel.append('SW')
                inst_data['channel'] = channel

                # Set the colors. All wedges with a pie chart have the same color.
                color_options = {'LW': '#c85108', 'SW': '#3d85c6', 'Dark': '#bec4d4'}
                colors = []
                for entry in channel:
                    colors.append(color_options[entry])
                inst_data['colors'] = colors

                # Even though it's not quite correct, create separate charts for SW vs LW. This will
                # hopefully make them much easier to read
                sw_data = inst_data.loc[inst_data['channel'] == 'SW'].copy()
                lw_data = inst_data.loc[inst_data['channel'] == 'LW'].copy()

                # Recalculate the angles. These won't be strictly correct since SW and LW filters
                # are not both used exactly 50% of the time, but it's close enough for now.
                sw_data['angle'] = sw_data['value'] / sw_data['value'].sum() * 2 * np.pi
                lw_data['angle'] = lw_data['value'] / lw_data['value'].sum() * 2 * np.pi

                # Zoomed in version of the small contributors
                sw_small = sw_data.loc[sw_data['value'] <0.5].copy()
                lw_small = lw_data.loc[lw_data['value'] <0.5].copy()
                sw_small['angle'] = sw_small['value'] / sw_small['value'].sum() * 2 * np.pi
                lw_small['angle'] = lw_small['value'] / lw_small['value'].sum() * 2 * np.pi
                sw_small['colors'] = ['#bec4d4'] * len(sw_small)
                lw_small['colors'] = ['#bec4d4'] * len(lw_small)

                # Set the filters that are used in less than 0.5% of observations to be grey.
                # These will be plotted in a second pie chart on theor own, in order to make
                # them more readable.
                sw_data.loc[sw_data['value'] < 0.5, 'colors'] = '#bec4d4'
                lw_data.loc[lw_data['value'] < 0.5, 'colors'] = '#bec4d4'

                """
                Would be nice to keep this treemap code somewhere, so that once we upgrade to
                bokeh 3.0, we can change the pie charts to treemaps, which should be easier to read
                #########treemap#######################
                ####treemap needs the squarify package, which would be a new dependency########
                ####https://docs.bokeh.org/en/3.0.0/docs/examples/topics/hierarchical/treemap.html###
                ####this also requires bokeh version > 3.0.0, so we need to hold off on this
                d = {'filter': filterpupil, 'num_obs': num_obs}
                df = pd.DataFrame(data=d)

                # only for nircam, add a column for LW/SW


                channel = []
                for f in filterpupil:
                    if 'FLAT' in f:
                        channel.append('Dark')
                    elif f[0] == 'F':
                        wav = int(f[1:4])
                        if wav < 220:
                            channel.append('SW')
                        else:
                            channel.append('LW')
                    else:
                        channel.append('SW')
                df['channel'] = channel

                filters = []
                pupils = []
                for f in filterpupil:
                    if f[0:3] != 'N/A':
                        filt, pup = f.split('/')
                        filters.append(filt)
                        pupils.append(pup)
                    else:
                        filters.append(f[0:3])
                        pupils.append(f[4:])
                df['filters'] = filters
                df['pupils'] = pupils

                regions = ('SW', 'LW', 'Dark')

                # Group by pupil value
                obs_by_pupil = df.groupby(["channel", "pupil"]).sum("num_obs")
                obs_by_pupil = obs_by_pupil.sort_values(by="num_obs").reset_index()

                # Get a total area for each channel
                obs_by_channel = df.groupby(["channel"]).sum("num_obs")

                # Figure size
                x, y, w, h = 0, 0, 800, 450

                blocks_by_channel= treemap(obs_by_channel, "num_obs", x, y, w, h)
                dfs = []
                for index, (channel, num_obs, x, y, dx, dy) in blocks_by_channel.iterrows():
                    df = obs_by_pupil[obs_by_pupil.channel==channel]
                    dfs.append(treemap(df, "num_obs", x, y, dx, dy, N=10))
                blocks = pd.concat(dfs)

                p = figure(width=w, height=h, tooltips="@pupil", toolbar_location=None,
                            x_axis_location=None, y_axis_location=None)
                p.x_range.range_padding = p.y_range.range_padding = 0
                p.grid.grid_line_color = None

                p.block('x', 'y', 'dx', 'dy', source=blocks, line_width=1, line_color="white",
                    fill_alpha=0.8, fill_color=factor_cmap("channel", "MediumContrast4", regions))

                p.text('x', 'y', x_offset=2, text="Channel", source=blocks_by_channel,
                   text_font_size="18pt", text_color="white")

                blocks["ytop"] = blocks.y + blocks.dy
                p.text('x', 'ytop', x_offset=2, y_offset=2, text="City", source=blocks,
                   text_font_size="6pt", text_baseline="top",
                   text_color=factor_cmap("Region", ("black", "white", "black", "white"), regions))

                show(p)
                """


                # Create pie charts for SW/LW, the main set of filters, and those that aren't used
                # as much.
                sw_pie_fig = create_filter_based_pie_chart("Percentage of observations using filter/pupil combinations: All Filters", sw_data)
                sw_small_pie_fig = create_filter_based_pie_chart("Low Percentage Filters (gray wedges from above)", sw_small)
                lw_pie_fig = create_filter_based_pie_chart("Percentage of observations using filter/pupil combinations: All Filters", lw_data)
                lw_small_pie_fig = create_filter_based_pie_chart("Low Percentage Filters (gray wedges from above)", lw_small)

                # Create columns and Panels
                sw_colplots = column(sw_pie_fig, sw_small_pie_fig)
                lw_colplots = column(lw_pie_fig, lw_small_pie_fig)

                tab_sw = TabPanel(child=sw_colplots, title=f'{instrument} SW')
                tab_lw = TabPanel(child=lw_colplots, title=f'{instrument} LW')
                figures.append(tab_sw)
                figures.append(tab_lw)

        # Add in a placeholder plot for FGS, in order to keep the page looking consistent
        # from instrument to instrument
        instrument = 'fgs'
        data_dict = {}
        data_dict['None'] = 100.
        inst_data = pd.Series(data_dict).reset_index(name='value').rename(columns={'index': 'filter'})
        inst_data['angle'] = 2 * np.pi
        inst_data['colors'] = ['#c85108']
        pie_fig = create_filter_based_pie_chart("FGS has no filters", inst_data)
        small_pie_fig = create_filter_based_pie_chart("FGS has no filters", inst_data)

        # Place the pie charts in a column/Panel, and append to the figure
        colplots = column(pie_fig, small_pie_fig)
        tab = TabPanel(child=colplots, title=f'{instrument}')
        figures.append(tab)

        tabs = Tabs(tabs=figures)

        return tabs


    def dashboard_anomaly_per_instrument(self):
        """Create figure for number of anamolies for each JWST instrument.

        Returns
        -------
        tabs : bokeh.models.widgets.widget.Widget
            A figure with tabs for each instrument.
        """

        # Set title and figures list to make panels
        title = 'Anomaly Types per Instrument'
        figures = []
        filter_kwargs={}

        # Make a tab for each instrument
        for instrument in ANOMALY_CHOICES_PER_INSTRUMENT.keys():
            # only show data for currently marked anomalies and current instrument
            filter_kwargs['root_file_info__instrument__iexact'] = instrument
            queryset = Anomalies.objects.filter(**filter_kwargs)

            # Convert the queryset to a Pandas DataFrame using only relevant columns
            labels = [anomaly_keys for anomaly_keys, values in ANOMALY_CHOICES_PER_INSTRUMENT[instrument]]
            data = pd.DataFrame.from_records(queryset.values(), columns=labels)

            # Sum columns to generate the bokeh panel
            summed_anomaly_columns = data.sum(axis=0, numeric_only=True).to_frame(name='counts')

            # Create plot of zeroes if empty (lookin at you FGS)
            if len(summed_anomaly_columns.index.values):
                plot_columns = summed_anomaly_columns.index.values
                summed_values = summed_anomaly_columns['counts']
            else:
                plot_columns = list(summed_anomaly_columns.index.values.base)
                summed_values = np.zeros(len(plot_columns))

            figures.append(self.make_panel(plot_columns, summed_values, instrument, title, 'Anomaly Type'))
        tabs = Tabs(tabs=figures)
        return tabs
