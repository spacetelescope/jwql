#! /usr/bin/env python

"""This module contains code for the cosmic ray monitor, which currently checks
the number and magnitude of jumps in all observations performed with MIRI.

The code first checks MAST for any new MIRI observations that have not yet been
run through the monitor. It then copies those files to a working directory,
where they are run through the pipeline, and for which the output is stored
in a new directory for each observation.

Each observation is then analyzed for jumps due to cosmic rays, of which the number
and magnitude are recorded. This information is then inserted into the
"MiriCosmicRayStats" database table.


Author
------

    -Mike Engesser

Use
---

    This module can be used from the command line as such:

    ::

        python cosmic_ray_monitor.py
"""


# Functions for logging
import logging
from jwql.utils.logging_functions import configure_logging
from jwql.utils.logging_functions import log_info
from jwql.utils.logging_functions import log_fail

# Funtions for database interaction
from jwql.jwql_monitors import monitor_mast
from jwql.utils.constants import JWST_DATAPRODUCTS

from jwql.database.database_interface import session
from jwql.database.database_interface import MIRICosmicRayQueryHistory
from jwql.database.database_interface import MIRICosmicRayStats
from sqlalchemy import func
from sqlalchemy.sql.expression import and_

# Functions for file manipulation
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config

# Astropy functions
from astropy.io import fits
from astropy.time import Time

# Utility functions
from jwql.instrument_monitors import pipeline_tools
import os
import numpy as np
import shutil
import julian
import datetime

@log_fail
@log_info
def cosmic_ray_monitor():
    """ 
    The main function of the ``monitor_template`` module.
    Queries MAST for new MIRI data and copies it to a working 
    directory where it is run through the JWST pipeline. The output of the 'jump'
    and 'rate' steps is used to determine the number and magnitudes of cosmic rays
    which is then saved to the database.
    """
    
    logging.info('Begin logging for cosmic_ray_monitor')

    aperture = 'MIRIM_FULL'
    query_table = MIRICosmicRayQueryHistory
    stats_table = MIRICosmicRayStats
    
    #We start by querying MAST for new data
    start_date = most_recent_search(aperture, query_table)
    end_date = Time.now().mjd
    logging.info('\tMost recent query: {}'.format(start_date))
    
    new_entries = query_mast(start_date, end_date)
    
    #for testing purposes only
    new_filenames = get_config()['local_test_data']

    #for file_entry in new_entries['data']:
    #    try:
    #        new_filenames.append(filesystem_path(file_entry['filename']))
    #    except FileNotFoundError:
    #        logging.info('\t{} not found in target directory'.format(file_entry['filename']))
    #    except ValueError:
    #        logging.info(
    #            '\tProvided file {} does not follow JWST naming conventions.'.format(file_entry['filename']))
     
    #Next we copy new files to the working directory
    output_dir = os.path.join(get_config()['outputs'], 'cosmic_ray_monitor')

    data_dir = get_config()['local_test_dir'] #for testing purposes only
    #data_dir =  os.path.join(output_dir,'data')

    ensure_dir_exists(data_dir)
    cosmic_ray_files, not_copied = copy_files(new_filenames, data_dir)
    
    for file_name in cosmic_ray_files:
        if 'uncal' in file_name:
            dir_name = file_name[51:76] #Gets the observation identifier. Should be constant?
            obs_dir = os.path.join(data_dir, dir_name)
            ensure_dir_exists(obs_dir)

            head = fits.getheader(file_name)
            nints = head['NINTS']

            try:
                shutil.copy2(file_name, obs_dir)
            except:
                logging.info('Failed to copy {} to observation dir.'.format(file_name))
            
            #Next we run the pipeline on the files to get the proper outputs
            MIRI_steps = pipeline_tools.get_pipeline_steps('MIRI')
                            
            file = os.path.join(obs_dir, os.path.basename(file_name))

            completed_steps = pipeline_tools.completed_pipeline_steps(file)
            steps = pipeline_tools.steps_to_run(MIRI_steps,completed_steps)
            
            try:
                pipeline_tools.calwebb_detector1_save_jump(file, obs_dir, ramp_fit=True, save_fitopt=False)
            except:
                logging.info('Failed to complete pipeline steps on {}.'.format(file))


            #Next we analyze the cosmic rays in the new data
            for output_file in os.listdir(obs_dir):
                
                if 'jump' in output_file:
                    jump_file = os.path.join(obs_dir,output_file)

                if 'rateint' in output_file:
                    rate_file = os.path.join(obs_dir,output_file)

                if nints == 1:
                    if '0_ramp_fit' in output_file:
                        rate_file = os.path.join(obs_dir, output_file)

                elif nints > 1:
                    if '1_ramp_fit' in output_file:
                        rate_file = os.path.join(obs_dir,output_file)

            try:
                jump_head, jump_data, jump_dq = get_jump_data(jump_file)
            except:
                logging.info('Could not open jump file: {}'.format(jump_file))

            try:
                rate_data = get_rate_data(rate_file)
            except:
                logging.info('Could not open rate file: {}'.format(rate_file))


            jump_locs = get_jump_locs(jump_dq,nints)
            jump_locs_pre = group_before(jump_locs,nints)

            eff_time = jump_head['EFFEXPTM']

            # Get observation time info
            obs_start_time = jump_head['EXPSTART']
            obs_end_time = jump_head['EXPEND']
            start_time = julian.from_jd(obs_start_time, fmt='mjd')
            end_time = julian.from_jd(obs_end_time, fmt='mjd')

            cosmic_ray_num = len(jump_locs)
            #cosmic_ray_rate = get_cr_rate(jump_locs, eff_time)
            cosmic_ray_mags = get_cr_mags(jump_locs, jump_locs_pre, rate_data, jump_data, jump_head, nints)

            # Insert new data into database
            try:
                cosmic_ray_db_entry = {'entry_date': datetime.datetime.now(),
                                       'aperture': aperture,
                                       'source_file': file_name,
                                       'obs_start_time': start_time,
                                       'obs_end_time': end_time,
                                       'jump_count': cosmic_ray_num,
                                       'magnitude': cosmic_ray_mags
                                       }
                stats_table.__table__.insert().execute(cosmic_ray_db_entry)

                logging.info("Successfully inserted into database. \n")
            except:
                logging.info("Could not insert entry into database. \n")
                
