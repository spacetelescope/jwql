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
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from bokeh.embed import components, file_html
from bokeh.layouts import layout
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool, Legend, LinearColorMapper, Panel, Tabs, Text
from bokeh.plotting import figure
from bokeh.resources import CDN
import datetime
import numpy as np
from sqlalchemy import and_, func

from jwql.database.database_interface import get_unique_values_per_column, session
from jwql.database.database_interface import NIRCamBadPixelQueryHistory, NIRCamBadPixelStats
from jwql.database.database_interface import NIRISSBadPixelQueryHistory, NIRISSBadPixelStats
from jwql.database.database_interface import MIRIBadPixelQueryHistory, MIRIBadPixelStats
from jwql.database.database_interface import NIRSpecBadPixelQueryHistory, NIRSpecBadPixelStats
from jwql.database.database_interface import FGSBadPixelQueryHistory, FGSBadPixelStats
from jwql.utils.constants import BAD_PIXEL_TYPES, DARKS_BAD_PIXEL_TYPES, FLATS_BAD_PIXEL_TYPES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import filesystem_path, get_config, read_png

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = get_config()['outputs']


class BadPixelPlots():
    """Class for creating the bad pixel plots and figures to be displayed in the web app
    """
    def __init__(self, instrument):
        self.instrument = instrument.lower()

        # Get the relevant database tables
        self.identify_tables()

        #self.apertures = self.get_inst_apers()
        #self.apertures = ['aper1', 'aper2', 'aper3']
        self.detectors = get_unique_values_per_column(self.pixel_table, 'detector')
        self.run()

    def identify_tables(self):
        """Determine which database tables as associated with
        a given instrument"""
        mixed_case_name = JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument.lower()]
        self.query_table = eval('{}BadPixelQueryHistory'.format(mixed_case_name))
        self.pixel_table = eval('{}BadPixelStats'.format(mixed_case_name))

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

        # Right now, the aperture name in the query history table is used as the title of the
        # bad pixel plots. The name associated with entries in the bad pixel stats table is the
        # detector name. Maybe we should switch to use this.
        detector_panels = []
        for detector in self.detectors:

            # Get data from the database
            data = BadPixelData(self.pixel_table, self.instrument, detector)

            # Create plots of the location of new bad pixels
            all_plots = {}
            #all_plots['new_dark'] = NewBadPixPlot(detector, data.num_files, data.new_bad_pix, data.background_file, 'darks',
            #                                      data.baseline_file, data.obs_start_time, data.obs_end_time).plot
            #all_plots['new_flat'] = NewBadPixPlot(detector, data.num_files, data.new_bad_pix, data.background_file, 'flats',
            #                                      data.baseline_file, data.obs_start_time, data.obs_end_time).plot
            all_plots['new_pix'] = {}
            all_plots['trending'] = {}
            for badtype in data.badtypes:
                all_plots['new_pix'][badtype] = NewBadPixPlot(detector, badtype, data.num_files[badtype], data.new_bad_pix[badtype],
                                                              data.background_file[badtype], data.baseline_file[badtype],
                                                              data.obs_start_time[badtype], data.obs_end_time[badtype]).plot
                all_plots['trending'][badtype] = BadPixTrendPlot(detector, badtype, data.trending_data[badtype]).plot
            plot_layout = badpix_monitor_plot_layout(all_plots)

            # Create a tab for each type of plot
            detector_panels.append(Panel(child=plot_layout, title=detector))

        # Build tabs
        tabs = Tabs(tabs=detector_panels)

        # Return tab HTML and JavaScript to web app
        script, div = components(tabs)

        # Insert into our html template and save
        template_file = '/Users/hilbert/python_repos/jwql/jwql/website/apps/jwql/templates/bad_pixel_monitor_savefile_basic.html'
        temp_vars = {'inst': self.instrument, 'plot_script': script, 'plot_div':div}
        self.html = file_html(tabs, CDN, f'{self.instrument} bad pix monitor', template_file, temp_vars)

        with open(template_file, 'w') as f:
            f.writelines(self.html)


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
    def __init__(self, pixel_table, instrument, detector):
        self.pixel_table = pixel_table
        self.instrument = instrument
        self.detector = detector
        self.trending_data = {}
        self.new_bad_pix = {}
        self.background_file = {}
        self.obs_start_time = {}
        self.obs_end_time = {}
        self.num_files = {}
        self.baseline_file = {}

        #self.identify_tables()

        # Get data for the plot of new bad pixels
        self.get_most_recent_entry()

        # Get data for the trending plots
        self.badtypes = get_unique_values_per_column(self.pixel_table, 'type')
        for badtype in self.badtypes:
            self.get_trending_data(badtype)


    def get_most_recent_entry(self):
        """Get all nedded data from the database tables.
        Parameters
        ----------
        detector : str
            Name of detector for which data are retrieved (e.g. NRCA1)
        """
        # For the given detector, get the latest entry for each bad pixel type
        subq = (session
                .query(self.pixel_table.type, func.max(self.pixel_table.entry_date).label("max_created"))
                .filter(self.pixel_table.detector == self.detector)
                .group_by(self.pixel_table.type)
                .subquery()
                )

        query = (session.query(self.pixel_table)
                 .join(subq, self.pixel_table.entry_date == subq.c.max_created)
                 )

        latest_entries_by_type = query.all()
        session.close()

        for row in latest_entries_by_type:
            self.new_bad_pix[row.type] = (row.x_coord, row.y_coord)
            self.background_file[row.type] = row.source_files[0]
            self.obs_start_time[row.type] = row.obs_start_time
            #self.obs_mid_time[row.type] = row.obs_mid_time
            self.obs_end_time[row.type] = row.obs_end_time
            self.num_files[row.type] = len(row.source_files)
            self.baseline_file[row.type] = row.baseline_file

    def get_trending_data(self, badpix_type):
        """
        """
         # The MIRI imaging detector does not line up with the full frame aperture. Fix that here
        if self.detector == 'MIRIM':
            self.detector = 'MIRIMAGE'

        # NIRCam LW detectors use 'LONG' rather than 5 in the pixel_table
        if '5' in self.detector:
            self.detector = self.detector.replace('5', 'LONG')

        # Query database for all data in the table with a matching detector and bad pixel type
        all_entries_by_type = session.query(self.pixel_table.type, self.pixel_table.detector, func.array_length(self.pixel_table.x_coord, 1),
                                            self.pixel_table.obs_mid_time) \
                              .filter(and_(self.pixel_table.detector == self.detector,  self.pixel_table.type == badpix_type)) \
                              .all()

        # Organize the results
        num_pix = []
        times = []
        for i, row in enumerate(all_entries_by_type):
            if i == 0:
                badtype = row[0]
                detector = row[1]
            num_pix.append(row[2])
            times.append(row[3])
        self.trending_data[badpix_type] = (detector, num_pix, times)

        # For the given detector, get the latest entry for each bad pixel type, and
        # return the bad pixel type, detector, and mean dark image file
        #subq = (session
        #        .query(self.pixel_table.type, func.max(self.pixel_table.entry_date).label("max_created"))
        #        .filter(self.pixel_table.detector == self.detector & self.pixle_table.type == self.type)
        #        .group_by(self.pixel_table.type)
        #        .subquery()
        #        )

        #query = (session.query(self.pixel_table.type, self.pixel_table.detector, self.pixel_table.x_coord.length, self.pixel_table.obs_mid_time)
        #         .join(subq, self.pixel_table.entry_date == subq.c.max_created)
        #         )

        #self.most_recent_data = query.all()
        session.close()


