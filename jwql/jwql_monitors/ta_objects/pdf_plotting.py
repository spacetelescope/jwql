#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  3 10:00:57 2019

@author: gkanarek
"""
import matplotlib
matplotlib.use('pdf')

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable


def mk_stamp_report_plot(stamp, oss_results=None):
    '''Make figure compararing images of various processing stages, overplotting location of
    measured locate box and final centroid, and also writing text summary to figure.
    Optionally include comparison with oss results from OSF log.
    (OSS results should really be added to PostageStamp object)
    returns: figure and axes objects of plot created, plus text summary string.
    '''
    fig, ax = plt.subplots(nrows=2, ncols=3, figsize=(16, 9))
    stamp_subplot(stamp, 'slope1', fig, ax[0, 0], lower_percentile=0.25, upper_percentile=99.5)
    stamp_subplot(stamp, 'slope2', fig, ax[0, 1], lower_percentile=0.25, upper_percentile=99.5)
    stamp_subplot(stamp, 'crj', fig, ax[0, 2], lower_percentile=0.25, upper_percentile=99.5)
    stamp_subplot(stamp, 'bkg_subtracted', fig, ax[1, 0], lower_percentile=0.25, upper_percentile=100)
    stamp_subplot(stamp, 'stamp_flat', fig, ax[1, 1], vmin=0, vmax=65535, cmap='gray')
    
    #draw locate boxes
    delta = stamp.check_box_size / 2.0        
    cc = stamp.col_locate_onebase - 1 + stamp.col_corner_stamp
    rr = stamp.row_locate_onebase - 1 + stamp.row_corner_stamp        
    locate_box_col = np.array([cc-delta, cc+delta, cc+delta, cc-delta])
    locate_box_row = np.array([rr-delta, rr-delta, rr+delta, rr+delta])
    ax[1, 0].fill(locate_box_col, locate_box_row, fill=False)        
  
    # mark centroid location
    for iax in np.arange(3):
        ax[0, iax].plot(stamp.col_detector_center, stamp.row_detector_center,'bx',lw=1, ms=6)
    ax[1, 0].plot(stamp.col_detector_center, stamp.row_detector_center,'bx',lw=1, ms=6)
    ax[1, 1].plot(stamp.col_detector_center, stamp.row_detector_center,'cx',lw=1, ms=6)

    #add oss_results to selected images and text results
    if(oss_results is not None):
        cc = oss_results['col_locate'] - 1 + stamp.col_corner_stamp
        rr = oss_results['row_locate'] - 1 + stamp.row_corner_stamp        
        locate_box_col = np.array([cc-delta, cc+delta, cc+delta, cc-delta])
        locate_box_row = np.array([rr-delta, rr-delta, rr+delta, rr+delta])
        for iax in np.arange(3):
            ax[0, iax].fill(locate_box_col, locate_box_row, fill=False, color='cyan')
            ax[0, iax].plot(oss_results['col_centroid'] - 1 + stamp.col_corner_stamp, 
                            oss_results['row_centroid'] - 1 + stamp.row_corner_stamp,
                            'cx',lw=3, ms=6)
        ax[1, 0].fill(locate_box_col, locate_box_row, fill=False, color='cyan')
        ax[1, 0].plot(oss_results['col_centroid'] - 1 + stamp.col_corner_stamp, 
                            oss_results['row_centroid'] - 1 + stamp.row_corner_stamp,
                            'cx',lw=3, ms=6)
        osf_centroid_text = str(
             "oss cen. col, row, flux: {:.3f}, {:.3f}, {:.1f}\n".format(oss_results['col_centroid'], 
                                                                    oss_results['row_centroid'], 
                                                                    oss_results['centroid_flux'])
              + "\n")
    else:
        osf_centroid_text = ''
    
    ax[1, 2].axis('off')
    report_string = str("Postage Stamp {} Input Parameters\n".format(stamp.refstar_no)
          + "v2, v3 desired; {:+.5f}, {:+.5f}\n".format(stamp.v2_desired, stamp.v3_desired)
          + "NRS{:1d} col , row corner; {}, {}\n".format(stamp.detector, 
                                                     stamp.col_corner_stamp,
                                                     stamp.row_corner_stamp)
          + "GWA X, Y tilt; {:.5f}, {:.5f}\n".format(stamp.gwa_x_tilt, stamp.gwa_y_tilt)
          + "\n"
          + "Gentalocate Results\n"
          + "background measured {:.3f}\n".format(stamp.bkg_measured)
          + "locate col, row, flux: {:2d}, {:2d}, {:.1f}\n".format(stamp.col_locate_onebase, 
                                                                   stamp.row_locate_onebase, 
                                                                   stamp.checkbox_flux)
          + "centroid col, row, flux: {:.3f}, {:.3f}, {:.1f}\n".format(stamp.col_center_onebase, 
                                                                    stamp.row_center_onebase, 
                                                                    stamp.centroid_flux)
          + osf_centroid_text
          + "detector col, row: {:.5f}, {:.5f}\n".format(stamp.col_detector_center, 
                                                                    stamp.row_detector_center, 
                                                                    stamp.centroid_flux)
          + "Centroid success: {}\n".format(stamp.centroid_success)
          + "\n"
          + "TA Transform Results\n"
          + "V2, V3 Measured: {:.5f}, {:.5f}\n".format(stamp.v2_measured, stamp.v3_measured)
          + "Expected SIAF DET y, x: {:.5f}, {:.5f}\n".format(stamp.y_siaf_expected, 
                                                              stamp.x_siaf_expected)
               )
    ax[1, 2].text(0.0, 0.0, report_string, fontsize=12)            

    fig.tight_layout()
    return(fig, ax, report_string)

def stamp_subplot(stamp, fieldname, fig, ax, lower_percentile=25, upper_percentile=99.5, 
              vmin=None, vmax=None, cmap=None):
    '''Plots image in fieldname to pyplot axes ax, including colorbar
    inputs:
      fieldname - field name of image to be plotted
      fix, ax - pyplot figure and axes objects to be drawn to
      Options to scale image range either by percentiles or fixed values. 
      If both specified, the fixed values take precendence 

      Images are plotted in the one-based coordinates of the full frame image, 
      assuming fitswriter image orientation.
    '''       
    
    if cmap is None:
        cmap = 'Wistia_r'
    row_size, col_size = np.shape(stamp[fieldname])
    if(vmin is None):
        vmin = np.percentile(stamp[fieldname], lower_percentile)
    if(vmax is None):
        vmax = np.percentile(stamp[fieldname], upper_percentile)
    col_lft = stamp['col_corner_stamp'] - 0.5
    col_rgt = stamp['col_corner_stamp'] + col_size - 0.5
    row_bot = stamp['row_corner_stamp'] - 0.5
    row_top = stamp['row_corner_stamp'] + row_size - 0.5
    
    imdivider = make_axes_locatable(ax)
    cbax = imdivider.append_axes('right', size='5%', pad="2%")

    implot = ax.imshow(stamp[fieldname], extent=(col_lft, col_rgt, row_bot, row_top) ,origin = 'lower',
                                       cmap=cmap, interpolation='Nearest', vmin=vmin, vmax=vmax)
    ax.set_title(fieldname)
    ax.set_xlabel('Col = SIAF Det Y')
    ax.set_ylabel('Row = SIAF Det X')
    fig.colorbar(implot, cax=cbax)