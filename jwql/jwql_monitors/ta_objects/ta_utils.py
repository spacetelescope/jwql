#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  3 10:48:05 2019

@author: gkanarek, cproffitt
"""

import configparser # https://docs.python.org/3.5/library/configparser.html
import sys, re, os
import lxml.etree as ET
import astropy.io.fits as fits
import numpy as np
from astropy.table import Table


from ta_objects import PostageStamp

code_path = os.path.dirname(os.path.abspath(__file__))
aux_data_path = os.path.join(code_path, 'aux_data')

"""Can possibly use these if we need all of data that Tony uses; otherwise, just going to replicate what Charles grabs.

class TAObservation(object):
    obs_id = ''
    visit_id = ''
    ta_type = ''
    readout_mode = ''
    ta_filter = ''
    subarray = ''
    exptime = 0.
    phottime = 0.
    crmethod = ''
    conv_thresh = 0.
    bkgmethod = ''
    cbox_ncol = 0
    cbox_nrow = 0
    refstars = []
    v2_offset = 0.
    v3_offset = 0.
    v2_sigma = 0.
    v3_sigma = 0.
    roll_offset = 0.
    idl_x_offset = 0.
    idl_y_offset = 0.
    idl_r_offset = 0.
    fgs_x_offset = 0.
    fgs_y_offset = 0.
    fgs_r_offset = 0.
    niter = 0
    fit_fraction = (0, 0)

