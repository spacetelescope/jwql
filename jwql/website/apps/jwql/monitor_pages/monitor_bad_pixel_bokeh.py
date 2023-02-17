"""This module contains code for the bad pixel monitor Bokeh plots.

Author
------

    - Bryan Hilbert

Use
---

    This module can be used from the command line as such:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_template = monitor_pages.BadPixelMonitor('NIRCam', 'NRCA3_FULL')
        script, div = monitor_template.embed("bad_pixel_time_figure")
"""

import os

from astropy.io import fits
from bokeh.embed import components, file_html
from bokeh.layouts import layout
from bokeh.models import ColumnDataSource, Panel, Tabs, Text
from bokeh.plotting import figure
from bokeh.resources import CDN
import datetime
import numpy as np

from jwql.database.database_interface import session
from jwql.database.database_interface import NIRCamBadPixelQueryHistory, NIRCamBadPixelStats
from jwql.database.database_interface import NIRISSBadPixelQueryHistory, NIRISSBadPixelStats
from jwql.database.database_interface import MIRIBadPixelQueryHistory, MIRIBadPixelStats
from jwql.database.database_interface import NIRSpecBadPixelQueryHistory, NIRSpecBadPixelStats
from jwql.database.database_interface import FGSBadPixelQueryHistory, FGSBadPixelStats
from jwql.utils.constants import BAD_PIXEL_TYPES, DARKS_BAD_PIXEL_TYPES, FLATS_BAD_PIXEL_TYPES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import filesystem_path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


"""
class BadPixMonitorData():
    def __init__(self):
        pass


class BadPixFigure():
    def __init__(self):
        pass

class BadPixPlots():
    #top-level class

    # Get the data from the database
    m = BadPixMonitorData()


    # Create the figures
    for badpix_type in badpix_types:
        p = BadPixFigure()
"""

class BadPixelPlots():
    """Class for creating the bad pixel plots and figures to be displayed in the web app
    """
    def __init__(self, instrument):
        self.instrument = instrument.lower()
        #self.apertures = self.get_inst_apers()
        self.apertures = ['aper1', 'aper2', 'aper3']
        self.run()

    def modify_bokeh_saved_html(self):
        """Given an html string produced by Bokeh when saving bad pixel monitor plots,
        make tweaks such that the page follows the general JWQL page formatting.
        """
        lines = self.html.split('\n')

        # List of lines that Bokeh likes to save in the file, but we don't want
        lines_to_remove = ["<!DOCTYPE html>",
                           '<html lang="en">',
                           '  </body>',
                           '</html>']

        # Our Django-related lines that need to be at the top of the file
        newlines = ['{% extends "base.html" %}\n', "\n",
                    "{% block preamble %}\n", "\n",
                    f"<title>{JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bad Pixel Monitor- JWQL</title>\n", "\n",
                    "{% endblock %}\n", "\n",
                    "{% block content %}\n", "\n",
                    '  <main role="main" class="container">\n', "\n",
                    f"  <h1>{JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bad Pixel Monitor</h1>\n",
                    "  <hr>\n",
                    ]

        # More lines that we want to have in the html file, at the bottom
        endlines = ["\n",
                    f"    <h1>{JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bad Pixel Stats Table</h1>\n",
                    "    <hr>\n", "\n",
                    """    <a href="{{'/jwqldb/nircam_bad_pixel_stats'}}" name=test_link class="btn btn-primary my-2" type="submit">Bad Pixel Stats</a>\n""", "\n",
                    "</main>\n", "\n",
                    "{% endblock %}"
                    ]

        for line in lines:
            if line not in lines_to_remove:
                newlines.append(line + '\n')
        newlines = newlines + endlines

        self.html = "".join(newlines)


    def run(self):
        aperture_panels = []
        for aperture in self.apertures:
            all_plots = {}
            all_plots['new_dark'] = NewBadPixPlot('darks').plot
            all_plots['new_flat'] = NewBadPixPlot('flats').plot
            all_plots['bad_types'] = {}
            for badtype in ['badtype1', 'badtype2', 'badtype3']:
                all_plots['bad_types'][badtype] = BadPixTypePlot(badtype).plot
            plot_layout = badpix_monitor_plot_layout(all_plots)

            # Create a tab for each type of plot
            aperture_panels.append(Panel(child=plot_layout, title=aperture))

        # Build tabs
        tabs = Tabs(tabs=aperture_panels)

        # Return tab HTML and JavaScript to web app
        script, div = components(tabs)

        # Insert into our html template and save
        template_file = '/Users/hilbert/python_repos/jwql/jwql/website/apps/jwql/templates/bad_pixel_monitor_savefile_basic.html'
        temp_vars = {'inst': self.instrument, 'plot_script': script, 'plot_div':div}
        self.html = file_html(tabs, CDN, f'{self.instrument} bad pix monitor', template_file, temp_vars)

        # Modify the html such that our Django-related lines are kept in place,
        # which will allow the page to keep the same formatting and styling as
        # the other web app pages
        self.modify_bokeh_saved_html()

        # Save html file
        outdir = os.path.dirname(template_file)
        #outfile = 'test_badpix_saved_file.html'
        outfile = f'{self.instrument}_bad_pix_plots.html'
        outfile = os.path.join(outdir, outfile)
        with open(outfile, "w") as file:
            file.write(self.html)


