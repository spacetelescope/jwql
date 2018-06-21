#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May  2 10:12:12 2018

@author: gkanarek

The JS9 interface, which I'm using as a starting starting point, has 8
"workspaces" (in Ginga jargon):
   - a large viewpane with the main display ("MAIN")
   - a smaller viewpane showing the full image with the zoom box indicated ("PAN")
   - a histogram plot for the image ("HIST")
   - an encircled energy plot for the selected region ("PSF")
   - x, y, and radial projections (only the encircled region? not clear) ("XPROJ", "YPROJ", "RPROJ")
   - a 3D plot of the image ("3D")

In this iteration, I'm omitting all the JS9 control buttons, for simplicity
"""

import yaml
import os

import factory

from ginga.web.bokehw import ImageViewBokeh as ivb
from ginga.misc import log
from ginga.AstroImage import AstroImage
from ginga import AutoCuts

import numpy as np

formats = """
Axis:
    visible: False
"""

class JWQLViewerParserError(Exception):
    """
    A custom error for problems with parsing the interface files.
    """
    
class JWQLViewer(object):
    """
    This uses an adaptation of the YAML templating framework that I created for 
    SYOTools, because I find it much easier to work with. The actual tool
    structure is templated in the 'interface.yaml' file, and the specific
    parsing & construction algorithms are in factory.py.
    """
    
    #Here we assign the constructor methods
    mapping_factory = factory.mapping_factory
    sequence_factory = factory.sequence_factory
    scalar_factory = factory.scalar_factory
    figure_constructor = factory.figure_constructor
    document_constructor = factory.document_constructor
    
    #Interface attributes
    format_string = formats
    interface_file = "interface.yaml"
    
    #Some tunable settings
    pan_scale = 0.05
    initial_zoom = 1.0
    zoom_speed = 0.02
    
    def self_constructor(self, loader, tag_suffix, node):
        """
        A multi_constructor for `!self` tag in the interface file.
        """
        yield eval("self"+tag_suffix, globals(), locals())

    
    def __init__(self, fitsfile=""):
        #initialize the Ginga stuff
        self.logger = log.get_logger("ginga", level=20, log_file="/tmp/ginga.log")
        self.autocuts = AutoCuts.Histogram(self.logger)
        self.selected_data = None
        self.box_corners = []
        
        #Handle YAML construction
        self.formats = {}
        self.refs = {}
        
        self.document = None
        
        #Register constructors
        for m in factory.mappings:
            yaml.add_constructor(u"!"+m+":", self.mapping_factory(m))
        for s in factory.sequences:
            yaml.add_constructor(u"!"+s+":", self.sequence_factory(s))
        for s in factory.scalars:
            yaml.add_constructor(u"!"+s+":", self.scalar_factory(s))
        
        yaml.add_constructor(u"!Figure:", self.figure_constructor)
        yaml.add_constructor(u"!Document:", self.document_constructor)
        
        yaml.add_multi_constructor(u"!self", self.self_constructor)
        
        #Build the interface from the file
        self.include_formatting()
        self.parse_interface()
        
        #Attach the viewer to the figure, and do more Ginga things
        self.viewer = ivb.CanvasView(self.logger)
        self.viewer.set_figure(self.refs["main_figure"])
        self.viewer.set_zoom_algorithm('rate')
        self.panviewer = ivb.CanvasView(self.logger)
        self.panviewer.set_figure(self.refs["pan_image"])
        bd = self.viewer.get_bindings()
        bd.enable_all(True)
        
        if fitsfile:
            self.load_fits(fitsfile)
            
        #remove toolbars
        for ref in ["main_figure", "pan_image", "hist_plot", "encl_plot",
                    "xproj_plot", "yproj_plot", "rproj_plot"]:
            self.remove_toolbar(ref)
        
        self.refs["encl_plot"].yaxis[0].formatter = self.refs["encl_formatter"]

    def remove_toolbar(self, ref):
        self.refs[ref].toolbar.logo = None
        self.refs[ref].toolbar_location = None
        
    def zoom_callback(self, attr, old, new):
        img = self.viewer.get_image()
        if img is None or not new["value"]:
            return
        zoom = self.initial_zoom + self.zoom_speed * new["value"][0]
        #zoom = self.refs["zoom_slider"].value
        self.viewer.zoom_to(int(zoom))
        self.initial_zoom = zoom
        scale = self.viewer.get_scale()
        self.logger.info("%f" % scale)
        self.viewer.onscreen_message("%f" % (scale), delay=0.3)
        self.update_pan_rect()
        self.update_selected_box()
            
    def pan_callback(self, attr, old, new):
        xc, yc = self.viewer.get_canvas_xy(*self.viewer.get_pan())
        dx, dy = new['value']
        x0, y0 = self.viewer.get_data_xy(xc + dx * self.pan_scale, 
                                         yc + dy * self.pan_scale)
        self.viewer.set_pan(x0, y0)
        self.update_pan_rect()
    
    def pan_tap_callback(self, attr, old, new):
        x0, y0 = new['value']
        x1, y1 = self.panviewer.get_data_xy(x0, y0)
        w, h = self.viewer.get_data_size()
        self.viewer.set_pan(x1, h - y1)
        self.update_pan_rect()
        self.update_selected_box()
    
    def update_pan_rect(self):
        px0, py0 = zip(*self.viewer.get_pan_rect())
        w, h = self.viewer.get_data_size()
        px, py = self.panviewer.get_canvas_xy(px0, [h - y for y in py0])
        px, py = px.tolist(), py.tolist()
        
        self.refs["pan_box_source"].data = {'x': px + [px[0]],
                                            'y': py + [py[0]]}
    
    def update_plots(self):
        if self.selected_data is None:
            for ref in ['hist', 'encl', 'xproj', 'rproj', 'yproj']:
                self.refs[ref+"_source"].data = {'x': [], 'y': []}
            self.refs['surf_source'].data = {'x': [0, 0], 'y': [0, 0], 'z': [0, 0]}
            return
        self.update_histogram()
        self.update_enclosed()
        self.update_xproj()
        self.update_yproj()
        self.update_rproj()
        self.update_surf()
    
    def update_xproj(self):
        xproj = np.sum(self.selected_data, axis=0)
        nx = xproj.size
        xpix = np.arange(nx, dtype=float)
        
        self.refs["xproj_source"].data = {'x': xpix.tolist(), 
                                          'y': xproj.tolist()}
        self.refs["xproj_xrange"].bounds = (0, nx-1)
        self.refs["xproj_xrange"].end = nx-1
        self.refs["xproj_yrange"].bounds = (xproj.min(), xproj.max())
        self.refs["xproj_yrange"].start = xproj.min()
        self.refs["xproj_yrange"].end = xproj.max() / 0.9
    
    def update_yproj(self):
        yproj = np.sum(self.selected_data, axis=1)
        ny = yproj.size
        ypix = np.arange(ny, dtype=float)
        
        self.refs["yproj_source"].data = {'x': ypix.tolist(), 
                                          'y': yproj.tolist()}
        self.refs["yproj_xrange"].bounds = (0, ny-1)
        self.refs["yproj_xrange"].end = ny-1
        self.refs["yproj_yrange"].bounds = (yproj.min(), yproj.max())
        self.refs["yproj_yrange"].start = yproj.min()
        self.refs["yproj_yrange"].end = yproj.max() / 0.9
    
    def update_rproj(self):
        rproj = self.selected_data.ravel()
        ny, nx = self.selected_data.shape
        hx, hy = nx / 2, ny / 2
        y, x = np.mgrid[:ny, :nx]
        dx, dy = x - hx, y - hy
        dd = np.sqrt(dx*dx + dy*dy).ravel() #distance from center
        
        self.refs["rproj_source"].data = {'x': dd.ravel().tolist(), 
                                          'y': rproj.tolist()}
        self.refs["rproj_xrange"].bounds = (0, dd.max())
        self.refs["rproj_xrange"].end = dd.max()
        self.refs["rproj_yrange"].bounds = (rproj.min(), rproj.max())
        self.refs["rproj_yrange"].start = rproj.min()
        self.refs["rproj_yrange"].end = rproj.max() / 0.9
    
    def update_surf(self):
        ny, nx = self.selected_data.shape
        y, x = np.mgrid[:ny, :nx]
        self.refs["surf_source"].data = {'x': x.ravel().tolist(),
                                         'y': y.ravel().tolist(),
                                         'z': self.selected_data.ravel().tolist()}
        self.refs["surf_xrange"].bounds = (0, nx-1)
        self.refs["surf_xrange"].end = nx-1
        self.refs["surf_yrange"].bounds = (0, ny-1)
        self.refs["surf_yrange"].end = ny-1
        self.refs["surf_zrange"].bounds = (self.selected_data.min(),
                                           self.selected_data.max())
        self.refs["surf_zrange"].start = self.selected_data.min()
        self.refs["surf_zrange"].end = self.selected_data.max()
        
    def update_histogram(self):
        nb = max(100, self.selected_data.size//2)
        hist = self.autocuts.calc_histogram(self.selected_data, numbins=nb)
        x = hist.bins.tolist()
        y = hist.dist.tolist()
        y.append(y[-1])
        self.refs["hist_source"].data = {'x': x, 'y': y}
        self.refs["hist_xrange"].bounds = (hist.loval, hist.hival)
        self.refs["hist_xrange"].start = hist.loval
        self.refs["hist_xrange"].end = hist.hival
        self.refs["hist_yrange"].bounds = (0, max(y))
        self.refs["hist_yrange"].end = max(y)
    
    def update_enclosed(self):
        ny, nx = self.selected_data.shape
        hx, hy = nx / 2, ny / 2
        y, x = np.mgrid[:ny, :nx]
        dx, dy = x - hx, y - hy
        dd = np.sqrt(dx*dx + dy*dy) #distance from center
        #Bin for smoothness
        max_distance = int(np.ceil(dd.max()))
        distance_bins = np.arange(1, max_distance+1)
        tot_energy = np.zeros(max_distance, dtype=float)
        
        for i, d in enumerate(distance_bins):
            in_bounds = (i < dd) & (dd <= d)
            tot = self.selected_data[in_bounds].sum()
            nscale = np.count_nonzero(in_bounds) / ((d*d - i*i) * np.pi)
            tot_energy[i] = tot / nscale
            
        tot_energy = np.cumsum(tot_energy)
        
        self.refs["encl_source"].data = {'x': distance_bins.tolist(), 
                                         'y': tot_energy.tolist()}
        self.refs["encl_xrange"].bounds = (0, max_distance)
        self.refs["encl_xrange"].end = max_distance
        self.refs["encl_yrange"].bounds = (tot_energy.min(), 
                                           tot_energy.max())
        self.refs["encl_yrange"].start = tot_energy.min()
        self.refs["encl_yrange"].end = tot_energy.max()
        
    
    def load_callback(self, attr, old, new):
        fitsfile = self.refs["fitsfile_input"].value
        if fitsfile:
            self.load_fits(fitsfile)
            self.update_plots
    
    def box_callback(self, attr, old, new):
        img = self.viewer.get_image()
        if not new['value'] or img is None:
            self.selected_data = None
            return
        x0, y0, x1, y1 = new['value']
        ny = self.refs["main_figure"].y_range.end
        
        data = self.viewer.get_image().get_data()
        x0, x1 = sorted([x0, x1])
        y0, y1 = sorted([y0, y1])
        xi0, yi0 = map(int, self.viewer.get_data_xy(x0, ny - y0))
        xi1, yi1 = map(int, self.viewer.get_data_xy(x1, ny - y1))
        w, h = self.viewer.get_data_size()
        self.selected_data = data[yi1:yi0+1, xi0:xi1+1]
        self.box_corners = [xi0, yi0, xi1, yi1]
        
        self.update_selected_box()
        self.update_plots()
    
    def update_selected_box(self):
        if not self.box_corners:
            return
        x0, y0, x1, y1 = self.box_corners
        
        niy = self.refs["main_figure"].y_range.end
        npy = self.refs["pan_image"].y_range.end
        
        xi0, yi0 = self.viewer.get_canvas_xy(x0, y0)
        xi1, yi1 = self.viewer.get_canvas_xy(x1, y1)
        
        yi0 = niy - yi0
        yi1 = niy - yi1
        
        rx = (xi0 + xi1) / 2
        ry = (yi0 + yi1) / 2
        rh = yi1 - yi0
        rw = xi1 - xi0
        
        self.refs["select_box_source_main"].data = {'rx': [rx], 'ry': [ry],
                                                    'rw': [rw], 'rh': [rh]}
        
        xp0, yp0 = self.panviewer.get_canvas_xy(x0, y0)
        xp1, yp1 = self.panviewer.get_canvas_xy(x1, y1)
        
        yp0 = npy - yp0
        yp1 = npy - yp1
        
        rx = (xp0 + xp1) / 2
        ry = (yp0 + yp1) / 2
        rh = yp1 - yp0
        rw = xp1 - xp0
        
        self.refs["select_box_source_pan"].data = {'rx': [rx], 'ry': [ry],
                                                   'rw': [rw], 'rh': [rh]}
        
        
    def load_fits(self, fitsfile):
        """
        Load a FITS image into the viewer.
        """
        image = AstroImage(logger=self.logger)
        image.load_file(fitsfile)
        self.viewer.set_image(image)
        panimage = AstroImage(logger=self.logger)
        panimage.load_file(fitsfile)
        self.panviewer.set_image(panimage)
    
    def inspector_callback(self, attr, old, new):
        outmsg = "Sorry, I don't recognize that."
        key = new['value'][0]
        if key in self.refs:
            print('found {}'.format(key))
            outmsg = str(self.refs[key].data)
        self.refs["inspector_output"].text = outmsg
    
    def include_formatting(self):
        """
        This should simply be a dictionary of formatting keywords.
        """
        if not self.format_string:
            return
        
        self.formats = yaml.load(self.format_string)
    
    def parse_interface(self):
        """
        This is the workhorse YAML parser, which creates the interface based
        on the layout file.
        
        `interface_file` is the path to the interface .yaml file to be parsed.
        """
        
        if not self.interface_file:
            raise NotImplementedError("Interface file required.")
        
        #Read the interface file into a string
        filepath = os.path.abspath(os.path.expanduser(self.interface_file))
        if not os.path.exists(filepath):
            raise JWQLViewerParserError("Interface file path does not exist.")
        with open(filepath) as f:
            interface = f.read()
        
        #First, let's make sure that there's a Document in here
        if '!Document' not in interface:
            raise JWQLViewerParserError("Interface file must contain a Document tag")
        
        #Now, since we've registered all the constructors, we can parse the 
        #entire string with yaml. We don't need to assign the result to a
        #variable, since the constructors store everything in self.refs
        #(and self.document, for the document)
        
        self.full_stream = list(yaml.load_all(interface))

JWQLViewer()