#! /usr/bin/env python

"""Module that can be used to read in a JWST observation and display one frame
    (from any extension) as an interactive Bokeh image.
    Authors
    -------
        - Bryan Hilbert
    Use
    ---
        This module can be imported and called as such:
        ::
            from jwql.xxx.xxx import InteractivePreviewImg
            file = 'jw01602001001_02102_00001_nrcb2_cal.fits'
            im = InteractivePreviewImg(
                file, low_lim=None, high_lim=None, scaling='lin', contrast=0.4, extname='DQ')
        Required Arguments:
        ''filename'' - Name of a fits file containing a JWST observation
    """
from copy import deepcopy
import os

from astropy.io import fits
from astropy.visualization import ZScaleInterval, MinMaxInterval, PercentileInterval
import numpy as np
from bokeh.embed import components
from bokeh.layouts import layout
from bokeh.models import (
    BasicTicker, BoxZoomTool, Button, ColorBar, CustomJS, Div, HoverTool,
    LinearColorMapper, LogColorMapper, LogTicker, RadioGroup, Row, Select, Spacer,
    Spinner, WheelZoomTool)
from bokeh.plotting import figure, output_file, show, save

from jwst.datamodels import dqflags


class InteractivePreviewImg:
    """Class to create the interactive Bokeh figure.
    """

    def __init__(self, filename, low_lim=None, high_lim=None, scaling='log', contrast=None, extname='SCI',
                 group=None, integ=None, mask=None, save_html=None, show=False):
        """Populate attributes, read in data, and create the Bokeh figure
        Parameters
        ----------
        filename : str
            Name of fits file containing observation data
        low_lim : float
            Signal value to use as the lower limit of the displayed image. If None, it will be calculated
            using the ZScale function
        high_lim : float
            Signal value to use as the upper limit of the displayed image. If None, it will be calculated
            using the ZScale function
        scaling : str
            Can be 'log' or 'lin', indicating logarithmic or linear scaling
        contrast : float
            Used in the ZScale function to calculated ``low_lim`` and ''high_lim``. Larger values result
            in a larger range between ``low_lim`` and ``high_lim``.
        extname : str
            Extension name within ``filename`` to read in.
        integ : int or list
            If an integer, this is the integration number of the data to be read in. Defaults to 0 (first
            integration). If a 2-element list, this lists the integration numbers of 2 frames to be read in
            and subtracted prior to display.
        group : int or list
            If an integer, this is the group number within ``integ`` to read in and display. Defaults to -1
            (final group of ``integration``). If a 2-element list, this lists the group numbers corresponding
            to the 2-element list in ``integ`` for the 2 frames to be read in and subtracted prior to display.
        mask : numpy.ndarray
            Mask to use in order to avoid some pixels when auto-scaling. Pixels with a value other than 0 will
            be ignored when auto-scaling.
        save_html : str
            Name of html file to save the figure to. If None, the components are returned instead.
        show : bool
            If True, the figure is shown on the screen rather than being saved or returned. Overrides ``save_html``.
        """
        self.filename = filename
        self.low_lim = low_lim
        self.high_lim = high_lim
        self.scaling = scaling
        self.contrast = contrast
        self.extname = extname.upper()
        self.mask = mask
        self.show = show
        self.save_html = save_html

        # Allow sending in of None without overriding defaults
        if group is None:
            group = -1
        if integ is None:
            integ = 0

        # Determine the min and max values to use for the display
        if self.contrast is None:
            self.contrast = 0.25
        if isinstance(group, list):
            if len(group) > 2:
                raise ValueError(
                    'group must be an integer or 2-element list')
        self.group = group
        if isinstance(integ, list):
            if len(integ) > 2:
                raise ValueError(
                    'integ must be an integer or 2-element list')
        self.integ = integ
        self.get_data()
        if 'DQ' in self.extname:
            self.get_bits()
        self.script, self.div = self.create_bokeh_image()

    def create_bokeh_image(self):
        """Method to create the figure
        """
        limits = self.get_scale()
        if self.low_lim is not None:
            limits = (self.low_lim, limits[1])
        if self.high_lim is not None:
            limits = (limits[0], self.high_lim)

        # handle log or linear scaling
        if limits[0] <= 0:
            log_limits = (1e-4, limits[1])
        else:
            log_limits = limits
        log_color_mapper = LogColorMapper(
            palette="Viridis256", low=log_limits[0], high=log_limits[1])
        log_ticker = LogTicker()
        lin_color_mapper = LinearColorMapper(
            palette="Viridis256", low=limits[0], high=limits[1])
        lin_ticker = BasicTicker()
        active = int(self.scaling == 'log')

        yd, xd = self.data.shape
        info = dict(image=[self.data], x=[0], y=[0], dw=[xd], dh=[yd])
        if 'DQ' in self.extname:
            info["dq"] = [self.bit_list]
        if not self.show and self.save_html is not None:
            output_file(filename=self.save_html,
                        title=os.path.basename(self.filename))

        # fix figure aspect from data aspect
        # bokeh throws errors if plot is too small, so make sure
        # the smaller dimension has reasonable size
        if xd > yd:
            plot_width = 800
            plot_height = int(plot_width * yd / xd)
            if plot_height < 400:
                plot_height = 400
        else:
            plot_height = 800
            plot_width = int(plot_height * xd / yd)
            if plot_width < 400:
                plot_width = 400

        fig = figure(tools='pan,reset,save', match_aspect=True,
                     plot_width=plot_width, plot_height=plot_height)
        fig.add_tools(BoxZoomTool(match_aspect=True))
        fig.add_tools(WheelZoomTool(zoom_on_axis=False))

        # make both linear and log scale images to allow toggling between them
        images = []
        color_bars = []
        scales = ((lin_color_mapper, lin_ticker), (log_color_mapper, log_ticker))
        for i, config in enumerate(scales):
            color_mapper, ticker = config
            visible = (i == active)
            img = fig.image(source=info, image='image',
                            level="image", color_mapper=color_mapper, visible=visible)
            color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12, ticker=ticker,
                                 title=self.signal_units, bar_line_color='black',
                                 minor_tick_line_color='black', major_tick_line_color='black',
                                 visible=visible)
            fig.add_layout(color_bar, 'below')
            images.append(img)
            color_bars.append(color_bar)

        # limit whitespace around image as much as possible
        fig.x_range.range_padding = fig.y_range.range_padding = 0
        if xd >= yd:
            fig.x_range.start = 0
            fig.x_range.end = xd
            fig.x_range.bounds = (0, xd)
        if yd >= xd:
            fig.y_range.start = 0
            fig.y_range.end = yd
            fig.y_range.bounds = (0, yd)

        if 'DQ' not in self.extname:
            hover_tool = HoverTool(tooltips=[("(x,y)", "($x{0.2f}, $y{0.2f})"),
                                             ('Value', '@image{0.4f}')
                                             ], mode='mouse', renderers=images)
        else:
            hover_tool = HoverTool(tooltips=[("(x,y)", "($x{0.2f}, $y{0.2f})"),
                                             ('Value', '@dq')
                                             ], mode='mouse', renderers=images)
        self.create_figure_title()
        fig.title.text = self.title
        fig.xaxis.axis_label = 'Pixel'
        fig.yaxis.axis_label = 'Pixel'
        fig.tools.append(hover_tool)

        # add interactive widgets
        widgets = self.add_interactive_controls(images, color_bars)
        box_layout = layout(children=[fig, *widgets])

        # Show figure on screen if requested
        if self.show:
            show(box_layout)
        elif self.save_html is not None:
            save(box_layout)
        else:
            return components(box_layout)

    def add_interactive_controls(self, images, color_bars):
        """
        Add client-side controls for images.

        Currently includes image scaling and limit setting controls.

        Parameters
        ----------
        images : list of bokeh.models.Image
            2-element list of images. The first is linear scale, second is log scale.
            Only one should be visible at any time.
        color_bars : list of bokeh.models.ColorBar
            2-element list of color bars, matching the images.

        Returns
        -------
        widgets: list of bokeh.Widget
            Widgets to add to the page layout.
        """
        # active scaling (0=linear, 1=log)
        active = int(self.scaling == 'log')

        tools_label = Div(text="<h4>Image Settings</h4>")

        scale_label = Div(text="Scaling:")
        scale_group = RadioGroup(labels=["linear", "log"],
                                 inline=True, active=active)
        scale_set = Row(scale_label, scale_group,
                        css_classes=['mb-4'])

        current_low = images[active].glyph.color_mapper.low
        current_high = images[active].glyph.color_mapper.high
        preset_limits = {'ZScale': (current_low, current_high),
                         'Min/Max': MinMaxInterval().get_limits(self.data),
                         '99.5%': PercentileInterval(99.5).get_limits(self.data),
                         '99%': PercentileInterval(99).get_limits(self.data),
                         '95%': PercentileInterval(95).get_limits(self.data),
                         '90%': PercentileInterval(90).get_limits(self.data)}
        options = [*preset_limits.keys(), 'Custom']
        preset_label = Div(text="Percentile presets:")
        preset_select = Select(value='ZScale', options=options, width=120)
        preset_set = Row(preset_label, preset_select)

        limit_label = Div(text="Limits:")
        limit_low = Spinner(title="Low", value=current_low)
        limit_high = Spinner(title="High", value=current_high)
        reset = Button(label='Reset', button_type='primary')
        limit_set = Row(limit_label, limit_low, limit_high,
                        css_classes=['mb-4'])

        # JS callbacks for client side controls

        # set alternate image visibility when scale selection changes
        scale_group.js_on_click(CustomJS(args={'i1': images[0], 'c1': color_bars[0],
                                               'i2': images[1], 'c2': color_bars[1]},
                                         code="""
            if (i1.visible == true) {
                i1.visible = false;
                c1.visible = false;
                i2.visible = true;
                c2.visible = true;
            } else {
                i1.visible = true;
                c1.visible = true;
                i2.visible = false;
                c2.visible = false;
            }
        """))

        # set scaling limits from select box on change
        limit_reset = CustomJS(
            args={'setting': preset_select, 'limits': preset_limits, 'low': limit_low,
                  'high': limit_high, 'scale': scale_group},
            code="""
                if (setting.value != "Custom") {
                    if (scale.active == 1 && limits[setting.value][0] <= 0) {
                        low.value = 0.0001;
                    } else {
                        low.value = limits[setting.value][0];
                    }
                    high.value = limits[setting.value][1];
                }
                """)
        preset_select.js_on_change('value', limit_reset)

        # set scaling limits from text boxes on change
        for i in range(len(images)):
            limit_low.js_link('value', images[i].glyph.color_mapper, 'low')
            limit_low.js_link('value', color_bars[i].color_mapper, 'low')
            limit_high.js_link('value', images[i].glyph.color_mapper, 'high')
            limit_high.js_link('value', color_bars[i].color_mapper, 'high')

        # reset boxes to preset range on button click
        reset.js_on_click(limit_reset)

        # also reset when swapping limit style
        scale_group.js_on_click(limit_reset)

        # return widgets
        spacer = Spacer(height=20)
        return [tools_label, scale_set, preset_set, limit_set, reset, spacer]

    def create_figure_title(self):
        """Create title for the image"""
        self.title = f'{os.path.basename(self.filename)}, {self.extname}'
        if isinstance(self.group, list) and isinstance(self.integ, list):
            self.title += f', Int {self.integ[0]}, Group {self.group[0]} - Int {self.integ[1]}, Group {self.group[1]}'
        else:
            if isinstance(self.integ, int):
                self.title += f', Int {self.integ}'
            elif isinstance(self.integ, list):
                self.title += f', Int ({self.integ[0]}-{self.integ[1]})'

            if isinstance(self.group, int):
                self.title += f', Group {self.group}'
            elif isinstance(self.group, list):
                self.title += f', Group ({self.group[0]}-{self.group[1]})'

    def get_bits(self):
        """Translate the numerical DQ values in a 2D array into a 2D array where each entry is
        a list of the DQ mnemonics that apply to that pixel.
        """
        self.bit_list = np.empty(self.data.shape, dtype=object)
        goodpix = np.where(self.data == 0)
        self.bit_list[goodpix] = ['GOOD']
        badpix = np.where(self.data != 0)
        for i in range(len(badpix[0])):
            self.bit_list[badpix[0][i], badpix[1][i]] = list(dqflags.dqflags_to_mnemonics(
                self.data[badpix[0][i], badpix[1][i]], mnemonic_map=dqflags.pixel))

    def get_data(self):
        """Read in the data from the given fits file and extension name
        """
        with fits.open(self.filename) as hdulist:
            header = hdulist[self.extname].header
            data_shape = hdulist[self.extname].data.shape
            self.index_check(data_shape)
            if len(data_shape) == 4:
                self.data = hdulist[self.extname].data[self.integ,
                                                       self.group, :, :]
            elif len(data_shape) == 3:
                self.data = hdulist[self.extname].data[self.integ, :, :]
                self.group = None
            elif len(data_shape) == 2:
                self.data = hdulist[self.extname].data
                self.group = None
                self.integ = None

        # If a difference image is requested, create the difference image here
        if len(self.data.shape) == 3 and (isinstance(self.group, list) or isinstance(self.integ, list)):
            diff_img = self.data[0, :, :] * 1. - self.data[1, :, :]
            self.data = diff_img

        # Get the units of the data. This will be reported as the title of the colorbar
        try:
            self.signal_units = header['BUNIT']
        except KeyError:
            self.signal_units = ''

    def get_scale(self):
        """Calculate the limits for the display, following the ZScale function
        originally created or IRAF.
        """
        z = ZScaleInterval(contrast=self.contrast)
        if self.mask is None:
            limits = z.get_limits(self.data)
        else:
            goodpix = self.mask == 0
            limits = z.get_limits(self.data[goodpix])
        return limits

    def index_check(self, shapes):
        """Check that the group and integ indexes are compatible with the data shape. If the
        input data are 3D (e.g. from a calints or rateints file), then self.group is ignored.
        Similarly, if the input data are 2D, both self.group and self.integ are ignored.
        Parameters
        ----------
        shapes : tuple
            Tuple of the dimensions of the data in ``self.filename``
        """
        checks = [True]

        # Put groups and ints into lists in all cases, to make comparisons easier
        if isinstance(self.group, int):
            group = [self.group]
            conv_group_to_int = True
        else:
            group = deepcopy(self.group)
            conv_group_to_int = False
        if isinstance(self.integ, int):
            integ = [self.integ]
            conv_integ_to_int = True
        else:
            integ = deepcopy(self.integ)
            conv_integ_to_int = False

        # Check groups and integs vs data shape. If the indexes are negative, translate to
        # the appropriate positive value. This is more for the title of the figure than the check here.
        if len(shapes) == 4:
            group = [shapes[1] + g if g < 0 else g for g in group]
            checks.append(np.all(np.array(group) < shapes[1]))
            integ = [shapes[0] + i if i < 0 else i for i in integ]
            checks.append(np.all(np.array(integ) < shapes[0]))
        elif len(shapes) == 3:
            integ = [shapes[0] + i if i < 0 else i for i in integ]
            checks.append(np.all(np.array(integ) < shapes[0]))

        if not np.all(checks):
            raise ValueError(
                f'Requested groups {group} or integs {integ} are larger than the input data size of {shapes}.')

        # Return the updated values to the same object type as they were input
        if conv_group_to_int:
            self.group = group[0]
        else:
            self.group = group
        if conv_integ_to_int:
            self.integ = integ[0]
        else:
            self.integ = integ