class BadPixelData():
    """Retrieve bad pixel monitor data from the database
    """
    def __init__(self):
        pass


class NewBadPixPlot():
    """Create a plot showing the location of newly discovered bad pixels
    """
    def __init__(self, data_type):
        self.plot = figure(title=data_type, tools='')
        self.plot.x_range.start = 0
        self.plot.x_range.end = 1
        self.plot.y_range.start = 0
        self.plot.y_range.end = 1

        source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
        glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
        self.plot.add_glyph(source, glyph)



class BadPixTypePlot():
    """Create a plot showing the location of a certain type of bad pixel
    """
    def __init__(self, badpix_type):
        self.plot = figure(title=badpix_type, tools='')
        self.plot.x_range.start = 0
        self.plot.x_range.end = 1
        self.plot.y_range.start = 0
        self.plot.y_range.end = 1

        source = ColumnDataSource(data=dict(x=[0.5], y=[0.5], text=['No data']))
        glyph = Text(x="x", y="y", text="text", angle=0., text_color="red", text_font_size={'value':'20px'})
        self.plot.add_glyph(source, glyph)







def badpix_monitor_plot_layout(plots):
    """Arrange a set of plots into a bokeh layout. Generate nested lists for
    the plot layout for a given aperture. Contents of tabs should be similar
    for all apertures of a given instrument. Keys of the input plots will
    control the exact layout.

    Paramters
    ---------
    plots : dict
        Dictionary containing a set of plots for an aperture.
        Possible keys are 'new_flat' and 'new_dark', which contain the figures
        showing new bad pixels derived from flats and darks, respectively.
        The third key is 'bad_types', which should contain a dictionary. The
        keys of this dictionary are bad pixel types (e.g. 'dead'). Each of
        these contains the Bokeh figure showing the locations of new bad
        pixels of that type.

    Returns
    -------
    plot_layout : bokeh.layouts.layout
    """
    # First the plots showing all bad pixel types derived from a given type of
    # input (darks or flats). If both plots are present, show them side by side.
    # Some instruments will only have one of these two (e.g. NIRCam has no
    # internal lamps, and so will not have flats). In that case, show the single
    # exsiting plot by itself in the top row.
    if 'new_dark' in plots and 'new_flat' in plots:
        new_list = [[plots['new_dark'], plots['new_flat']]]
    elif 'new_dark' in plots:
        new_list = [plots['new_dark']]
    elif 'new_flat' in plots:
        new_list = [plots['new_flat']]

    # Next create a list of plots where each plot shows one flavor of bad pixel
    plots_per_row = 2
    num_bad_types = len(plots['bad_types'])
    first_col = np.arange(0, num_bad_types, plots_per_row)

    badtype_lists = []
    keys = list(plots['bad_types'])
    for i, key in enumerate(keys):
        if i % plots_per_row == 0:
            sublist = keys[i: i + plots_per_row]
            rowplots = []
            for subkey in sublist:
                rowplots.append(plots['bad_types'][subkey])
            badtype_lists.append(rowplots)

    # Combine full frame and subarray aperture lists
    full_list = new_list + badtype_lists

    # Now create a layout that holds the lists
    plot_layout = layout(full_list)

    return plot_layout














"""OLD CODE BELOW HERE"""
"""CAN BE DELETED"""


