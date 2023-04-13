"""This module contains code for the bad pixel monitor Bokeh plots.

Author
------

    - Bryan Hilbert

Use
---

    This module can be used from the command line like this:

    ::

        from jwql.website.apps.jwql import monitor_pages
        monitor_pages.BadPixelPlots('nircam')
"""

import os

from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from bokeh.embed import components, file_html
from bokeh.io import export_png, show
from bokeh.layouts import layout
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool, Legend, LinearColorMapper, Panel, Tabs, Text, Title
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
from jwql.utils.constants import BAD_PIXEL_MONITOR_MAX_POINTS_TO_PLOT, BAD_PIXEL_TYPES, DARKS_BAD_PIXEL_TYPES
from jwql.utils.constants import DETECTOR_PER_INSTRUMENT, FLATS_BAD_PIXEL_TYPES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import filesystem_path, get_config, read_png

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = get_config()['outputs']


class BadPixelPlots():
    """Class for creating the bad pixel monitor plots and figures to be displayed
    in the web app

    Attributes
    ----------
    instrument : str
        Name of instrument (e.g. 'nircam')

    detectors : list
        List of detectors corresponding to ```instrument```. One tab will be created
        for each detector.

    pixel_table : sqlalchemy table
        Table containing bad pixel information for each detector

    query_table : sqlalchemy table
        Table containing history of bad pixel monitor runs and files used

    _html : str
        HTML for the bad pixel monitor page
    """
    def __init__(self, instrument):
        self.instrument = instrument.lower()

        # Get the relevant database tables
        self.identify_tables()

        #self.detectors = get_unique_values_per_column(self.pixel_table, 'detector')

        self.detectors = sorted(DETECTOR_PER_INSTRUMENT[self.instrument])
        if self.instrument == 'miri':
            self.detectors = ['MIRIMAGE']

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
        lines = self._html.split('\n')

        # List of lines that Bokeh likes to save in the file, but we don't want
        lines_to_remove = ["<!DOCTYPE html>",
                           '<html lang="en">',
                           '  </body>',
                           '</html>']

        # Our Django-related lines that need to be at the top of the file
        hstring = """href="{{'/jwqldb/%s_bad_pixel_stats'%inst.lower()}}" name=test_link class="btn btn-primary my-2" type="submit">Go to JWQLDB page</a>"""
        newlines = ['{% extends "base.html" %}\n', "\n",
                    "{% block preamble %}\n", "\n",
                    f"<title>{JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bad Pixel Monitor- JWQL</title>\n", "\n",
                    "{% endblock %}\n", "\n",
                    "{% block content %}\n", "\n",
                    '  <main role="main" class="container">\n', "\n",
                    f"  <h1>{JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bad Pixel Monitor</h1>\n",
                    "  <hr>\n",
                    f"  <b>View or Download {JWST_INSTRUMENT_NAMES_MIXEDCASE[self.instrument]} Bad Pixel Stats Table:</b>&emsp; <a " + hstring,
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

        self._html = "".join(newlines)


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
        template_dir = os.path.join(os.path.dirname(__file__), '../templates')
        template_file = os.path.join(template_dir, 'bad_pixel_monitor_savefile_basic.html')
        temp_vars = {'inst': self.instrument, 'plot_script': script, 'plot_div':div}
        self._html = file_html(tabs, CDN, f'{self.instrument} bad pix monitor', template_file, temp_vars)

        # Modify the html such that our Django-related lines are kept in place,
        # which will allow the page to keep the same formatting and styling as
        # the other web app pages
        self.modify_bokeh_saved_html()

        # Save html file
        outdir = os.path.dirname(template_file)
        outfile = f'{self.instrument}_bad_pix_plots.html'
        outfile = os.path.join(outdir, outfile)
        with open(outfile, "w") as file:
            file.write(self._html)


class BadPixelData():
    """Class to retrieve and store bad pixel monitor data from the database

    Parameters
    ----------
    pixel_table : sqlalchemy table
        Table containing bad pixel information for each detector

    instrument : str
        Instrument name, e.g. 'nircam'

    detector : str
        Detector name, e.g. 'NRCA1'

    Atributes
    ---------
    background_file : str
        Name of one file used to find the current selection of bad pixels

    badtypes : list
        List of bad pixel types present in ```pixel_table```

    baseline_file : str
        Name of file containing a previous collection of bad pixels, to be
        compared against the new collection of bad pixels

    detector : str
        Detector name, e.g. 'NRCA1'

    instrument : str
        Instrument name, e.g. 'nircam'

    new_bad_pix : dict
        Keys are the types of bad pixels (e.g. 'dead'). The value for each key
        is a 2-tuple. The first element is a list of x coordinates, and the second
        element is a list of y coordinates, corresponding to the locations of that
        type of bad pixel.

    num_files : dict
        Keys are the types of bad pixels (e.g. 'dead'). The value of each is the number
        of files used when searching for that type of bad pixel.

    obs_end_time : dict
        Keys are the types of bad pixels (e.g. 'dead'). The value of each is the ending
        time (datetime instance) of the observations used to find the bad pixels.

    obs_start_time : dict
        Keys are the types of bad pixels (e.g. 'dead'). The value of each is the starting
        time (datetime instance) of the observations used to find the bad pixels.

    pixel_table : sqlalchemy table
        Table containing bad pixel information for each detector

    trending_data : dict
        Keys are the types of bad pixels (e.g. 'dead'). The value of each is a 3-tuple of
        data to be used to create the trending plot. The first element is the detector name,
        the second is a list of the number of bad pixels, and the third is a list of the
        datetimes associated with the bad pixel numbers.
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

        # Get a list of the bad pixel types present in the database
        self.badtypes = get_unique_values_per_column(self.pixel_table, 'type')

        # If the database is empty, return a generic entry showing that fact
        if len(self.badtypes) == 0:
            self.badtypes = ['BAD']

        # Get data for the plot of new bad pixels
        self.get_most_recent_entry()

        # Get data for the trending plots
        for badtype in self.badtypes:
            self.get_trending_data(badtype)


    def get_most_recent_entry(self):
        """Get all nedded data from the database tables.
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

        # Organize the results
        for row in latest_entries_by_type:
            self.new_bad_pix[row.type] = (row.x_coord, row.y_coord)
            self.background_file[row.type] = row.source_files[0]
            self.obs_start_time[row.type] = row.obs_start_time
            self.obs_end_time[row.type] = row.obs_end_time
            self.num_files[row.type] = len(row.source_files)
            self.baseline_file[row.type] = row.baseline_file

        # If no data is retrieved from the database at all, add a dummy generic entry
        if len(self.new_bad_pix.keys()) == 0:
            self.new_bad_pix[self.badtypes[0]] = ([], [])
            self.background_file[self.badtypes[0]] = ''
            self.obs_start_time[self.badtypes[0]] = datetime.datetime.today()
            self.obs_end_time[self.badtypes[0]] = datetime.datetime.today()
            self.num_files[self.badtypes[0]] = 0
            self.baseline_file[self.badtypes[0]] = ''

    def get_trending_data(self, badpix_type):
        """Retrieve and organize the data needed to produce the trending plot.

        Parameters
        ----------
        badpix_type : str
            The type of bad pixel to query for, e.g. 'dead'
        """
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

        # If there was no data in the database, create an empty entry
        if len(num_pix) == 0:
            badtype = badpix_type
            detector = self.detector
            num_pix = [0]
            times = [datetime.datetime.today()]

        # Add results to self.trending_data
        self.trending_data[badpix_type] = (detector, num_pix, times)
        session.close()


class NewBadPixPlot():
    """Class to create a plot showing the location of newly discovered bad pixels of a certain type

    Parameters
    ----------
    detector_name : str
        Name of detector, e.g. NRCA1

    badpix_type : str
        Type of bad pixel, e.g. 'dead'

    nfiles : int
        Number of files used to find the bad pixels

    coords : tuple
        2-tuple. The first element is a list of x coordinates, and the second
        element is a list of y coordinates, corresponding to the locations of that
        type of bad pixel.

    background_file : str
        Name of one of the files used to find the bad pixels

    baseline_file : str
        Name of file containing previously identified bad pixels, which were compared to the
        new collection of bad pixels

    obs_start_time : datetime.datetime
        Datetime of the beginning of the observations used in the search for the bad pixels

    obs_end_time : datetime.datetime
        Datetime of the ending of the observations used in the search for the bad pixels

    Attributes
    ----------
    background_file : str
        Name of one of the files used to find the bad pixels

    badpix_type : str
        Type of bad pixel, e.g. 'dead'

    baseline_file : str
        Name of file containing previously identified bad pixels, which were compared to the
        new collection of bad pixels

    coords : tuple
        2-tuple. The first element is a list of x coordinates, and the second
        element is a list of y coordinates, corresponding to the locations of that
        type of bad pixel.

    detector : str
        Name of detector, e.g. NRCA1

    num_files : int
        Number of files used to find the bad pixels

    obs_start_time : datetime.datetime
        Datetime of the beginning of the observations used in the search for the bad pixels

    obs_end_time : datetime.datetime
        Datetime of the ending of the observations used in the search for the bad pixels

    plot : Bokeh.plotting.figure
        Figure showing the location of the bad pixels on the detector

    _detlen : int
        Number of pixels in one row or column of ```detector```

    _use_png : bool
        Whether or not to create the Bokeh figure using circle glyphs of all bad pixels, or to
        save the plot of bad pixels as a png and load that (in order to reduce data volume.)
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

        # If no background file is given, we fall back to plotting the bad pixels
        # on top of an empty image. In that case, we need to know how large the
        # detector is, just to create an image of the right size.
        if 'MIRI' in self.detector.upper():
            self._detlen = 1024
        else:
            self._detlen = 2048

        # If there are "too many" points then we are going to save the plot as
        # a png rather than send all the data to the browser.\
        self._use_png = False
        if len(self.coords[0]) > BAD_PIXEL_MONITOR_MAX_POINTS_TO_PLOT:
            self._use_png = True

        self.create_plot()

    def create_plot(self):
        """Create the plot by showing background image, and marking the locations
        of new bad pixels on top. We load a png file of the background image rather
        than the original fits file in order to reduce the amount of data in the
        final html file.
        """
        # Read in the data, or create an empty array
        png_file = self.background_file.replace('.fits', '.png')
        full_path_background_file = os.path.join(OUTPUT_DIR, 'bad_pixel_monitor/', png_file)

        if os.path.isfile(full_path_background_file):
            image = read_png(full_path_background_file)
        else:
            image = None

        start_time = self.obs_start_time.strftime("%m/%d/%Y")
        end_time = self.obs_end_time.strftime("%m/%d/%Y")

        title_text = f'{self.detector}: New {self.badpix_type} pix: from {self.num_files} files. {start_time} to {end_time}'

        # Create figure
        # If there are "too many" points then we are going to save the plot as
        # a png rather than send all the data to the browser. In that case, we
        # don't want to add any tools to the figure
        if not self._use_png:
            tools = 'pan,box_zoom,reset,wheel_zoom,save'
            self.plot = figure(title=title_text, tools=tools,
                               x_axis_label="Pixel Number", y_axis_label="Pixel Number")
        else:
            self.plot = figure(tools='') #, x_axis_label="Pixel Number", y_axis_label="Pixel Number")
            self.plot.toolbar.logo = None
            self.plot.toolbar_location = None
            self.plot.min_border = 0
            self.plot.xaxis.visible = False
            self.plot.yaxis.visible = False

        self.plot.x_range.range_padding = self.plot.y_range.range_padding = 0

        # Plot image
        if image is not None:
            ny, nx = image.shape
            #imgplot = self.plot.image(image=[image], x=0, y=0, dw=nx, dh=ny, color_mapper=mapper, level="image")



            # Shift the figure title slightly right in this case to get it
            # to align with the axes
            #self.plot = figure(title=title, x_range=(0, self._detlen), y_range=(0, self._detlen), width=xdim, height=ydim*,
            #                   tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_label="Pixel Number", y_axis_label="Pixel Number")
            self.plot.image_rgba(image=[image], x=0, y=0, dw=self._detlen, dh=self._detlen, alpha=0.5)



        else:
            # If the background image is not present, manually set the x and y range
            self.plot.x_range.start = 0
            self.plot.x_range.end = self._detlen
            self.plot.x_range.start = 0
            self.plot.x_range.end = self._detlen

        legend_title = f'Compared to baseline file {os.path.basename(self.baseline_file)}'

        # Overplot locations of bad pixels for the bad pixel type
        plot_legend = self.overplot_bad_pix()

        # If there are "too many" points, we have already omitted all of the bokeh tools.
        # Now we export as a png and place that into the figure, as a way of reducing the
        # amount of data sent to the browser. This png will be saved and immediately read
        # back in.
        if self._use_png:
            output_filename = full_path_background_file.replace('.png', f'_{self.badpix_type}_pix.png')
            self.switch_to_png(output_filename, title_text)

        # Create and add legend to the figure
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

        if numpix > 0:
            source = ColumnDataSource(data=dict(pixels_x=self.coords[0],
                                                pixels_y=self.coords[1],
                                                values=[self.badpix_type] * numpix
                                                )
                                      )
        else:
            # If there are no new bad pixels, write text within the figure mentioning that
            txt_source = ColumnDataSource(data=dict(x=[self._detlen / 10], y=[self._detlen / 2],
                                          text=[f'No new {self.badpix_type} pixels found']))
            glyph = Text(x="x", y="y", text="text", angle=0., text_color="navy", text_font_size={'value':'20px'})
            self.plot.add_glyph(txt_source, glyph)

            # Insert a fake one, in order to get the plot to be made
            fakex = np.array([0, self._detlen, self._detlen, 0])
            fakey = np.array([0, 0, self._detlen, self._detlen])
            fakex = [int(e) for e in fakex]
            fakey = [int(e) for e in fakey]
            source = ColumnDataSource(data=dict(pixels_x=fakex,
                                                pixels_y=fakey,
                                                values=['N/A'] * len(fakex)
                                                )
                                      )

        # Overplot the bad pixel locations
        # If we have very few bad pixels to plot, increase the size of the circles, in order to make
        # it easier to find them on the plot
        radius = 0.5
        if len(self.coords[0]) < 50:
            radius = 1.0
        pink = '#EC04FF'
        green = '#07FF1F'
        badpixplots = self.plot.circle(x='pixels_x', y='pixels_y', source=source, fill_color=pink, line_color=pink,
                                       fill_alpha=1.0, line_alpha=1.0, radius=radius)

        # Create hover tool for the bad pixel type
        # If there are "too many" points then we are going to save the plot as
        # a png rather than send all the data to the browser. In that case, we
        # don't need a hover tool
        if not self._use_png:
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

    def switch_to_png(self, filename, title):
        """Convert the current Bokeh figure from a figure containing circle glyphs to a png
        representation.

        Parameters
        ----------
        filename : str
            Name of file to save the current figure as a png into

        title : str
            Title to add to the Figure
        """
        # Save the figure as a png
        export_png(self.plot, filename=filename)
        set_permissions(filename)

        # Read in the png and insert into a replacement figure
        fig_array = read_png(filename)
        ydim, xdim = fig_array.shape

        # Create the figure
        self.plot = figure(title=title, x_range=(0, self._detlen), y_range=(0, self._detlen), width=xdim, height=ydim,
                           tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_label="Pixel Number", y_axis_label="Pixel Number")
        self.plot.image_rgba(image=[fig_array], x=0, y=0, dw=self._detlen, dh=self._detlen)

        # Now that the data from the png is in the figure, delete the png
        os.remove(filename)


class BadPixTrendPlot():
    """Class to create a plot of the number of bad pixels of a certain type versus time

    Parameters
    ----------
    detector_name : str
        Name of the detector, e.g. 'NRCA1'

    badpix_type : str
        Type of bad pixel, e.g. 'dead'

    entry : tup
        3-tuple of the data to be plotted. (BadPixelData.trending_data for a certain type
        of bad pixel). The first element is the detector name, the second is a list of
        the number of bad pixels, and the third is a list of the datetimes associated
        with the bad pixel numbers.

    Attributes
    ----------
    detector : str
        Name of the detector, e.g. 'NRCA1'

    badpix_type : str
        Type of bad pixel, e.g. 'dead'

    num_pix : list
        List of the number of bad pixels found for a list of times

    plot : Bokeh.plotting.figure
        Bokeh figure showing a plot of the number of bad pixels versus time

    time : list
        List of datetimes associated with ```num_pix```
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
        Nested dictionary containing a set of plots for an aperture.
        Required keys are 'new_pix' and 'trending'. Each of these contain a
        dictionary where the keys are the types of bad pixels, and the values
        are the Bokeh figures. 'new_pix' and 'trending' should contain the
        same set of keys. 'new_pix' contains the figures showing new bad pixel
        locations, while 'trending' contains the figures showign the number of
        bad pixels with time.

    Returns
    -------
    plot_layout : bokeh.layouts.layout
        Layout containing all of the input figures
    """
    # Create a list of plots where each plot shows one flavor of bad pixel
    all_plots = []
    for badtype in plots["trending"]:
        rowplots = [plots["new_pix"][badtype], plots["trending"][badtype]]
        all_plots.append(rowplots)

    # Now create a layout that holds the lists
    plot_layout = layout(all_plots)

    return plot_layout