def get_cr_mags(jump_locs, jump_locs_pre, rateints, jump_data, jump_head, nints):
    """
    Computes a list of magnitudes using the coordinate of the detected jump compared to 
    the magnitude of the same pixel in the group prior to the jump. 
    
    Parameters:
    ----------
    
    jump_locs: list
        List of coordinates to a pixel marked with a jump.
        
    jump_locs_pre: list
        List of matching coordinates one group before jump_locs.
        
    head: FITS header
        Header containing file information.
        
    rateints: ndarray
        Array in DN/s. 
        
    Returns:
    -------
    
    mags: list
        A list of cosmic ray magnitudes corresponding to each jump. 

    """
    
    mags = []
    for coord, coord_gb in zip(jump_locs, jump_locs_pre):
        mags.append(magnitude(coord, coord_gb, rateints, jump_data, jump_head, nints))

    return mags 

def get_cr_rate(jump_locs, t):
    """
    Computes the rate of cosmic ray impacts in a given time.
    
    Parameters:
    ----------
    jump_locs: list
        List of coordinates to a pixel marked with a jump.
        
    t: int or float
        Time over which to compute the rate. 
        Nominally the effective exposure time.
    
    """
    
    return len(jump_locs)/t
                
def get_jump_data(jump_filename):
    """
    Opens and reads a given .FITS file containing cosmic rays.
    
    Parameters:
    ----------
    jump_filename: str
        Path to file.
        
    Returns:
    -------
    head: FITS header
        Header containing file information
    
    data: NoneType
        FITS data
    
    dq: ndarray
        Data Quality array containing jump flags.
        
    """
    
    hdu = fits.open(jump_filename)
    
    head = hdu[0].header
    data = hdu[1].data
    
    dq = hdu[3].data
    
    hdu.close()
    
    return head, data, dq  

def get_jump_locs(dq,nints):
    """
    Uses the data quality array to find the location of all jumps in the data.
    
    Parameters:
    ----------
    dq: ndarray
        Data Quality array containing jump flags.
        
    Returns:
    -------
    jump_locs: list
        List of coordinates to a pixel marked with a jump.
    """
    
    temp = np.where(dq==4)
    
    jump_locs = []

    if nints > 1:
        for i in range(len(temp[0])):
            jump_locs.append((temp[0][i],temp[1][i],temp[2][i],temp[3][i]))
    else:
        for i in range(len(temp[0])):
            jump_locs.append((temp[0][i],temp[1][i],temp[2][i]))
        
    return jump_locs

