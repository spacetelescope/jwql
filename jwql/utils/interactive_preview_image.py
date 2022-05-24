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
         im = InteractivePreviewImg(file, low_lim=None, high_lim=None, scaling='lin', contrast=0.4, extname='DQ')
     Required Arguments:
     ''filename'' - Name of a fits file containing a JWST observation
 """
 from copy import deepcopy
 import os

 from astropy.io import fits
 from astropy.visualization import ZScaleInterval
 from bokeh.plotting import figure, show
 import numpy as np
 from bokeh.embed import components
 from bokeh.layouts import column
 from bokeh.models import BasicTicker, ColorBar, HoverTool, LinearColorMapper, LogColorMapper, LogTicker
 from bokeh.plotting import figure, output_file, show, save

 from jwst.datamodels import dqflags


 class InteractivePreviewImg():
     """Class to create the interactive Bokeh figure.
     """
     def __init__(self, filename, low_lim=None, high_lim=None, scaling='log', contrast=None, extname='SCI',
                  group=-1, integ=0, save_html=None, show=False):
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
         self.show = show
         self.save_html = save_html

         # Determine the min and max values to use for the display
         if self.contrast is None:
             self.contrast = 0.25

         if isinstance(group, list):
             if len(group) > 2:
                 raise ValueErorr('group must be an integer or 2-element list')
         self.group = group

         if isinstance(integ, list):
             if len(integ) > 2:
                 raise ValueErorr('integ must be an integer or 2-element list')
         self.integ = integ

         self.get_data()

         if 'DQ' in self.extname:
             self.get_bits()

         self.create_bokeh_image()


     def create_bokeh_image(self):
         """Method to create the figure
         """
         limits = self.get_scale()
         if limits[0] <= 0:
             limits = (1e-4, limits[1])

         if self.low_lim is not None:
             limits = (self.low_lim, limits[1])
         if self.high_lim is not None:
             limits = (limits[0], self.high_lim)

         if self.scaling == 'log':
             color_mapper = LogColorMapper(palette="Viridis256", low=limits[0], high=limits[1])
             ticker = LogTicker()
         elif self.scaling == 'lin':
             color_mapper = LinearColorMapper(palette="Viridis256", low=limits[0], high=limits[1])
             ticker = BasicTicker()

         yd, xd = self.data.shape
         info = dict(image=[self.data], x=[0], y=[0], dw=[yd] , dh=[xd])
         if 'DQ' in self.extname:
             info["dq"] = [self.bit_list]

         if not self.show and self.save_html is not None:
             output_file(filename=self.save_html, title=os.path.basename(self.filename))

         fig = figure(tools='pan,box_zoom,reset,wheel_zoom,save')
         img = fig.image(source=info, image='image', level="image", color_mapper=color_mapper)

         color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12, ticker=ticker, title=self.signal_units, bar_line_color='black',
                              minor_tick_line_color='black', major_tick_line_color='black')
         fig.add_layout(color_bar, 'below')
         fig.x_range.range_padding = fig.y_range.range_padding = 0

         if 'DQ' not in self.extname:
             hover_tool = HoverTool(tooltips=[("(x,y)", "($x{0.2f}, $y{0.2f})"),
                                              ('Value', '@image{0.4f}')
                                             ], mode='mouse', renderers=[img])
         else:
             hover_tool = HoverTool(tooltips=[("(x,y)", "($x{0.2f}, $y{0.2f})"),
                                              ('Value', '@dq')
                                             ], mode='mouse', renderers=[img])
         self.create_figure_title()
         fig.title.text = self.title
         fig.xaxis.axis_label = 'Pixel'
         fig.yaxis.axis_label = 'Pixel'
         fig.tools.append(hover_tool)

         # Show figure on screen if requested
         if self.show:
             show(fig)
         elif self.save_html is not None:
             save(fig)
         else:
             return components(fig)


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
             self.bit_list[badpix[0][i], badpix[1][i]] = list(dqflags.dqflags_to_mnemonics(self.data[badpix[0][i], badpix[1][i]], mnemonic_map=dqflags.pixel))

     def get_data(self):
         """Read in the data from the given fits file and extension name
         """
         with fits.open(self.filename) as hdulist:
             header = hdulist[self.extname].header
             data_shape = hdulist[self.extname].data.shape
             self.index_check(data_shape)
             if len(data_shape) == 4:
                 self.data = hdulist[self.extname].data[self.integ, self.group, :, :]
             elif len(data_shape) == 3:
                 self.data = hdulist[self.extname].data[self.integ, :, :]
                 self.group = None
             elif len(data_shape) == 2:
                 self.data = hdulist[self.extname].data
                 self.group = None
                 self.integ = None

         # If a difference image is requested, create the difference image here
         if len(self.data.shape) == 3 and (isinstance(self.group, list) or isinstance(self.integ, list)):
             diff_img = self.data[0, :, :]*1. - self.data[1, :, :]
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
         limits = z.get_limits(self.data)
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
             raise ValueError(f'Requested groups {group} or integs {integ} are larger than the input data size of {shapes}.')

         # Return the updated values to the same object type as they were input
         if conv_group_to_int:
             self.group = group[0]
         else:
             self.group = group
         if conv_integ_to_int:
             self.integ = integ[0]
         else:
             self.integ = integ