class NewBadPixPlot():
    """Create a plot showing the location of newly discovered bad pixels

    Parameters
    ----------
    """
    def __init__(self, detector_name, badpix_type, nfiles, coords, background_file, baseline_file, obs_start_time, obs_end_time):
        self.detector = detector_name
        self.badpix_type = badpix_type
        self.num_files = nfiles
        self.coords = coords
        self.background_file = background_file
        self.baseline_file = baseline_file
        self.obs_start_time = obs_start_time
        self.obs_end_time = obs_end_time
        #if self.data_type == 'darks':
        #    self.badpix_types = DARKS_BAD_PIXEL_TYPES
        #elif self.data_type == 'flats':
        #    self.badpix_types = FLATS_BAD_PIXEL_TYPES
        #else:
        #    raise ValueError("Unrecognized data type. Should be 'flats' or 'darks'")

        # If no background file is given, we fall back to plotting the bad pixels
        # on top of an empty image. In that case, we need to know how large the
        # detector is, just to create an image of the right size.
        if 'MIRI' in self.detector.upper():
            self._detlen = 1024
        else:
            self._detlen = 2048

        self.create_plot()

    def create_plot(self):
        """Create the plot by showing background image, and marking the locations
        of new bad pixels on top
        """

        # Use the first background image you come across for the given bad pixel types
        #background_file = None
        #start_time = None
        #end_time = None
        #baseline_file = None
        #for bad_type in self.badpix_types:
        #    if bad_type in self.background_files:
        #        background_file = self.background_files[bad_type]
        #        start_time = self.obs_start_time[bad_type]
        #        end_time = self.obs_end_time[bad_type]
        #        baseline_file = self.baseline_file[bad_type]
        #        break

        # Check to see if all of the most recent entries are comparing to the same
        # baseline file and have the same obs times. If not, we'll still plot all



        # Read in the data, or create an empty array
        png_file = self.background_file.replace('.fits', '.png')
        full_path_background_file = os.path.join(OUTPUT_DIR, 'bad_pixel_monitor/', png_file)
        if os.path.isfile(full_path_background_file):
            image = read_png(full_path_background_file)
        else:
            print(f'Background_file {full_path_background_file} is not a valid file')
            #image = np.zeros((self._detlen, self._detlen))
            image = None
            #title_text = f'{self.detector}: New bad pix from {self.data_type}. {self.num_files} files.'

        #start_time = Time(float(self.obs_start_time), format='mjd').tt.datetime.strftime("%m/%d/%Y")
        #end_time  = Time(float(self.obs_end_time), format='mjd').tt.datetime.strftime("%m/%d/%Y")

        start_time = self.obs_start_time.strftime("%m/%d/%Y")
        end_time = self.obs_end_time.strftime("%m/%d/%Y")

        title_text = f'{self.detector}: New {self.badpix_type} pix: from {self.num_files} files. {start_time} to {end_time}'

        #ny, nx = image.shape
        #img_mn, img_med, img_dev = sigma_clipped_stats(image[4: ny - 4, 4: nx - 4])

        # Create figure
        self.plot = figure(title=title_text, tools='pan,box_zoom,reset,wheel_zoom,save',
                           x_axis_label="Pixel Number", y_axis_label="Pixel Number",)
        self.plot.x_range.range_padding = self.plot.y_range.range_padding = 0

        # Create the color mapper that will be used to scale the image
        #mapper = LinearColorMapper(palette='Viridis256', low=(img_med-5*img_dev) ,high=(img_med+5*img_dev))

        # Plot image
        if image is not None:
            imgplot = self.plot.image(image=[image], x=0, y=0, dw=nx, dh=ny, color_mapper=mapper, level="image")
        else:
            # If the background image is not present, manually set the x and y range
            self.plot.x_range.start = 0
            self.plot.x_range.end = self._detlen
            self.plot.x_range.start = 0
            self.plot.x_range.end = self._detlen

        legend_title = f'Compared to baseline file {os.path.basename(self.baseline_file)}'

        # Overplot locations of bad pixels for all bad pixel types
        plot_legend = self.overplot_bad_pix()

        legend = Legend(items=[plot_legend],
                        location="center",
                        orientation='vertical',
                        title = legend_title)

        self.plot.add_layout(legend, 'below')




    def overplot_bad_pix(self):
        """Add a scatter plot of potential new bad pixels to the plot

        Returns
        -------
        legend_item : tup
            Tuple of legend text and associated plot. Will be converted into
            a LegendItem and added to the plot legend
        """
        numpix = len(self.coords[0])

        #######TEST - if too many points, cut them way down
        if numpix > 2:
            self.coords = (self.coords[0][0:2], self.coords[1][0:2])
            numpix = 2
        #########TEST - remove before merging



        source = ColumnDataSource(data=dict(pixels_x=self.coords[0],
                                            pixels_y=self.coords[1],
                                            values=[self.badpix_type] * numpix
                                            )
                                  )

        # Overplot the bad pixel locations
        badpixplots = self.plot.circle(x='pixels_x', y='pixels_y', source=source, color='blue')

        # Create hover tools for the bad pixel types
        hover_tool = HoverTool(tooltips=[(f'{self.badpix_type} (x, y):', '(@pixels_x, @pixels_y)'),
                                         ],
                               renderers=[badpixplots])
        # Add tool to plot
        self.plot.tools.append(hover_tool)

        # Add to the legend
        text = f"{numpix} potential new {self.badpix_type} pix compared to baseline"

        # Create a tuple to be added to the plot legend
        legend_items = (text, [badpixplots])
        return legend_items