class TARefstar(object):
    exp_num = 0
    detector = ''
    status = ''
    niter = 0
    counts = 0
    v2_meas = 0.
    v3_meas = 0.
    rejection = ''
    col_ctr = 0.
    row_ctr = 0.
    PScol = 0.
    PSrow = 0.
    diff_col = 0.
    diff_row = 0.
    peak_col = 0.
    peak_row = 0.
    peak_cts = 0.
    bkg_cts = 0."""
    

def parse_osf_xml(osf_xml_file):
    root = ET.parse(osf_xml_file)
    
    #for now we're using charles's list of information, with just a couple additions
    
    osf_dict_template = {'obs_id': '',
                 'star_num': '',                          #8217:
                 'background_measured': -1.0,                     #8215:
                 'locate_flux': 0.0,                              #8213:
                 'col_locate': -1, 'row_locate': -1,              #8244:
                 'centroid_flux': 0.0, 'centroid_iter': 0,        #8211:
                 'col_diff': 0.0, 'row_diff': 0.0 ,               #8212:
                 'col_centroid': -1.0, 'row_centroid': -1.0,      #8214:
                 'convergence_flag': ''                           #8224:
                 }
    
    all_ta_stars = []
    
    for obs_id in set([child.text for child in root.findall(".//*[TARGET_ACQ]/OBSERVATION_ID")]): #iterate over all unique observation IDs for TA exposures
        exposures = root.xpath("./*[TARGET_ACQ and ./OBSERVATION_ID/text()='{}']".format(obs_id)) #all TA exposures for the given obs_id
        for exposure in exposures:
            ta_stars = root.findall(".//*[TARGET_LOCATE_SUMMARY]")
            for star in ta_stars:
                
        
    
    
    
    return osf_results

def extract_osf_genta(osf_logfile):
    '''Extract results of GENTALOCATE from OSF log for all reference stars
       Input:
          osf_logfile - name of text file containing the OSF log covering a pair of 
                        dithered MSA TA exposures 
        output:
          list of dictionaries of desired quantities from the OSF log.
          A new dictionary is added to the list when the "8217:" message is encountered,
          which starts the "Target Locate" section for a new reference star.
          Entry is then populated by extracting quantities from subsequent messages.
          The structure of each dictionary in the output list is as follows: 
                {'star_num': str,                                  #8217:
                 'background_measured': float,                     #8215:
                 'locate_flux': float                              #8213:
                 'col_locate': int, 'row_locate': int,             #8244:
                 'centroid_flux': float, 'centroid_iter': int,     #8211:
                 'col_diff': float, 'row_diff': float ,            #8212:
                 'col_centroid': float, 'row_centroid': float,     #8214:
                 'convergence_flag': str                           #8224:
                 }
        '''

    # this code breaks if a log entry is split over two lines!
    # this happens occaisionally for 8212, so we've added code to handle that case
    # probably should pre-screen to merge continuation lines
    # should also write a function to handle the parsing of values more uniformly

    # comment on right is spevmsg number in OSF log line in which these values are found    
    osf_dict_template = {'star_num': '',                          #8217:
                 'background_measured': -1.0,                     #8215:
                 'locate_flux': 0.0,                              #8213:
                 'col_locate': -1, 'row_locate': -1,              #8244:
                 'centroid_flux': 0.0, 'centroid_iter': 0,        #8211:
                 'col_diff': 0.0, 'row_diff': 0.0 ,               #8212:
                 'col_centroid': -1.0, 'row_centroid': -1.0,      #8214:
                 'convergence_flag': ''                           #8224:
                 }

    osf_results = []
    with open(osf_logfile, 'r') as f:
        for line in f.readlines():  
              if(((line.find('8217:') > -1) | (line.find('FSW 8217') > -1)) ):
                  istar = len(osf_results)
                  osf_results.append(osf_dict_template.copy())
                  osf_results[istar]['star_num'] = str(istar+1)
              elif(((line.find('8215:') > -1) | (line.find('FSW 8215') > -1)) ):
                  bkm, background_measured = line[line.find('=') + 1 : ].replace('(','').replace(')','').split()
                  osf_results[istar]['background_measured'] = eval(background_measured)
              elif(((line.find('8213:') > -1) | (line.find('FSW 8213') >-1)) ):
                  osf_results[istar]['locate_flux'] = eval(line[line.find('=') + 1 : ])
              elif(((line.find('8244:') > -1) | (line.find('FSW 8244') >-1)) ):
                  col_locate, row_locate = eval(line[line.find('=') + 1 : ])
                  osf_results[istar]['col_locate'] = col_locate
                  osf_results[istar]['row_locate'] = row_locate  
              elif(((line.find('8211:') > -1) | (line.find('FSW 8211') >-1)) ):
                  centroid_flux, centroid_iter = eval(line[line.find('=') + 1 : ])
                  osf_results[istar]['centroid_flux'] = centroid_flux
                  osf_results[istar]['centroid_iter'] = centroid_iter
              elif(((line.find('8212:') > -1) | (line.find('FSW 8212') >-1)) ):
                 if(line.rstrip()[-1] != ')' ):
                     line = line + ')'
                 if(line.find('(')> -1 ):   # skip any continuation lines for 8212 
                    col_diff, row_diff = eval(line[line.find('=') + 1 : ])
                    osf_results[istar]['col_diff'] = col_diff
                    osf_results[istar]['row_diff'] = row_diff
              elif(((line.find('8214:') > -1) | ( line.find('FSW 8214')>-1)) ):
                  col_centroid, row_centroid = eval(line[line.find('=') + 1 : ])
                  osf_results[istar]['col_centroid'] = col_centroid
                  osf_results[istar]['row_centroid'] = row_centroid
              elif(((line.find('8224:') > -1) | (line.find('FSW 8224') > -1)) ):
                  conflag = line[line.find('=') + 1 : ].replace('(','').replace(')','').split(',')
                  osf_results[istar]['convergence_flag'] = conflag[0].strip()
                  
    return(osf_results)


def get_nrsta_stamps(activity_file):
    ''' Parse NRSTAMAIN activity from visit file to extract stamp parameters
    inputs
      activity_file - text file with activity line for single NRSTAMAIN activity
    output
      list of dictionaries for each reference star specified in the TA activity 
            {'v2_desired': float, 
             'v3_desired': float, 
             'detector': int, 
             'row_corner_stamp': in,    
             'col_corner_stamp': int,
             'refstar_no': str
    ''' 

    # strategy is toread NRSTAMAIN activity in as a string, removing line breaks,
    # search for the first occurence of the string "REFSTAR", 
    # use the next 5 numbers (between [ ]) to create the desired dictionary,
    # append that to the list of dictionaries,
    # remove the part of the string we just used, and keep searcing for [ ] pairs
    # until there are no more reference stars to process

    with open(activity_file, 'r') as f:
          activity_string = f.read().replace('\n', '')

    stamp_param_dict_list = []
    activity_string = activity_string[activity_string.find('REFSTAR'): ]
    refstar_no = 0
    while activity_string.find('REFSTAR') >= 0:
        refstar_no += 1
        alist = activity_string[
            activity_string.find('[') + 1: activity_string.find(']')].split(',')
        stamp_param_dict_list.append(
            {'v2_desired': float(alist[0]), 
             'v3_desired': float(alist[1]), 
             'detector': int(alist[2]), 
             'row_corner_stamp': int(alist[3]),    
             'col_corner_stamp': int(alist[4]),
             'refstar_no': str(refstar_no)
            } )
        activity_string = activity_string[activity_string.find(']') + 1 :]
    return(stamp_param_dict_list)

def get_ta_data_cube(filename, return_expo_params = True):
    '''get 3 group data cube for NIRSpec TA observation
    For now assume that the data is in the primary header in fitswriter format,
    but eventually need to cover other cases including DMS format,
    and then perform any needed axis flips or rotations
    
    Also should add option to deal with multi ramp files for testing using multi-ramp darks
    (will need keyword to indicate which ramp the 3 groups should be taken from)
    
    Also consider option to average 12 groups of NRSRAPID data to fake an NRS TA
        
    '''
    
    hdulist = fits.open(filename)
    data_cube = hdulist['Primary'].data
    data_cube = data_cube[0:3, :, :]
    if return_expo_params:
        data_header = hdulist['Primary'].header
        hdulist.close()
        exposure_params = {'gwa_x_tilt': float(data_header['GWA_XTIL']), 
                 'gwa_y_tilt': float(data_header['GWA_YTIL']),
                 'col_start': int(data_header['COLCORNR']),
                 'row_start': int(data_header['ROWCORNR']), 
                 'tgroup': data_header['TGROUP'],
                 'filter_name': data_header['FWA_POS']}
        return(data_cube, exposure_params)
    else:
        hdulist.close()
        return(data_cube)
        
def get_ta_flat_image(filename, bigendian = None):
    '''Import a NRS TA flat image either in fits format, or in big or little endian format.

       required inputs:
           filename - name of file containing flat image. If name ends in ".fits" it is assumed to be a fits file, 
                      otherwise it is assumed to be a binary file of 1024*2048 uint16 bytes.  If a binary file name 
                      ends in "big" the input is assumed to use big endian byte ordering, otherwise "little" is assumed
       keyword inputs:
           bigendian - if set to True, forces a binary file to treated as big endian even if the name does not end in
                       'big'. Has no effect on fits files or if value set to anything other than True.
       outputs:
           flat_image - a 1024 x 2048 numpy uint16 array.
    '''

    if(filename[-5:] == '.fits'):
        hdulist = fits.open(filename)
        flat_image = hdulist['PRIMARY'].data
        hdulist.close()
    else:
        flat_bytes = np.fromfile(filename, dtype='uint16')
        if((filename[-3:] == 'big') or bigendian):
            byteorder = 'big'
        else:
            byteorder = 'little'
        if(byteorder != sys.byteorder):
            flat_bytes = flat_bytes.byteswap()
        flat_image = np.reshape(flat_bytes, (1024, 2048))
        
    return(flat_image)
    
def mk_ta_params(configfile, extra_dict=None):

    '''Extract desired sections from config file into dictionary, converting       
    ints and floats as appropriate 
    '''
    taconfig = configparser.ConfigParser()
    taconfig.read(configfile)  

    sections = ['GENTALOCATE','TA_TRANSFORM']
    
    ta_params_dict = {}
    for section_name in sections:
        section = taconfig[section_name]
        for key in section:
            if section[key].isdigit():
                ta_params_dict[key] = int(section[key])
            elif re.match("^\d+?\.\d+?$", section[key]) is not None:
                ta_params_dict[key] = float(section[key])
            else:
                ta_params_dict[key] = section[key]
                
    if extra_dict:
        ta_params_dict.update(extra_dict)
    
    return(ta_params_dict)

def mk_stamp_list(stamp_param_list, image_nrs1_name=None, image_nrs2_name=None, 
                  flat1_file=None, flat2_file=None, ta_config_file=None,
                  gwa_tilt=None):
    '''Make a list of postage stamp objects for a pair of NIRSpec MSATA observations.
    Note that to cover both dither positions, it will be necessary to call this routine twice!
    inputs:
      stamp_param_list - list of stamp parameter dictionaries
      image_nrs1_name - name of fits file with NRS1 TA image
      image_nrs2_name - name of fits file with NRS2 TA image
     optional keyword inputs:
      flat1_file - TA flat/bad pixel mask for NRS1 - if None will use default file from ta_config_file
      flat2_file - TA flat/bad pixel mask for NRS2 - if None will use default file from ta_config_file
      ta_config - configurationfile with TA parameters - if =None, will use hardwired default
    output:
      list of PostageStamp objects
    '''
    
    if(ta_config_file is None):
        ta_config_file = os.path.join(aux_data_path, 'ta_parameters_new.ini')
    ta_params = mk_ta_params(ta_config_file)

    if image_nrs1_name is not None:
        data_cube1, exposure1_params = get_ta_data_cube(image_nrs1_name)
        if(flat1_file is None):
            flat1 = get_ta_flat_image(os.path.join(aux_data_path, 'nrs_taflat_otis1_2018_08_23_NRS1_big'))
            # should really get default flat name from the config file!!!
        else:
            flat1 = get_ta_flat_image(flat1_file)

    if image_nrs2_name is not None:
        data_cube2, exposure2_params = get_ta_data_cube(image_nrs2_name)
        if(flat2_file is None):
            flat2 = get_ta_flat_image(os.path.join(aux_data_path, 'nrs_taflat_otis1_2018_08_23_NRS2_big'))
        else:
            flat2 = get_ta_flat_image(flat2_file)

    # override of tilt values taken from image headers
    if(gwa_tilt is not None):
            exposure1_params['gwa_x_tilt'] = exposure2_params['gwa_x_tilt'] = gwa_tilt[0]
            exposure1_params['gwa_y_tilt'] = exposure2_params['gwa_y_tilt'] = gwa_tilt[1]

    #now make the list of postage stamps with gentalocate and ta transform calculations
    stamp_list = []
    for stamp_param in stamp_param_list:
        if stamp_param['detector'] == 1 :
            stamp_list.append(PostageStamp(data_cube1, flat1, stamp_param, exposure1_params, ta_params))
        else:
            stamp_list.append(PostageStamp(data_cube2, flat2, stamp_param, exposure2_params, ta_params))
    return(stamp_list) 

def write_stamp_list(stamp_list, output_filename, overwrite=False):
    table_out = Table([stamp.table_output for stamp in stamp_list])
    table_out.write(output_filename, format='fits', overwrite=overwrite)
