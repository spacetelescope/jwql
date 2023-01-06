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

from bokeh.layouts import row
from bokeh.models import Axis, ColumnDataSource, DatetimeTickFormatter, OpenURL, TapTool
from bokeh.models.widgets import Panel, Tabs
from bokeh.plotting import figure
from bokeh.transform import cumsum
import numpy as np
import pandas as pd
from sqlalchemy import func, and_

from jwql.utils.constants import ANOMALY_CHOICES_PER_INSTRUMENT, FILTERS_PER_INSTRUMENT
from jwql.utils.utils import get_base_url, map_filterpupil_name_to_wavelength
from jwql.website.apps.jwql.data_containers import build_table


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

    session, _, _, _ = load_connection(get_config()['connection_string'])
    table_object = tables_of_interest[tablename]  # Select table object

    subq = session.query(table_object.instrument,
                         func.max(table_object.date).label('maxdate')
                         ).group_by(table_object.instrument).subquery('t2')

    result = session.query(table_object).join(
        subq,
        and_(
            table_object.istrument == subq.c.instrument,
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
    title = 'Percentage of observations using filter/pupil combinations'
    pie = figure(height=350, title=title, toolbar_location=None,
                 tools="hover", tooltips="@filter: @value", x_range=(-0.5, 1.0))

    pie.wedge(x=0, y=1, radius=0.4,
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


def treemap(df, col, x, y, dx, dy, *, N=100):
    sub_df = df.nlargest(N, col)
    normed = normalize_sizes(sub_df[col], dx, dy)
    blocks = squarify(normed, x, y, dx, dy)
    blocks_df = pd.DataFrame.from_dict(blocks).set_index(sub_df.index)
    return sub_df.join(blocks_df, how='left').reset_index()


class GeneralDashboard:

    def __init__(self, delta_t=None):
        self.name = 'jwqldb_general_dashboard'
        self.delta_t = delta_t

        now = dt.now()
        self.date = pd.Timestamp('{}-{}-{}'.format(now.year, now.month, now.day))

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

        # Set title and figures list to make panels
        title = 'Files per Filetype by Instrument'
        figures = []

        # For unique instrument values, loop through data
        # Find all entries for instrument/filetype combo
        # Make figure and append it to list.
        for instrument in data.instrument.unique():
            index = data["instrument"] == instrument
            inst_only = data[index].sort_values('filetype')
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
        plot = figure(title="Number of Files Per Instrument", toolbar_location=None,
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

        p1 = figure(title="Number of Files in Filesystem", tools="reset,hover,box_zoom,wheel_zoom", tooltips="@datestr: @total_file_count", plot_width=1700, x_axis_label='Date', y_axis_label='Number of Files Added')
        p1.line(x='date', y='total_file_count', source=source, color='#6C5B7B', line_dash='dashed', line_width=3)
        disable_scientific_notation(p1)
        tab1 = Panel(child=p1, title='Files Per Day')

        # Create separate tooltip for storage plot.
        # Show date and used and available storage together

        p2 = figure(title="Available & Used Storage", tools="reset,hover,box_zoom,wheel_zoom", tooltips="@datestr: @total_file_count", plot_width=1700, x_axis_label='Date', y_axis_label='Storage Space [Terabytes?]')
        p2.line(x='date', y='available', source=source, color='#F8B195', line_dash='dashed', line_width=3, legend='Available Storage')
        p2.line(x='date', y='used', source=source, color='#355C7D', line_dash='dashed', line_width=3, legend='Used Storage')
        disable_scientific_notation(p2)
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

        data['start_time'] = data['start_time'].map(lambda x: x.strftime('%m-%d-%Y %H:%M:%S'))
        data['end_time'] = data['end_time'].map(lambda x: x.strftime('%m-%d-%Y %H:%M:%S'))
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

        data = pd.Series(dict(zip(x_value, top))).reset_index(name='top').rename(columns={'index': 'x'})
        source = ColumnDataSource(data)
        plot = figure(x_range=x_value, title=title, plot_width=850, tools="hover", tooltips="@x: @top", x_axis_label=x_axis_label)
        plot.vbar(x='x', top='top', source=source, width=0.9, color='#6C5B7B')
        plot.xaxis.major_label_orientation = pi / 4
        disable_scientific_notation(plot)
        tab = Panel(child=plot, title=instrument)

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

        ####################################################
        # Commented out for testing. uncomment before merging
        #data = build_table_latest_entry('filesystem_characteristics')

        # Sort by instrument name so that the order of the tabs will always be the same
        #data = data.sort_values('instrument')
        ##################################################


        title = 'File Counts Per Filter'
        figures = []



        outer_radii = vals / np.max(vals) * 100. + 0.1
        inner_radii = [0.1] * len(waves)
        start_angle = np.arange(len(waves))*360./len(waves)
        end_angle = np.arange(1, len(waves)+1)*360./len(waves)

        # This is a loop over instruments
        for i in range(len(data)):
            instrument = data.loc[i]['instrument']
            filterpupil = data.loc[i]['filter_pupil']
            num_obs = data.loc[i]['obs_per_filter_pupil']

            # For testing
            #num_obs = np.linspace(0.01, 30., 100)
            #num_obs = np.linspace(1, 400, 100)
            num_obs = np.array([88, 3, 95, 187, 1, 1, 1, 60, 10, 10, 6, 175, 3, 56, 32, 35, 8, 5, 1, 36, 8, 4, 12, 43, 3, 3, 8, 15, 255, 1, 12, 6, 12, 6, 9, 115, 19, 17, 14, 560, 6, 3, 5, 3, 241, 273, 61, 8, 6, 10, 9, 219, 1, 12, 6, 5, 2, 45, 8, 6, 5, 9, 57, 50, 1, 29, 66, 6, 109, 6, 8, 6, 35, 75, 216, 16, 36, 4, 39, 37, 8, 6, 5, 6, 73, 10, 7, 8, 9, 38, 10, 9, 8, 13, 202, 315, 27, 44, 14, 38, 5, 39, 29, 10, 9, 8, 6, 327, 10, 10, 9, 6, 253,109,5,57,57])
            filterpupil = np.array(['F070W/CLEAR', 'F070W/WLP8', 'F090W/CLEAR', 'F115W/CLEAR',
       'F115W/FLAT', 'F115W/MASKBAR', 'F115W/MASKRND', 'F140M/CLEAR',
       'F140M/GDHS0', 'F140M/GDHS60', 'F140M/WLP8', 'F150W/CLEAR',
       'F150W/WLP8', 'F150W2/CLEAR', 'F150W2/F162M', 'F150W2/F164N',
       'F150W2/GDHS0', 'F150W2/GDHS60', 'F150W2/MASKIPR', 'F182M/CLEAR',
       'F182M/MASKBAR', 'F182M/MASKRND', 'F182M/WLP8', 'F187N/CLEAR',
       'F187N/MASKBAR', 'F187N/MASKRND', 'F187N/WLM8', 'F187N/WLP8',
       'F200W/CLEAR', 'F200W/GDHS60', 'F200W/MASKBAR', 'F200W/MASKIPR',
       'F200W/MASKRND', 'F200W/WLM8', 'F200W/WLP8', 'F210M/CLEAR',
       'F210M/MASKBAR', 'F210M/MASKRND', 'F210M/WLP8', 'F212N/CLEAR',
       'F212N/FLAT', 'F212N/MASKBAR', 'F212N/MASKIPR', 'F212N/MASKRND',
       'F212N/WLM8', 'F212N/WLP8', 'F250M/CLEAR', 'F250M/GRISMC',
       'F250M/GRISMR', 'F250M/MASKBAR', 'F250M/MASKRND', 'F277W/CLEAR',
       'F277W/FLAT', 'F277W/GRISMC', 'F277W/GRISMR', 'F277W/MASKBAR',
       'F277W/MASKRND', 'F300M/CLEAR', 'F300M/GRISMC', 'F300M/GRISMR',
       'F300M/MASKBAR', 'F300M/MASKRND', 'F322W2/CLEAR', 'F322W2/F323N',
       'F322W2/F405N', 'F322W2/GRISMC', 'F322W2/GRISMR', 'F322W2/MASKRND',
       'F335M/CLEAR', 'F335M/FLAT', 'F335M/GRISMC', 'F335M/GRISMR',
       'F335M/MASKBAR', 'F335M/MASKRND', 'F356W/CLEAR', 'F356W/GRISMC',
       'F356W/GRISMR', 'F356W/MASKBAR', 'F356W/MASKRND', 'F360M/CLEAR',
       'F360M/GRISMC', 'F360M/GRISMR', 'F360M/MASKBAR', 'F360M/MASKRND',
       'F410M/CLEAR', 'F410M/GRISMC', 'F410M/GRISMR', 'F410M/MASKBAR',
       'F410M/MASKRND', 'F430M/CLEAR', 'F430M/GRISMC', 'F430M/GRISMR',
       'F430M/MASKBAR', 'F430M/MASKRND', 'F444W/CLEAR', 'F444W/F405N',
       'F444W/F466N', 'F444W/F470N', 'F444W/GRISMC', 'F444W/GRISMR',
       'F444W/MASKBAR', 'F444W/MASKRND', 'F460M/CLEAR', 'F460M/GRISMC',
       'F460M/GRISMR', 'F460M/MASKBAR', 'F460M/MASKRND', 'F480M/CLEAR',
       'F480M/GRISMC', 'F480M/GRISMR', 'F480M/MASKBAR', 'F480M/MASKRND',
       'N/A/FLAT', 'WLP4/CLEAR', 'WLP4/MASKIPR', 'WLP4/WLM8', 'WLP4/WLP8'])

            #filterpupil = [f'filter{i}' for i in range(100)]

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

            data = pd.Series(data_dict).reset_index(name='value').rename(columns={'index': 'filter'})
            #data['angle'] = data['value']/data['value'].sum() * 2*np.pi

            if instrument != 'nircam':
                # Calculate the angle covered by each filter
                data['angle'] = data['value']/data['value'].sum() * 2 * np.pi

                # Keep all wedges the same color, except for those that are a very
                # small fraction, and will be covered in the second pie chart. Make
                # those wedges grey in the primary pie chart.
                data['colors'] = ['#c85108'] * len(data)
                data.loc[data['value'] < 0.5, 'colors'] = '#bec4d4'

                # Make a dataframe containing only the filters that are used in less
                # than some threshold percentage of observations
                small = data.loc[data['value'] <0.5].copy()

                # Recompute the angles for these, and make them all the same color.
                small['angle'] = small['value'] / small['value'].sum() * 2 * np.pi
                small['colors'] = ['#c85108'] * len(small)

                # Create two pie charts
                pie_fig = create_filter_based_pie_chart("All Filters", data)
                small_pie_fig = create_filter_based_pie_chart("Low Contributors", sw_small)

                # Place the pie charts in a row/Panel, and append to the figure
                rowplots = row(pie_fig, small_pie_fig)
                tab = Panel(child=rowplots, title=f'{instrument}')
                figures.append(tab)

            else:
                # For NIRCam, we split the SW and LW channels and put each in its own tab.
                #  This will cut down on the number of entries in each and make the pie
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
                data['channel'] = channel

                # Set the colors. All wedges with a pie chart have the same color.
                color_options = {'LW': '#c85108', 'SW': '#3d85c6', 'Dark': '#bec4d4'}
                colors = []
                for entry in channel:
                    colors.append(color_options[entry])
                data['colors'] = colors

                # Even though it's not quite correct, create separate charts for SW vs LW. This will
                # hopefully make them much easier to read
                sw_data = data.loc[data['channel'] == 'SW'].copy()
                lw_data = data.loc[data['channel'] == 'LW'].copy()

                # Recalculate the angles. These won't be strictly correct since SW and LW filters
                # are not both used exactly 50% of the time, but it's close enough for now.
                sw_data['angle'] = sw_data['value'] / sw_data['value'].sum() * 2 * np.pi
                lw_data['angle'] = lw_data['value'] / lw_data['value'].sum() * 2 * np.pi

                # Zoomed in version of the small contributors
                sw_small = sw_data.loc[sw_data['value'] <0.5].copy()
                lw_small = lw_data.loc[lw_data['value'] <0.5].copy()
                sw_small['angle'] = sw_small['value'] / sw_small['value'].sum() * 2 * np.pi
                lw_small['angle'] = lw_small['value'] / lw_small['value'].sum() * 2 * np.pi

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
                sw_pie_fig = create_filter_based_pie_chart("SW All Filters", sw_data)
                sw_small_pie_fig = create_filter_based_pie_chart("SW Low Contributors", sw_small)
                lw_pie_fig = create_filter_based_pie_chart("LW All Filters", lw_data)
                lw_small_pie_fig = create_filter_based_pie_chart("LW Low Contributors", lw_small)

                # Create rows and Panels
                sw_rowplots = row(sw_pie_fig, sw_small_pie_fig)
                lw_rowplots = row(lw_pie_fig, lw_small_pie_fig)

                tab_sw = Panel(child=sw_rowplots, title=f'{instrument} SW')
                tab_lw = Panel(child=lw_rowplots, title=f'{instrument} LW')
                figures.append(tab_sw)
                figures.append(tab_lw)

                #figures.append(self.make_panel(data.loc[i]['filter_pupil'], data_loc[i]['obs_per_filter_pupil'], data_loc[i]['instrument'], title, 'Filter/Pupil'))

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

        # For unique instrument values, loop through data
        # Find all entries for instrument/filetype combo
        # Make figure and append it to list.
        for instrument in ANOMALY_CHOICES_PER_INSTRUMENT.keys():
            data = build_table('{}_anomaly'.format(instrument))
            data = data.drop(columns=['id', 'rootname', 'user'])
            if not pd.isnull(self.delta_t) and not data.empty:
                data = data[(data['flag_date'] >= (self.date - self.delta_t)) & (data['flag_date'] <= self.date)]
            summed_anomaly_columns = data.sum(axis=0, numeric_only=True).to_frame(name='counts')
            figures.append(self.make_panel(summed_anomaly_columns.index.values, summed_anomaly_columns['counts'], instrument, title, 'Anomaly Type'))

        tabs = Tabs(tabs=figures)

        return tabs