class BadPixTrendPlot():
    """Create a plot showing the location of a certain type of bad pixel
    """
    def __init__(self, detector_name, badpix_type, entry):
        self.detector = detector_name
        self.badpix_type = badpix_type
        self.detector, self.num_pix, self.time = entry
        self.create_plot()

    def create_plot(self):
        """Takes the data, places it in a ColumnDataSource, and creates the figure
        """
        # This plot will eventually be saved to an html file by Bokeh. However, when
        # we place the saved html lines into our jinja template files, we cannot have
        # datetime formatted data in the hover tool. This is because the saved Bokeh
        # html will contain lines such as "time{%d %m %Y}". But jinja sees this and
        # interprets the {%d as an html tag, so when you try to load the page, it
        # crashes when it finds a bunch of "d" tags that are unclosed. To get around
        # this, we'll create a list of string representations of the datetime values
        # here, and place these in the columndatasource to be used with the hover tool
        string_times = [e.strftime('%d %b %Y %H:%M') for e in self.time]

        # Create a ColumnDataSource for the main amp to use
        source = ColumnDataSource(data=dict(num_pix=self.num_pix,
                                            time=self.time,
                                            string_time=string_times,
                                            value=[self.badpix_type] * len(self.num_pix)
                                            )
                                    )

        self.plot = figure(title=f'{self.detector}: New {self.badpix_type} Pixels', tools='pan,box_zoom,reset,wheel_zoom,save',
                           background_fill_color="#fafafa")

        # Plot the "main" amp data along with error bars
        self.plot.scatter(x='time', y='num_pix', fill_color="navy", alpha=0.75, source=source)

        hover_tool = HoverTool(tooltips=[('# Pixels:', '@num_pix'),
                                         ('Date:', '@string_time')
                                         ])
        self.plot.tools.append(hover_tool)

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
        time_pad = (max(self.time) - min(self.time)) * 0.05
        if time_pad == datetime.timedelta(seconds=0):
            time_pad = datetime.timedelta(days=1)
        self.plot.x_range.start = min(self.time) - time_pad
        self.plot.x_range.end = max(self.time) + time_pad
        self.plot.grid.grid_line_color="white"
        self.plot.xaxis.axis_label = 'Date'
        self.plot.yaxis.axis_label = f'Number of {self.badpix_type} pixels'


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
    num_bad_types = len(plots['trending'])
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
    """



    # Create a list of plots where each plot shows one flavor of bad pixel
    all_plots = []
    for badtype in plots["trending"]:
        rowplots = [plots["new_pix"][badtype], plots["trending"][badtype]]
        all_plots.append(rowplots)

    # Now create a layout that holds the lists
    plot_layout = layout(all_plots)

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