def get_rate_data(rate_filename):
    """
    Opens and reads a given .FITS file.
    
    Parameters:
    ----------
    rate_filename: str
        Path to file.
        
    Returns:
    -------
    data: NoneType
        FITS data
    """
    
    data = fits.getdata(rate_filename)
    
    return data

def group_before(jump_locs, nints):
    """
    Creates a list of coordinates one group before given jump coordinates.

    Parameters:
    ----------
    jump_locs: list
        List of coordinates to a pixel marked with a jump.

    Returns:
    -------
    jump_locs_pre: list
        List of matching coordinates one group before jump_locs.

    """
    jump_locs_pre = []

    if nints > 1:
        for coord in jump_locs:
            jump_locs_pre.append((coord[0], coord[1] - 1, coord[2], coord[3]))
    else:
        for coord in jump_locs:
            jump_locs_pre.append((coord[0] - 1, coord[1], coord[2]))

    return jump_locs_pre

def magnitude(coord, coord_gb, rateints, data, head, nints):
    """
    Calculates the magnitude of a list of jumps given their coordinates
    in an array of pixels.
    
    Parameters:
    ----------
    coord: tuple
        Coordinate of jump.
    
    coord_gb: tuple
        Coordinate of jump pixel one group before.
    
    head: FITS header
        Header containing file information.
        
    rateints: ndarray
        Array in DN/s. 
        
    Returns:
    -------
    cr_mag: 
    
    """

    grouptime = head['TGROUP']

    if nints == 1:
        rate = rateints[coord[-2]][coord[-1]]
        cr_mag = data[0][coord[0]][coord[1]][coord[2]] \
                 - data[0][coord_gb[0]][coord_gb[1]][coord_gb[2]] \
                 - rate * grouptime
    else:
        rate = rateints[coord[0]][coord[-2]][coord[-1]]
        cr_mag = data[coord] - data[coord_gb] - rate * grouptime

    return cr_mag

def most_recent_search(aperture, query_table):
    """Adapted from Dark Monitor (Bryan Hilbert)
    
    Query the query history database and return the information
    on the most recent query for the given ``aperture_name`` where
    the cosmic ray monitor was executed.
    
    Returns:
    -------
    query_result : float
        Date (in MJD) of the ending range of the previous MAST query
        where the cosmic ray monitor was run.
    """
    
    sub_query = session.query(query_table.aperture,
                              func.max(query_table.end_time_mjd).label('maxdate')
                              ).group_by(query_table.aperture).subquery('t2')

    # Note that "self.query_table.run_monitor == True" below is
    # intentional. Switching = to "is" results in an error in the query.
    query = session.query(query_table).join(
        sub_query,
        and_(
            query_table.aperture == aperture,
            query_table.end_time_mjd == sub_query.c.maxdate,
            query_table.run_monitor == True
        )
    ).all()

    query_count = len(query)
    if query_count == 0:
        query_result = 57357.0  # a.k.a. Dec 1, 2015 == CV3
        logging.info(('\tNo query history for {}. Beginning search date will be set to {}.'
                     .format(aperture, query_result)))
    elif query_count > 1:
        raise ValueError('More than one "most recent" query?')
    else:
        query_result = query[0].end_time_mjd

    return query_result

def query_mast(start_date, end_date):
    """
    Use astroquery to search MAST for cosmic ray data
    
    Parameters:
    ----------
    start_date : float
        Starting date for the search in MJD
    end_date : float
        Ending date for the search in MJD
    
    Returns
    -------
    result : list
        List of dictionaries containing the query results
    
    """
    
    instrument = 'MIRI'
    dataproduct = JWST_DATAPRODUCTS
    parameters = {"date_obs_mjd": {"min": start_date, "max": end_date}}

    result = monitor_mast.instrument_inventory(instrument, dataproduct, 
                                               add_filters=parameters, 
                                               return_data=True)
    
    return result


if __name__ == '__main__':

    # Configure logging
    module = os.path.basename(__file__).strip('.py')
    configure_logging(module)

    # Call the main function
    cosmic_ray_monitor()