class BadPixelMonitor():

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

    def bad_pixel_history(self, bad_pixel_type):
        """Use the database to construct information on the total number
        of a given type of bad pixels over time

        Parameters
        ----------
        bad_pixel_type : str
            The flavor of bad pixel (e.g. 'hot')

        Returns
        -------
        num_bad_pixels : numpy.ndarray
            1D array of the number of bad pixels

        dates : datetime.datetime
            1D array of dates/times corresponding to num_bad_pixels
        """
        # Find all the rows corresponding to the requested type of bad pixel
        rows = [row for row in self.bad_pixel_table if row.type == bad_pixel_type]

        # Extract the dates and number of bad pixels from each entry
        dates = [row.obs_mid_time for row in rows]
        num = [len(row.coordinates[0]) for row in rows]

        # If there are no valid entres in the database, return None
        if len(dates) == 0:
            return None, None

        # Sort by date to make sure everything is in chronological order
        chrono = np.argsort(dates)
        dates = dates[chrono]
        num = num[chrono]

        # Sum the number of bad pixels found from the earliest entry up to
        # each new entry
        num_bad_pixels = [np.sum(num[0:i]) for i in range(1, len(num) + 1)]

        return num_bad_pixels, dates

    def _badpix_image(self):
        """Update bokeh objects with sample image data."""

        # Open the mean dark current file and get the data
        with fits.open(self.image_file) as hdulist:
            data = hdulist[1].data

        # Grab only one frame
        ndims = len(data.shape)
        if ndims == 4:
            data = data[0, -1, :, :]
        elif ndims == 3:
            data = data[-1, :, :]
        elif ndims == 2:
            pass
        else:
            raise ValueError('Unrecognized number of dimensions in data file: {}'.format(ndims))

        # Update the plot with the data and boundaries
        y_size, x_size = data.shape
        self.refs["bkgd_image"].data['image'] = [data]
        self.refs["stamp_xr"].end = x_size
        self.refs["stamp_yr"].end = y_size
        self.refs["bkgd_source"].data['dw'] = [x_size]
        self.refs["bkgd_source"].data['dh'] = [y_size]

        # Set the image color scale
        self.refs["log_mapper"].high = 0
        self.refs["log_mapper"].low = -.2

        # Add a title
        self.refs['badpix_map_figure'].title.text = '{}: New Bad Pixels'.format(self._aperture)
        self.refs['badpix_map_figure'].title.align = "center"
        self.refs['badpix_map_figure'].title.text_font_size = "20px"

    def most_recent_coords(self, bad_pixel_type):
        """Return the coordinates of the bad pixels in the most recent
        database entry for the given bad pixel type

        Parameters
        ----------
        bad_pixel_type : str
            The flavor of bad pixel (e.g. 'hot')

        Returns
        -------
        coords : tup
            Tuple containing a list of x coordinates and a list of y
            coordinates
        """
        # Find all the rows corresponding to the requested type of bad pixel
        rows = [row for row in self.bad_pixel_table if row.type == bad_pixel_type]

        # Extract dates, number of bad pixels, and files used from each entry
        dates = [row.obs_mid_time for row in rows]
        coords = [row.coordinates for row in rows]
        files = [row.source_files[0] for row in rows]

        # If there are no valid entres in the database, return None
        if len(dates) == 0:
            return None, None

        # Sort by date to make sure everything is in chronological order
        chrono = np.argsort(dates)
        dates = dates[chrono]
        coords = coords[chrono]
        files = files[chrono]

        # Keep track of the latest timestamp
        self.last_timestamp = dates[-1].isoformat()

        # Grab the name of one of the files used when these bad pixels
        # were identified. We'll use this as an image on top of which
        # the bad pixels will be noted. Note that these should be
        # slope files
        self.image_file = filesystem_path(files[-1])

        # Return the list of coordinates for the most recent entry
        return coords[-1]

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
        self.interface_file = os.path.join(SCRIPT_DIR, "yaml", "badpixel_monitor_interface.yaml")

        # Load data tables
        self.load_data()
        self.get_history_data()
        # For development, while the database tables are empty
        # self.load_dummy_data()

        # Get dates and coordinates of the most recent entries
        self.most_recent_data()

        # This shows that for e.g. NRCA2_FULL, the data are what we expect,
        # but somehow the plot is not showing it!!!!!!!!
        # if self._aperture != 'NRCA1_FULL':
        #    raise ValueError(self._aperture, self.latest_bad_from_dark_type, self.latest_bad_from_dark_x, self.latest_bad_from_dark_y)

    def post_init(self):
        self._update_badpix_v_time()
        self._update_badpix_loc_plot()

    def get_history_data(self):
        """Extract data on the history of bad pixel numbers from the
        database query result
        """
        self.bad_history = {}
        self.bad_latest = {}
        for bad_pixel_type in BAD_PIXEL_TYPES:
            matching_rows = [row for row in self.bad_pixel_table if row.type == bad_pixel_type]
            if len(matching_rows) != 0:
                real_data = True
                times = [row.obs_mid_time for row in matching_rows]
                num = np.array([len(row.x_coord) for row in matching_rows])

                latest_row = times.index(max(times))
                self.bad_latest[bad_pixel_type] = (max(times), matching_rows[latest_row].x_coord, matching_rows[latest_row].y_coord)

            # If there are no records of a certain type of bad pixel, then
            # fall back to a default date and 0 bad pixels. Remember that
            # these plots are always showing the number of NEW bad pixels
            # that are not included in the current reference file.
            else:
                real_data = False

                times = [datetime.datetime(2021, 10, 31), datetime.datetime(2021, 11, 1)]
                badpix_x = [1000, 999]
                badpix_y = [1000, 999]
                num = np.array([0, 0])
                self.bad_latest[bad_pixel_type] = (max(times), badpix_x, badpix_y)

            hover_values = np.array([datetime.datetime.strftime(t, "%d-%b-%Y") for t in times])
            self.bad_history[bad_pixel_type] = (times, num, hover_values)

            # if real_data:
            #    raise ValueError(bad_pixel_type, self.bad_history[bad_pixel_type])

    def identify_tables(self):
        """Determine which database tables as associated with
        a given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self._instrument.lower()]
        self.query_table = eval('{}BadPixelQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}BadPixelStats'.format(mixed_case_name))

    def load_data(self):
        """Query the database tables to get data"""

        # Determine which database tables are needed based on instrument
        self.identify_tables()

        # Query database for all data with a matching aperture
        self.bad_pixel_table = session.query(self.pixel_table) \
            .filter(self.pixel_table.detector == self.detector) \
            .all()

        session.close()

    def load_dummy_data(self):
        """Create dummy data for Bokeh plot development"""
        import datetime

        # Populate a dictionary with the number of bad pixels vs time for
        # each type of bad pixel. We can't get the full list of bad pixel
        # types from the database itself, because if there is a type of bad
        # pixel with no found instances, then it won't appear in the database
        # Also populate a dictionary containing the locations of all of the
        # bad pixels found in the most recent search
        self.bad_history = {}
        self.bad_latest = {}
        for i, bad_pixel_type in enumerate(BAD_PIXEL_TYPES):

            # Comment out while waiting for populated database tables
            # num, times = self.bad_pixel_history(bad_pixel_type)
            delta = 10 * i

            # Placeholders while we wait for a populated database
            days = np.arange(1, 11)
            times = np.array([datetime.datetime(2020, 8, day, 12, 0, 0) for day in days])
            num = np.arange(10)
            hover_values = np.array([datetime.datetime.strftime(t, "%d-%b-%Y") for t in times])

            self.bad_history[bad_pixel_type] = (times, num, hover_values)
            self.bad_latest[bad_pixel_type] = (datetime.datetime(1999, 12, 31), [500 + delta, 501 + delta, 502 + delta], [4, 4, 4])

    def most_recent_data(self):
        """Get the bad pixel type and coordinates associated with the most
        recent run of the monitor. Note that the most recent date can be
        different for dark current data vs flat field data
        """
        self.latest_bad_from_dark_type = []
        self.latest_bad_from_dark_x = []
        self.latest_bad_from_dark_y = []
        dark_times = [self.bad_latest[bad_pixel_type][0] for bad_pixel_type in DARKS_BAD_PIXEL_TYPES]
        if len(dark_times) > 0:
            self.most_recent_dark_date = max(dark_times)
        else:
            self.most_recent_dark_date = datetime.datetime(1999, 10, 31)

        for bad_pixel_type in DARKS_BAD_PIXEL_TYPES:
            if self.bad_latest[bad_pixel_type][0] == self.most_recent_dark_date:
                self.latest_bad_from_dark_type.extend([bad_pixel_type] * len(self.bad_latest[bad_pixel_type][1]))
                self.latest_bad_from_dark_x.extend(self.bad_latest[bad_pixel_type][1])
                self.latest_bad_from_dark_y.extend(self.bad_latest[bad_pixel_type][2])

        self.latest_bad_from_dark_type = np.array(self.latest_bad_from_dark_type)
        self.latest_bad_from_dark_x = np.array(self.latest_bad_from_dark_x)
        self.latest_bad_from_dark_y = np.array(self.latest_bad_from_dark_y)

        self.latest_bad_from_flat_type = []
        self.latest_bad_from_flat_x = []
        self.latest_bad_from_flat_y = []

        self.latest_bad_from_flat = [[], [], []]
        flat_times = [self.bad_latest[bad_pixel_type][0] for bad_pixel_type in FLATS_BAD_PIXEL_TYPES]
        if len(flat_times) > 1:
            self.most_recent_flat_date = max(flat_times)
        else:
            self.most_recent_flat_date = datetime.datetime(1999, 10, 31)
        for bad_pixel_type in FLATS_BAD_PIXEL_TYPES:
            if self.bad_latest[bad_pixel_type][0] == self.most_recent_flat_date:
                self.latest_bad_from_flat_type.extend([bad_pixel_type] * len(self.bad_latest[bad_pixel_type][1]))
                self.latest_bad_from_flat_x.extend(self.bad_latest[bad_pixel_type][1])
                self.latest_bad_from_flat_y.extend(self.bad_latest[bad_pixel_type][2])

        self.latest_bad_from_flat_type = np.array(self.latest_bad_from_flat_type)
        self.latest_bad_from_flat_x = np.array(self.latest_bad_from_flat_x)
        self.latest_bad_from_flat_y = np.array(self.latest_bad_from_flat_y)

    def _update_badpix_loc_plot(self):
        """Update the plot properties for the plots showing the locations
        of new bad pixels"""
        if 'MIR' in self._aperture:
            self.refs['dark_position_xrange'].end = 1024
            self.refs['dark_position_yrange'].end = 1024
            self.refs['flat_position_xrange'].end = 1024
            self.refs['flat_position_yrange'].end = 1024

        dark_date = self.most_recent_dark_date.strftime('%d-%b-%Y %H:%m')
        self.refs['dark_position_figure'].title.text = '{} New Bad Pixels (darks). Obs Time: {}'.format(self._aperture, dark_date)
        self.refs['dark_position_figure'].title.align = "center"
        self.refs['dark_position_figure'].title.text_font_size = "15px"

        flat_date = self.most_recent_flat_date.strftime('%d-%b-%Y %H:%m')
        self.refs['flat_position_figure'].title.text = '{} New Bad Pixels (flats). Obs Time: {}'.format(self._aperture, flat_date)
        self.refs['flat_position_figure'].title.align = "center"
        self.refs['flat_position_figure'].title.text_font_size = "15px"

    def _update_badpix_v_time(self):
        """Update the plot properties for the plots of the number of bad
        pixels versus time
        """
        for bad_pixel_type in BAD_PIXEL_TYPES:
            bad_pixel_type_lc = bad_pixel_type.lower()

            # Define y ranges of bad pixel v. time plot
            buffer_size = 0.05 * (max(self.bad_history[bad_pixel_type][1]) - min(self.bad_history[bad_pixel_type][1]))
            if buffer_size == 0:
                buffer_size = 1
            self.refs['{}_history_yrange'.format(bad_pixel_type_lc)].start = min(self.bad_history[bad_pixel_type][1]) - buffer_size
            self.refs['{}_history_yrange'.format(bad_pixel_type_lc)].end = max(self.bad_history[bad_pixel_type][1]) + buffer_size

            # Define x range of bad_pixel v. time plot
            horizontal_half_buffer = (max(self.bad_history[bad_pixel_type][0]) - min(self.bad_history[bad_pixel_type][0])) * 0.05
            if horizontal_half_buffer == 0:
                horizontal_half_buffer = 1.  # day
            self.refs['{}_history_xrange'.format(bad_pixel_type_lc)].start = min(self.bad_history[bad_pixel_type][0]) - horizontal_half_buffer
            self.refs['{}_history_xrange'.format(bad_pixel_type_lc)].end = max(self.bad_history[bad_pixel_type][0]) + horizontal_half_buffer

            # Add a title
            self.refs['{}_history_figure'.format(bad_pixel_type.lower())].title.text = '{}: {} pixels'.format(self._aperture, bad_pixel_type)
            self.refs['{}_history_figure'.format(bad_pixel_type.lower())].title.align = "center"
            self.refs['{}_history_figure'.format(bad_pixel_type.lower())].title.text_font_size = "20px"





# Uncomment the line below when testing via the command line:
# bokeh serve --show monitor_badpixel_bokeh.py
# BadPixelMonitor()
