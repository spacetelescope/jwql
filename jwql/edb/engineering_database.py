#! /usr/bin/env python

"""Module for dealing with JWST DMS Engineering Database mnemonics.

This module provides ``jwql`` with convenience classes and functions
to retrieve and manipulate mnemonics from the JWST DMS EDB. It uses
the ``engdb_tools`` module of the ``jwst`` package to interface the
EDB directly.

Authors
-------

    - Johannes Sahlmann
    - Mees Fix
    - Bryan Hilbert

Use
---

    This module can be imported and used with

    ::

        from jwql.edb.engineering_database import get_mnemonic
        get_mnemonic(mnemonic_identifier, start_time, end_time)

    Required arguments:

    ``mnemonic_identifier`` - String representation of a mnemonic name.
    ``start_time`` - astropy.time.Time instance
    ``end_time`` - astropy.time.Time instance

Notes
-----
    There are two possibilities for MAST authentication:

    1. A valid MAST authentication token is present in the local
    ``jwql`` configuration file (config.json).
    2. The MAST_API_TOKEN environment variable is set to a valid
    MAST authentication token.

    When querying mnemonic values, the underlying MAST service returns
    data that include the datapoint preceding the requested start time
    and the datapoint that follows the requested end time.
"""
import calendar
from collections import OrderedDict
from datetime import datetime, timedelta
from numbers import Number
import os
import warnings

from astropy.io import ascii
from astropy.stats import sigma_clipped_stats
from astropy.table import Table
from astropy.time import Time
import astropy.units as u
from astroquery.mast import Mast
from bokeh.embed import components
from bokeh.layouts import column
from bokeh.models import BoxAnnotation, ColumnDataSource, DatetimeTickFormatter, HoverTool, Range1d
from bokeh.plotting import figure, output_file, show, save
import numpy as np

from jwst.lib.engdb_tools import ENGDB_Service
from jwql.utils.constants import MIRI_POS_RATIO_VALUES
from jwql.utils.credentials import get_mast_base_url, get_mast_token
from jwql.utils.utils import get_config

MAST_EDB_MNEMONIC_SERVICE = 'Mast.JwstEdb.Mnemonics'
MAST_EDB_DICTIONARY_SERVICE = 'Mast.JwstEdb.Dictionary'

# Temporary until JWST operations: switch to test string for MAST request URL
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')
if not ON_GITHUB_ACTIONS:
    Mast._portal_api_connection.MAST_REQUEST_URL = get_config()['mast_request_url']


class EdbMnemonic:
    """Class to hold and manipulate results of DMS EngDB queries."""
    def __add__(self, mnem):
        """Allow EdbMnemonic instances to be added (i.e. combine their data).
        info and metadata will not be touched. Data will be updated. Duplicate
        rows due to overlapping dates will be removed. The overlap is assumed to
        be limited to a single section of the end of once EdbMnemonic instance and
        the beginning of the other instance. Either one of the two instances to be
        added can contain the earlier dates. The function will check the starting
        date of each instance and treat the earlier starting date as the instance
        that is first. Blocks will be updated to account for removed duplicate rows.

        Parameters
        ----------
        mnem : jwql.edb.engineering_database.EdbMnemonic
            Instance to be added to the current instance

        Returns
        -------
        new_obj : jwql.edb.engineering_database.EdbMnemonic
            Summed instance
        """
        # Do not combine two instances of different mnemonics
        if self.mnemonic_identifier != mnem.mnemonic_identifier:
            raise ValueError((f'Unable to concatenate EdbMnemonic instances for {self.info["tlmMnemonic"]} '
                              'and {mnem.info["tlmMnemonic"]}.'))

        # Case where one instance has an empty data table
        if len(self.data["dates"]) == 0:
            return mnem
        if len(mnem.data["dates"]) == 0:
            return self

        if np.min(self.data["dates"]) < np.min(mnem.data["dates"]):
            early_dates = self.data["dates"].data
            late_dates = mnem.data["dates"].data
            early_data = self.data["euvalues"].data
            late_data = mnem.data["euvalues"].data
            early_blocks = self.blocks
            late_blocks = mnem.blocks
        else:
            early_dates = mnem.data["dates"].data
            late_dates = self.data["dates"].data
            early_data = mnem.data["euvalues"].data
            late_data = self.data["euvalues"].data
            early_blocks = mnem.blocks
            late_blocks = self.blocks

        # Remove any duplicates, based on the dates entries
        # Keep track of the indexes of the removed rows, so that any blocks
        # information can be updated
        all_dates = np.append(early_dates, late_dates)
        unique_dates, unq_idx = np.unique(all_dates, return_index=True)

        # Combine the data and keep only unique elements
        all_data = np.append(early_data, late_data)
        unique_data = all_data[unq_idx]

        # This assumes that if there is overlap between the two date arrays, that
        # the overlap all occurs in a single continuous block at the beginning of
        # the later set of dates. It will not do the right thing if you ask it to
        # (e.g.) interleave two sets of dates.
        overlap_len = len(unique_dates) - len(all_dates)

        # Shift the block values for the later instance to account for any removed
        # duplicate rows
        if late_blocks[0] is not None:
            new_late_blocks = late_blocks - overlap_len
            if early_blocks[0] is None:
                new_blocks = new_late_blocks
            else:
                new_blocks = np.append(early_blocks, new_late_blocks)
        else:
            if early_blocks[0] is not None:
                new_blocks = early_blocks
            else:
                new_blocks = [None]

        new_data = Table([unique_dates, unique_data], names=('dates', 'euvalues'))
        new_obj = EdbMnemonic(self.mnemonic_identifier, self.data_start_time, self.data_end_time,
                              new_data, self.meta, self.info, blocks=new_blocks)

        if self.mean_time_block is not None:
            new_obj.mean_time_block = self.mean_time_block
        elif mnem.mean_time_block is not None:
            new_obj.mean_time_block = mnem.mean_time_block
        else:
            new_obj.mean_time_block = None

        # Combine any existing mean, median, min, max data, removing overlaps
        # All of these are populated in concert with median_times, so we can
        # use that to look for overlap values
        all_median_times = np.array(list(self.median_times) + list(mnem.median_times))
        srt = np.argsort(all_median_times)
        comb_median_times = all_median_times[srt]
        unique_median_times, idx_median_times = np.unique(comb_median_times, return_index=True)

        new_obj.median_times = unique_median_times
        new_obj.mean = np.array(list(self.mean) + list(mnem.mean))[srt][idx_median_times]
        new_obj.median = np.array(list(self.median) + list(mnem.median))[srt][idx_median_times]
        new_obj.max = np.array(list(self.max) + list(mnem.max))[srt][idx_median_times]
        new_obj.min = np.array(list(self.min) + list(mnem.min))[srt][idx_median_times]

        return new_obj

    def __init__(self, mnemonic_identifier, start_time, end_time, data, meta, info, blocks=[None],
                 mean_time_block=None):
        """Populate attributes.

        Parameters
        ----------
        mnemonic_identifier : str
            Telemetry mnemonic identifier
        start_time : astropy.time.Time instance
            Start time
        end_time : astropy.time.Time instance
            End time
        data : astropy.table.Table
            Table representation of the returned data.
        meta : dict
            Additional information returned by the query
        info : dict
            Auxiliary information on the mnemonic (description,
            category, unit)
        blocks : list
            Index numbers corresponding to the beginning of separate blocks
            of data. This can be used to calculate separate statistics for
            each block.
        mean_time_block : astropy.units.quantity.Quantity
            Time period over which data are averaged
        """

        self.mnemonic_identifier = mnemonic_identifier
        self.requested_start_time = start_time
        self.requested_end_time = end_time
        self.data = data

        self.mean = []
        self.median = []
        self.stdev = []
        self.median_times = []
        self.min = []
        self.max = []
        self.mean_time_block = mean_time_block

        self.meta = meta
        self.info = info
        self.blocks = np.array(blocks)

        if len(self.data) == 0:
            self.data_start_time = None
            self.data_end_time = None
        else:
            self.data_start_time = np.min(self.data['dates'])
            self.data_end_time = np.max(self.data['dates'])
            if isinstance(self.data['euvalues'][0], Number) and 'TlmMnemonics' in self.meta:
                self.full_stats()

    def __len__(self):
        """Report the length of the data in the instance"""
        return len(self.data["dates"])

    def __mul__(self, mnem):
        """Allow EdbMnemonic instances to be multiplied (i.e. combine their data).
        info will be updated with new units if possible. Data will be updated.
        Blocks will not be updated, under the assumption that the times in self.data
        will all be kept, and therefore self.blocks will remain correct after
        multiplication.

        Parameters
        ----------
        mnem : jwql.edb.engineering_database.EdbMnemonic
            Instance to be multiplied into the current instance

        Returns
        -------
        new_obj : jwql.edb.engineering_database.EdbMnemonic
            New object where the data table is the product of those in the inputs
        """
        # If the data has only a single entry, we won't be able to interpolate, and therefore
        # we can't multiply it. Return an empty EDBMnemonic instance
        if len(mnem.data["dates"].data) < 2:
            mnem.data["dates"] = []
            mnem.data["euvalues"] = []
            return mnem

        # First, interpolate the data in mnem onto the same times as self.data
        mnem.interpolate(self.data["dates"].data)

        # Extrapolation will not be done, so make sure that we account for any elements
        # that were removed rather than extrapolated. Find all the dates for which
        # data exists in both instances.
        common_dates, self_idx, mnem_idx = np.intersect1d(self.data["dates"], mnem.data["dates"],
                                                          return_indices=True)

        # Adjust self.blocks based on the new dates. For each block, find the index of common_dates
        # that corresponds to its previous date, and use that index in the new blocks list. Note that
        # we will do this for self.blocks. mnem.blocks is ignored and will not factor in to the
        # new blocks list. We have to choose either self.blocks or mnem.blocks to keep, and it makes
        # more sense to keep with self.blocks since this is a method of self.data
        new_blocks = [0]
        for block in self.blocks:
            try:
                prev_date = self.data['dates'][block]
                before = np.where(common_dates == self.data['dates'][block])[0]

                if len(before) > 0:
                    new_blocks.append(before[0]) # + 1)
            except IndexError:
                # The final block value is usually equal to the length of the array, and will
                # therefore cause an Index Error in the lines above. Ignore that error here.
                # This way, if the final block is less than the length of the array, we can
                # still process it properly.
                pass

        # The last element of blocks should be the final element of the data
        if new_blocks[-1] != len(common_dates):
            new_blocks.append(len(common_dates))

        # Strip away any rows from the tables that are not common to both instances
        self_data = self.data[self_idx]
        mnem_data = mnem.data[mnem_idx]

        # Mulitply
        new_tab = Table()
        new_tab["dates"] = common_dates
        new_tab["euvalues"] = self_data["euvalues"] * mnem_data["euvalues"]

        new_obj = EdbMnemonic(self.mnemonic_identifier, self.requested_start_time, self.requested_end_time,
                              new_tab, self.meta, self.info, blocks=new_blocks)
        if self.mean_time_block is not None:
            new_obj.mean_time_block = self.mean_time_block
        elif mnem.mean_time_block is not None:
            new_obj.mean_time_block = mnem.mean_time_block
        else:
            new_obj.mean_time_block = None

        try:
            combined_unit = (u.Unit(self.info['unit']) * u.Unit(mnem.info['unit'])).compose()[0]
            new_obj.info['unit'] = f'{combined_unit}'
            new_obj.info['tlmMnemonic'] = f'{self.info["tlmMnemonic"]} * {mnem.info["tlmMnemonic"]}'
            new_obj.info['description'] = f'({self.info["description"]}) * ({mnem.info["description"]})'
        except KeyError:
            pass
        return new_obj

    def __str__(self):
        """Return string describing the instance."""
        return 'EdbMnemonic {} with {} records between {} and {}'.format(
            self.mnemonic_identifier, len(self.data), self.data_start_time,
            self.data_end_time)

    def block_stats(self, sigma=3, ignore_vals=[], ignore_edges=False, every_change=False):
        """Calculate stats for a mnemonic where we want a mean value for
        each block of good data, where blocks are separated by times where
        the data are ignored.

        Parameters
        ----------
        sigma : int
            Number of sigma to use for sigma clipping

        ignore_vals : list
            Any elements with values matching values in this list will be ignored

        ignore_edges : bool
            If True, the first and last elements of each block will be ignored. This
            is intended primarily for the MIRI ever_change data in IMIR_HK_xxx_POS_RATIO,
            where the position ratio values are not exactly synced up with the IMIR_HK_xxx_CUR_POS
            value. In that case, the first or last elements can have values from a time when
            the ratio has not yet settled to its final value.

        every_change : bool
            If True, the data are assumed to be every_change data. This is used when dealing with
            blocks that exclusively contain data to be ignored
        """
        means = []
        medians = []
        maxs = []
        mins = []
        stdevs = []
        medtimes = []
        remove_change_indexes = []
        if type(self.data["euvalues"].data[0]) not in [np.str_, str]:
            for i, index in enumerate(self.blocks[0:-1]):
                # Protect against repeated block indexes
                if index < self.blocks[i + 1]:
                    if self.meta['TlmMnemonics'][0]['AllPoints'] != 0:
                        block = self.data["euvalues"].data[index:self.blocks[i + 1]]

                        empty_block = False
                        uvals = np.unique(block)
                        if np.array_equal(np.array(sorted(ignore_vals)), uvals):
                            empty_block = True
                            meanval, medianval, stdevval, maxval, minval = np.nan, np.nan, np.nan, np.nan, np.nan

                            # If the block is composed entirely of data to be ignored, then we don't
                            # add new mean, median, max, min, stdev values, and we also need to remove
                            # the associated entry from self.every_change_values and self.blocks
                            # (only in the case of every_change data)
                            if every_change:
                                remove_change_indexes.append(i)

                        else:
                            # If there are values to be ignored, remove those from the array
                            # of elements. Keep track of whether the first and last are ignored.
                            ignore_first = False
                            ignore_last = False
                            for ignore_val in ignore_vals:
                                ignore_idx = np.where(block == ignore_val)
                                block = np.delete(block, ignore_idx)
                                if 0 in ignore_idx[0]:
                                    ignore_first = True
                                if len(block) - 1 in ignore_idx[0]:
                                    ignore_last = True

                            # If we want to ignore the first and last elements, do that here
                            if ignore_edges:
                                if len(block) > 3:
                                    if not ignore_last:
                                        block = block[0:-1]
                                    if not ignore_first:
                                        block = block[2:]

                            meanval, medianval, stdevval = sigma_clipped_stats(block, sigma=sigma)
                            maxval = np.max(block)
                            minval = np.min(block)
                    else:
                        meanval, medianval, stdevval, maxval, minval = change_only_stats(self.data["dates"].data[index:self.blocks[i + 1]],
                                                                                         self.data["euvalues"].data[index:self.blocks[i + 1]],
                                                                                         sigma=sigma)
                    if np.isfinite(meanval):
                        medtimes.append(calc_median_time(self.data["dates"].data[index:self.blocks[i + 1]]))
                        means.append(meanval)
                        medians.append(medianval)
                        maxs.append(maxval)
                        mins.append(minval)
                        stdevs.append(stdevval)
                    else:
                        pass

            # If there were blocks composed entirely of bad data, meaning no mean values were
            # calculated, remove those every change values and block values from the EdbMnemonic
            # instance.
            if every_change:
                if len(remove_change_indexes)  > 0:
                    self.every_change_values = np.delete(self.every_change_values, remove_change_indexes)
                    self.blocks = np.delete(self.blocks, remove_change_indexes)

        else:
            # If the data are strings, then set the mean to be the data value at the block index
            for i, index in enumerate(self.blocks[0:-1]):
                # Protect against repeated block indexes
                if index < self.blocks[i + 1]:
                    meanval = self.data["euvalues"].data[index]
                    medianval = meanval
                    stdevval = 0
                    medtimes.append(calc_median_time(self.data["dates"].data[index:self.blocks[i + 1]]))
                    means.append(meanval)
                    medians.append(medianval)
                    stdevs.append(stdevval)
                    maxs.append(meanval)
                    mins.append(meanval)
                    #if hasattr(self, 'every_change_values'):
                    #        updated_every_change_vals.append(self.every_change_values[i + 1])
        self.mean = means
        self.median = medians
        self.stdev = stdevs
        self.median_times = medtimes
        self.max = maxs
        self.min = mins

    def block_stats_filter_positions(self, sigma=5):
        """Calculate stats for a mnemonic where we want a mean value for
        each block of good data, where blocks are separated by times where
        the data are ignored. In this case, there are custom adjustments meant
        to work on the MIRI filter position mnemonics (e.g. IMIR_HK_GW14_POS_RATIO,
        IMIR_HK_FW_POS_RATIO).

        Parameters
        ----------
        sigma : int
            Number of sigma to use for sigma clipping
        """
        means = []
        medians = []
        maxs = []
        mins = []
        stdevs = []
        medtimes = []
        remove_change_indexes = []
        if type(self.data["euvalues"].data[0]) not in [np.str_, str]:
            for i, index in enumerate(self.blocks[0:-1]):
                # Protect against repeated block indexes
                if index < self.blocks[i + 1]:
                    if self.meta['TlmMnemonics'][0]['AllPoints'] != 0:
                        block = self.data["euvalues"].data[index:self.blocks[i + 1]]
                        filter_value = self.every_change_values[i]
                        pos_type = self.mnemonic_identifier.split('_')[2]
                        if pos_type not in MIRI_POS_RATIO_VALUES:
                            raise ValueError((f'Unrecognized filter position type: {pos_type} in {self.mnemonic_identifier}.'
                                              f'Expected one of {MIRI_POS_RATIO_VALUES.keys()}'))
                        if filter_value not in MIRI_POS_RATIO_VALUES[pos_type]:
                            raise ValueError((f'Unrecognized filter value: {filter_value} in block {i} of {self.mnemonic_identifier}'))

                        nominal_value, std_value = MIRI_POS_RATIO_VALUES[pos_type][filter_value]
                        max_value = nominal_value + sigma * std_value
                        min_value = nominal_value - sigma * std_value

                        empty_block = False
                        good = np.where((block <= max_value) & (block >= min_value))[0]
                        if len(good) == 0:
                            empty_block = True
                            meanval, medianval, stdevval, maxval, minval = np.nan, np.nan, np.nan, np.nan, np.nan

                            # If the block is composed entirely of data to be ignored, then we don't
                            # add new mean, median, max, min, stdev values, and we also need to remove
                            # the associated entry from self.every_change_values and self.blocks
                            # (only in the case of every_change data)
                            remove_change_indexes.append(i)

                        else:
                            # If there are values to be ignored, remove those from the array
                            # of elements. Keep track of whether the first and last are ignored.
                            block = block[good]
                            meanval, medianval, stdevval = sigma_clipped_stats(block, sigma=sigma)
                            maxval = np.max(block)
                            minval = np.min(block)

                    else:
                        meanval, medianval, stdevval, maxval, minval = change_only_stats(self.data["dates"].data[index:self.blocks[i + 1]],
                                                                                         self.data["euvalues"].data[index:self.blocks[i + 1]],
                                                                                         sigma=sigma)
                    if np.isfinite(meanval):
                        #this is preventing the nans above from being added. not sure what to do here.
                        #bokeh cannot deal with nans. but we need entries in order to have the blocks indexes
                        #remain correct. but maybe we dont care about the block indexes after averaging
                        medtimes.append(calc_median_time(self.data["dates"].data[index:self.blocks[i + 1]][good]))
                        means.append(meanval)
                        medians.append(medianval)
                        maxs.append(maxval)
                        mins.append(minval)
                        stdevs.append(stdevval)

            # If there were blocks composed entirely of bad data, meaning no mean values were
            # calculated, remove those every change values and block values from the EdbMnemonic
            # instance.
            if len(remove_change_indexes)  > 0:
                self.every_change_values = np.delete(self.every_change_values, remove_change_indexes)
                self.blocks = np.delete(self.blocks, remove_change_indexes)

        else:
            # If the data are strings, then set the mean to be the data value at the block index
            for i, index in enumerate(self.blocks[0:-1]):
                # Protect against repeated block indexes
                if index < self.blocks[i + 1]:
                    meanval = self.data["euvalues"].data[index]
                    medianval = meanval
                    stdevval = 0
                    medtimes.append(calc_median_time(self.data["dates"].data[index:self.blocks[i + 1]]))
                    means.append(meanval)
                    medians.append(medianval)
                    stdevs.append(stdevval)
                    maxs.append(meanval)
                    mins.append(meanval)

        self.mean = means
        self.median = medians
        self.stdev = stdevs
        self.median_times = medtimes
        self.max = maxs
        self.min = mins

    def bokeh_plot(self, show_plot=False, savefig=False, out_dir='./', nominal_value=None, yellow_limits=None,
                   red_limits=None, title=None, xrange=(None, None), yrange=(None, None), return_components=True,
                   return_fig=False, plot_data=True, plot_mean=False, plot_median=False, plot_max=False, plot_min=False):
        """Make basic bokeh plot showing value as a function of time. Optionally add a line indicating
        nominal (expected) value, as well as yellow and red background regions to denote values that
        may be unexpected.

        Paramters
        ---------
        show_plot : bool
            If True, show plot on screen rather than returning div and script

        savefig : bool
            If True, file is saved to html file

        out_dir : str
            Directory into which the html file is saved

        nominal_value : float
            Expected or nominal value for the telemetry. If provided, a horizontal dashed line
            at this value will be added.

        yellow_limits : list
            2-element list giving the lower and upper limits outside of which the telemetry value
            is considered non-nominal. If provided, the area of the plot between these two values
            will be given a green background, and that outside of these limits will have a yellow
            background.

        red_limits : list
            2-element list giving the lower and upper limits outside of which the telemetry value
            is considered worse than in the yellow region. If provided, the area of the plot outside
            of these two values will have a red background.

        title : str
            Will be used as the plot title. If None, the mnemonic name and description (if present)
            will be used as the title

        xrange : tuple
            Tuple of min, max datetime values to use as the plot range in the x direction.

        yrange : tuple
            Tuple of min, max datetime values to use as the plot range in the y direction.

        return_components : bool
            If True, return the plot as div and script components

        return_fig : bool
            If True, return the plot as a bokeh Figure object

        plot_data : bool
            If True, plot the data in the EdbMnemonic.data table

        plot_mean : bool
            If True, also plot the line showing the self.mean values

        plot_median : bool
            If True, also plot the line showing the self.median values

        plot_max : bool
            If True, also plot the line showing the self.max values

        plot_min : bool
            If True, also plot the line showing the self.min values


        Parameters
        ----------
        show_plot : boolean
            A switch to show the plot in the browser or not.

        Returns
        -------
        obj : list or bokeh.plotting.figure
            If return_components is True, return a list containing [div, script]
            If return_figre is True, return the bokeh figure itself
        """
        # Make sure that only one output type is specified, or bokeh will get mad
        options = np.array([show_plot, savefig, return_components, return_fig])
        if np.sum(options) > 1:
            trues = np.where(options)[0]
            raise ValueError((f'{options[trues]} are set to True in plot_every_change_data. Bokeh '
                              'will only allow one of these to be True.'))

        # yellow and red limits must come in pairs
        if yellow_limits is not None:
            if len(yellow_limits) != 2:
                yellow_limits = None
        if red_limits is not None:
            if len(red_limits) != 2:
                red_limits = None

        # If there are no data in the table, then produce an empty plot in the date
        # range specified by the requested start and end time
        if len(self.data["dates"]) == 0:
            null_dates = [self.requested_start_time, self.requested_end_time]
            null_vals = [0, 0]
            source = ColumnDataSource(data={'x': null_dates, 'y': null_vals})
        else:
            source = ColumnDataSource(data={'x': self.data['dates'], 'y': self.data['euvalues']})

        if savefig:
            filename = os.path.join(out_dir, f"telem_plot_{self.mnemonic_identifier.replace(' ','_')}.html")

        if self.info is None:
            units = 'Unknown'
        else:
            units = self.info["unit"]

        # Create a useful plot title if necessary
        if title is None:
            if 'description' in self.info:
                if len(self.info['description']) > 0:
                    title = f'{self.mnemonic_identifier} - {self.info["description"]}'
                else:
                    title = self.mnemonic_identifier
            else:
                title = self.mnemonic_identifier

        fig = figure(tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type='datetime',
                     title=title, x_axis_label='Time', y_axis_label=f'{units}')

        # For cases where the plot is empty or contains only a single point, force the
        # plot range to something reasonable
        if len(self.data["dates"]) < 2:
            fig.x_range = Range1d(self.requested_start_time - timedelta(days=1), self.requested_end_time)
            bottom, top = (-1, 1)
            if yellow_limits is not None:
                bottom, top = yellow_limits
            if red_limits is not None:
                bottom, top = red_limits
            fig.y_range = Range1d(bottom, top)

        if plot_data:
            data = fig.scatter(x='x', y='y', line_width=1, line_color='blue', source=source)
            data_line = fig.line(x='x', y='y', line_width=1, line_color='blue', source=source)
            hover_tool = HoverTool(tooltips=[('Value', '@y'),
                                             ('Date', '@x{%d %b %Y %H:%M:%S}')
                                             ], mode='mouse', renderers=[data])
            hover_tool.formatters = {'@x': 'datetime'}
            fig.tools.append(hover_tool)

        # Plot the mean value over time
        if len(self.median_times) > 0:
            if self.median_times[0] is not None:
                if plot_mean:
                    source_mean = ColumnDataSource(data={'mean_x': self.median_times, 'mean_y': self.mean})
                    mean_data = fig.scatter(x='mean_x', y='mean_y', line_width=1, line_color='orange', alpha=0.75, source=source_mean)
                    mean_hover_tool = HoverTool(tooltips=[('Mean', '@mean_y'),
                                                          ('Date', '@mean_x{%d %b %Y %H:%M:%S}')
                                                         ], mode='mouse', renderers=[mean_data])
                    mean_hover_tool.formatters = {'@mean_x': 'datetime'}
                    fig.tools.append(mean_hover_tool)

                if plot_median:
                    source_median = ColumnDataSource(data={'median_x': self.median_times, 'median_y': self.median})
                    median_data = fig.scatter(x='median_x', y='median_y', line_width=1, line_color='orangered', alpha=0.75, source=source_median)
                    median_hover_tool = HoverTool(tooltips=[('Median', '@median_y'),
                                                            ('Date', '@median_x{%d %b %Y %H:%M:%S}')
                                                           ], mode='mouse', renderers=[median_data])
                    median_hover_tool.formatters = {'@median_x': 'datetime'}
                    fig.tools.append(median_hover_tool)

                 # If the max and min arrays are to be plotted, create columndata sources for them as well
                if plot_max:
                    source_max = ColumnDataSource(data={'max_x': self.median_times, 'max_y': self.max})
                    max_data = fig.scatter(x='max_x', y='max_y', line_width=1, color='black', line_color='black', source=source_max)
                    max_hover_tool = HoverTool(tooltips=[('Max', '@max_y'),
                                                         ('Date', '@max_x{%d %b %Y %H:%M:%S}')
                                                        ], mode='mouse', renderers=[max_data])
                    max_hover_tool.formatters = {'@max_x': 'datetime'}
                    fig.tools.append(max_hover_tool)

                if plot_min:
                    source_min = ColumnDataSource(data={'min_x': self.median_times, 'min_y': self.min})
                    min_data = fig.scatter(x='min_x', y='min_y', line_width=1, color='black', line_color='black', source=source_min)
                    minn_hover_tool = HoverTool(tooltips=[('Min', '@min_y'),
                                                          ('Date', '@min_x{%d %b %Y %H:%M:%S}')
                                                         ], mode='mouse', renderers=[min_data])
                    min_hover_tool.formatters = {'@min_x': 'datetime'}
                    fig.tools.append(min_hover_tool)

        if len(self.data["dates"]) == 0:
            data.visible = False
            if nominal_value is not None:
                fig.line(null_dates, np.repeat(nominal_value, len(null_dates)), color='black',
                         line_dash='dashed', alpha=0.5)
        else:
            # If there is a nominal value provided, plot a dashed line for it
            if nominal_value is not None:
                fig.line(self.data['dates'], np.repeat(nominal_value, len(self.data['dates'])), color='black',
                         line_dash='dashed', alpha=0.5)

        # If limits for warnings/errors are provided, create colored background boxes
        if yellow_limits is not None or red_limits is not None:
            fig = add_limit_boxes(fig, yellow=yellow_limits, red=red_limits)

        # Make the x axis tick labels look nice
        fig.xaxis.formatter = DatetimeTickFormatter(microseconds=["%d %b %H:%M:%S.%3N"],
                                                    seconds=["%d %b %H:%M:%S.%3N"],
                                                    hours=["%d %b %H:%M"],
                                                    days=["%d %b %H:%M"],
                                                    months=["%d %b %Y %H:%M"],
                                                    years=["%d %b %Y"]
                                                    )
        fig.xaxis.major_label_orientation = np.pi / 4

        # Force the axes' range if requested
        if xrange[0] is not None:
            fig.x_range.start = xrange[0].timestamp() * 1000.
        if xrange[1] is not None:
            fig.x_range.end = xrange[1].timestamp() * 1000.
        if yrange[0] is not None:
            fig.y_range.start = yrange[0]
        if yrange[1] is not None:
            fig.y_range.end = yrange[1]

        if savefig:
            output_file(filename=filename, title=self.mnemonic_identifier)
            save(fig)

        if show_plot:
            show(fig)
        if return_components:
            script, div = components(fig)
            return [div, script]
        if return_fig:
            return fig

    def bokeh_plot_text_data(self, show_plot=False):
        """Make basic bokeh plot showing value as a function of time.

        Parameters
        ----------
        show_plot : boolean
            A switch to show the plot in the browser or not.

        Returns
        -------
        [div, script] : list
            List containing the div and js representations of figure.
        """

        abscissa = self.data['dates']
        ordinate = self.data['euvalues']

        p1 = figure(tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type='datetime',
                    title=self.mnemonic_identifier, x_axis_label='Time')

        override_dict = {}  # Dict instructions to set y labels
        unique_values = np.unique(ordinate)  # Unique values in y data

        # Enumerate i to plot 1, 2, ... n in y and then numbers as dict keys
        # and text as value. This will tell bokeh to change which numerical
        # values to text.
        for i, value in enumerate(unique_values):
            index = np.where(ordinate == value)[0]
            override_dict[i] = value
            dates = abscissa[index].astype(np.datetime64)
            y_values = list(np.ones(len(index), dtype=int) * i)
            p1.line(dates, y_values, line_width=1, line_color='blue', line_dash='dashed')
            p1.circle(dates, y_values, color='blue')

        p1.yaxis.ticker = list(override_dict.keys())
        p1.yaxis.major_label_overrides = override_dict

        if show_plot:
            show(p1)
        else:
            script, div = components(p1)

            return [div, script]

    def change_only_add_points(self):
        """Tweak change-only data. Add an additional data point immediately prior to
        each original data point, with a value equal to that in the previous data point.
        This will help with filtering data based on conditions later, and will create a
        plot that looks more realistic, with only horizontal and vertical lines.
        """
        new_dates = [self.data["dates"][0]]
        new_vals = [self.data["euvalues"][0]]
        delta_t = timedelta(microseconds=1)
        for i, row in enumerate(self.data["dates"][1:]):
            new_dates.append(self.data["dates"][i + 1] - delta_t)
            new_vals.append(self.data["euvalues"][i])
            new_dates.append(self.data["dates"][i + 1])
            new_vals.append(self.data["euvalues"][i + 1])
        new_table = Table()
        new_table["dates"] = new_dates
        new_table["euvalues"] = new_vals
        self.data = new_table

        # Update the metadata to say that this is no longer change-only data
        self.meta['TlmMnemonics'][0]['AllPoints'] = 1

    def daily_stats(self, sigma=3):
        """Calculate the statistics for each day in the data
        contained in data["data"]. Should we add a check for a
        case where the final block of time is <<1 day?

        Parameters
        ----------
        sigma : int
            Number of sigma to use for sigma clipping
        """
        if len(self.data["euvalues"]) == 0:
            self.mean = []
            self.median = []
            self.stdev = []
            self.median_times = []
            self.max = []
            self.min = []
        else:
            if type(self.data["euvalues"].data[0]) not in [np.str_, str]:
                min_date = np.min(self.data["dates"])
                date_range = np.max(self.data["dates"]) - min_date
                num_days = date_range.days
                num_seconds = date_range.seconds
                range_days = num_days + 1

                # Generate a list of times to use as boundaries for calculating means
                limits = np.array([min_date + timedelta(days=x) for x in range(range_days)])
                limits = np.append(limits, np.max(self.data["dates"]))

                means, meds, devs, maxs, mins, times = [], [], [], [], [], []
                for i in range(len(limits) - 1):
                    good = np.where((self.data["dates"] >= limits[i]) & (self.data["dates"] < limits[i + 1]))

                    if self.meta['TlmMnemonics'][0]['AllPoints'] != 0:
                        avg, med, dev = sigma_clipped_stats(self.data["euvalues"][good], sigma=sigma)
                        maxval = np.max(self.data["euvalues"][good])
                        minval = np.min(self.data["euvalues"][good])
                    else:
                        avg, med, dev, maxval, minval = change_only_stats(self.data["dates"][good], self.data["euvalues"][good], sigma=sigma)
                    means.append(avg)
                    meds.append(med)
                    maxs.append(maxval)
                    mins.append(minval)
                    devs.append(dev)
                    times.append(limits[i] + (limits[i + 1] - limits[i]) / 2.)
                self.mean = means
                self.median = meds
                self.stdev = devs
                self.median_times = times
                self.max = maxs
                self.min = mins
            else:
                # If the mnemonic data are strings, we don't compute statistics
                self.mean = []
                self.median = []
                self.stdev = []
                self.median_times = []
                self.max = []
                self.min = []

    def full_stats(self, sigma=3):
        """Calculate the mean/median/stdev of the full compliment of data

        Parameters
        ----------
        sigma : int
            Number of sigma to use for sigma clipping
        """
        if type(self.data["euvalues"].data[0]) not in [np.str_, str]:
            if self.meta['TlmMnemonics'][0]['AllPoints'] != 0:
                self.mean, self.median, self.stdev = sigma_clipped_stats(self.data["euvalues"], sigma=sigma)
                self.max = np.max(self.data["euvalues"])
                self.min = np.min(self.data["euvalues"])
            else:
                self.mean, self.median, self.stdev, self.max, self.min = change_only_stats(self.data["dates"], self.data["euvalues"], sigma=sigma)
            self.mean = [self.mean]
            self.median = [self.median]
            self.stdev = [self.stdev]
            self.max = [self.max]
            self.min = [self.min]
            self.median_times = [calc_median_time(self.data["dates"])]
        else:
            # If the mnemonic values are strings, don't compute statistics
            self.mean = []
            self.median = []
            self.stdev = []
            self.max = []
            self.min = []
            self.median_times = []

    def get_table_data(self):
        """Get data needed to make interactivate table in template."""

        # generate tables for display and download in web app
        display_table = copy.deepcopy(self.data)

        # temporary html file,
        # see http://docs.astropy.org/en/stable/_modules/astropy/table/
        tmpdir = tempfile.mkdtemp()
        file_name_root = 'mnemonic_exploration_result_table'
        path_for_html = os.path.join(tmpdir, '{}.html'.format(file_name_root))
        with open(path_for_html, 'w') as tmp:
            display_table.write(tmp, format='jsviewer')
        html_file_content = open(path_for_html, 'r').read()

        return html_file_content

    def interpolate(self, times):
        """Interpolate data euvalues at specified datetimes.

        Parameters
        ----------
        times : list
            List of datetime objects describing the times to interpolate to
        """
        new_tab = Table()

        # Change-only data is unique and needs its own way to be interpolated
        if self.meta['TlmMnemonics'][0]['AllPoints'] == 0:
            new_values = []
            new_dates = []
            for time in times:
                latest = np.where(self.data["dates"] <= time)[0]
                if len(latest) > 0:
                    new_values.append(self.data["euvalues"][latest[-1]])
                    new_dates.append(time)
            if len(new_values) > 0:
                new_tab["euvalues"] = np.array(new_values)
                new_tab["dates"] = np.array(new_dates)

        # This is for non change-only data
        else:
            # We can only linearly interpolate if we have more than one entry
            if len(self.data["dates"]) >= 2:
                interp_times = np.array([create_time_offset(ele, self.data["dates"][0]) for ele in times])
                mnem_times = np.array([create_time_offset(ele, self.data["dates"][0]) for ele in self.data["dates"]])

                # Do not extrapolate. Any requested interoplation times that are outside the range
                # or the original data will be ignored.
                good_times = ((interp_times >= mnem_times[0]) & (interp_times <= mnem_times[-1]))
                interp_times = interp_times[good_times]

                new_tab["euvalues"] = np.interp(interp_times, mnem_times, self.data["euvalues"])
                new_tab["dates"] = np.array([add_time_offset(ele, self.data["dates"][0]) for ele in interp_times])

            else:
                # If there are not enough data and we are unable to interpolate,
                # then set the data table to be empty
                new_tab["euvalues"] = np.array([])
                new_tab["dates"] = np.array([])

        # Adjust any block values to account for the interpolated data
        new_blocks = []
        if self.blocks is not None:
            for index in self.blocks[0:-1]:
                good = np.where(new_tab["dates"] >= self.data["dates"][index])[0]

                if len(good) > 0:
                    new_blocks.append(good[0])

            # Add en entry for the final element if it's not already there
            if len(new_blocks) > 0:
                if new_blocks[-1] < len(new_tab["dates"]):
                    new_blocks.append(len(new_tab["dates"]))
                self.blocks = np.array(new_blocks)

        # Update the data in the instance.
        self.data = new_tab

    def plot_data_plus_devs(self, use_median=False, show_plot=False, savefig=False, out_dir='./', nominal_value=None, yellow_limits=None,
                            red_limits=None, xrange=(None, None), yrange=(None, None), title=None, return_components=True,
                            return_fig=False, plot_max=False, plot_min=False):
        """Make basic bokeh plot showing value as a function of time. Optionally add a line indicating
        nominal (expected) value, as well as yellow and red background regions to denote values that
        may be unexpected. Also add a plot of the mean value over time and in a second figure, a plot of
        the devaition from the mean.

        Paramters
        ---------
        use_median : bool
            If True, plot the median rather than the mean, as well as the deviation from the
            median rather than from the mean

        show_plot : bool
            If True, show plot on screen rather than returning div and script

        savefig : bool
            If True, file is saved to html file

        out_dir : str
            Directory into which the html file is saved

        nominal_value : float
            Expected or nominal value for the telemetry. If provided, a horizontal dashed line
            at this value will be added.

        yellow_limits : list
            2-element list giving the lower and upper limits outside of which the telemetry value
            is considered non-nominal. If provided, the area of the plot between these two values
            will be given a green background, and that outside of these limits will have a yellow
            background.

        red_limits : list
            2-element list giving the lower and upper limits outside of which the telemetry value
            is considered worse than in the yellow region. If provided, the area of the plot outside
            of these two values will have a red background.

        xrange : tuple
            Tuple of min, max datetime values to use as the plot range in the x direction.

        yrange : tuple
            Tuple of min, max datetime values to use as the plot range in the y direction.

        title : str
            Will be used as the plot title. If None, the mnemonic name and description (if present)
            will be used as the title

        return_components : bool
            If True, return the plot as div and script components

        return_fig : bool
            If True, return the plot as a bokeh Figure object

        plot_max : bool
            If True, also plot the line showing the self.max values

        plot_min : bool
            If True, also plot the line showing the self.min values

        Returns
        -------
        obj : list or bokeh.plotting.figure
            If return_components is True, return a list containing [div, script]
            If return_figre is True, return the bokeh figure itself
        """
        # Make sure that only one output type is specified, or bokeh will get mad
        options = np.array([show_plot, savefig, return_components, return_fig])
        if np.sum(options) > 1:
            trues = np.where(options)[0]
            raise ValueError((f'{options[trues]} are set to True in plot_every_change_data. Bokeh '
                              'will only allow one of these to be True.'))

        # If there are no data in the table, then produce an empty plot in the date
        # range specified by the requested start and end time
        if len(self.data["dates"]) == 0:
            null_dates = [self.requested_start_time, self.requested_end_time]
            null_vals = [0, 0]
            data_dates = null_dates
            data_vals = null_vals
        else:
            data_dates = self.data['dates']
            data_vals = self.data['euvalues']
        source = ColumnDataSource(data={'x': data_dates, 'y': data_vals})

        # yellow and red limits must come in pairs
        if yellow_limits is not None:
            if len(yellow_limits) != 2:
                yellow_limits = None
        if red_limits is not None:
            if len(red_limits) != 2:
                red_limits = None

        if savefig:
            filename = os.path.join(out_dir, f"telem_plot_{self.mnemonic_identifier.replace(' ','_')}.html")

        if self.info is None:
            units = 'Unknown'
        else:
            units = self.info["unit"]

        # Create a useful plot title if necessary
        if title is None:
            if 'description' in self.info:
                if len(self.info['description']) > 0:
                    title = f'{self.mnemonic_identifier} - {self.info["description"]}'
                else:
                    title = self.mnemonic_identifier
            else:
                title = self.mnemonic_identifier

        fig = figure(tools='pan,box_zoom,reset,wheel_zoom,save', x_axis_type=None,
                     title=title, x_axis_label='Time',
                     y_axis_label=f'{units}')

        # For cases where the plot is empty or contains only a single point, force the
        # plot range to something reasonable
        if len(self.data["dates"]) < 2:
            fig.x_range = Range1d(self.requested_start_time - timedelta(days=1), self.requested_end_time)
            bottom, top = (-1, 1)
            if yellow_limits is not None:
                bottom, top = yellow_limits
            if red_limits is not None:
                bottom, top = red_limits
            fig.y_range = Range1d(bottom, top)

        data = fig.scatter(x='x', y='y', line_width=1, line_color='blue', source=source)

        # Plot the mean value over time
        if len(self.median_times) > 0:
            if self.median_times[0] is not None:
                if use_median:
                    meanvals = self.median
                else:
                    meanvals = self.mean

                mean_data = fig.line(self.median_times, meanvals, line_width=1, line_color='orange', alpha=0.75)

                # If the max and min arrays are to be plotted, create columndata sources for them as well
                if plot_max:
                    source_max = ColumnDataSource(data={'max_x': self.median_times, 'max_y': self.max})
                    fig.scatter(x='max_x', y='max_y', line_width=1, line_color='black', source=source_max)

                if plot_min:
                    source_min = ColumnDataSource(data={'min_x': self.median_times, 'min_y': self.min})
                    fig.scatter(x='min_x', y='min_y', line_width=1, line_color='black', source=source_min)

        if len(self.data["dates"]) == 0:
            data.visible = False
            if nominal_value is not None:
                fig.line(null_dates, np.repeat(nominal_value, len(null_dates)), color='black',
                         line_dash='dashed', alpha=0.5)
        else:
            # If there is a nominal value provided, plot a dashed line for it
            if nominal_value is not None:
                fig.line(self.data['dates'], np.repeat(nominal_value, len(self.data['dates'])), color='black',
                         line_dash='dashed', alpha=0.5)

        # If limits for warnings/errors are provided, create colored background boxes
        if yellow_limits is not None or red_limits is not None:
            fig = add_limit_boxes(fig, yellow=yellow_limits, red=red_limits)

        hover_tool = HoverTool(tooltips=[('Value', '@y'),
                                         ('Date', '@x{%d %b %Y %H:%M:%S}')
                                         ], mode='mouse', renderers=[data])
        hover_tool.formatters = {'@x': 'datetime'}

        fig.tools.append(hover_tool)

        # Force the axes' range if requested
        if xrange[0] is not None:
            fig.x_range.start = xrange[0].timestamp() * 1000.
        if xrange[1] is not None:
            fig.x_range.end = xrange[1].timestamp() * 1000.
        if yrange[0] is not None:
            fig.y_range.start = yrange[0]
        if yrange[1] is not None:
            fig.y_range.end = yrange[1]

        # Now create a second plot showing the devitation from the mean
        fig_dev = figure(height=250, x_range=fig.x_range, tools="xpan,xwheel_zoom,xbox_zoom,reset", y_axis_location="left",
                         x_axis_type='datetime', x_axis_label='Time', y_axis_label=f'Data - Mean ({units})')

        # Interpolate the mean values so that we can subtract the original data
        if len(self.median_times) > 1:
            interp_means = interpolate_datetimes(data_dates, self.median_times, meanvals)
            dev = data_vals - interp_means
        elif len(self.median_times) == 1:
            if self.median_times[0] is not None:
                dev = data_vals - meanvals
            else:
                dev = [0] * len(data_vals)
        else:
            # No median data, so we can't calculate any deviation
            dev = [0] * len(data_vals)

        # Plot
        fig_dev.line(data_dates, dev, color='red')

        # Make the x axis tick labels look nice
        fig_dev.xaxis.formatter = DatetimeTickFormatter(microseconds=["%d %b %H:%M:%S.%3N"],
                                                        seconds=["%d %b %H:%M:%S.%3N"],
                                                        hours=["%d %b %H:%M"],
                                                        days=["%d %b %H:%M"],
                                                        months=["%d %b %Y %H:%M"],
                                                        years=["%d %b %Y"]
                                                        )
        fig.xaxis.major_label_orientation = np.pi / 4

        # Place the two figures in a column object
        bothfigs = column(fig, fig_dev)

        if savefig:
            output_file(filename=filename, title=self.mnemonic_identifier)
            save(bothfigs)

        if show_plot:
            show(bothfigs)
        if return_components:
            script, div = components(bothfigs)
            return [div, script]
        if return_fig:
            return bothfigs

    def save_table(self, outname):
        """Save the EdbMnemonic instance

        Parameters
        ----------
        outname : str
            Name of text file to save information into
        """
        ascii.write(self.data, outname, overwrite=True)

    def timed_stats(self, sigma=3):
        """Break up the data into chunks of the given duration. Calculate the
        mean value for each chunk.

        Parameters
        ----------
        sigma : int
            Number of sigma to use in sigma-clipping
        """
        if type(self.data["euvalues"].data[0]) not in [np.str_, str]:
            duration_secs = self.mean_time_block.to('second').value
            date_arr = np.array(self.data["dates"])
            num_bins = (np.max(self.data["dates"]) - np.min(self.data["dates"])).total_seconds() / duration_secs

            # Round up to the next integer if there is a fractional number of bins
            num_bins = np.ceil(num_bins)

            self.mean = []
            self.median = []
            self.max = []
            self.min = []
            self.stdev = []
            self.median_times = []
            for i in range(int(num_bins)):
                min_date = self.data["dates"][0] + timedelta(seconds=i * duration_secs)
                max_date = min_date + timedelta(seconds=duration_secs)
                good = ((date_arr >= min_date) & (date_arr < max_date))
                if self.meta['TlmMnemonics'][0]['AllPoints'] != 0:
                    avg, med, dev = sigma_clipped_stats(self.data["euvalues"][good], sigma=sigma)
                    maxval = np.max(self.data["euvalues"][good])
                    minval = np.min(self.data["euvalues"][good])
                else:
                    avg, med, dev, maxval, minval = change_only_stats(self.data["dates"][good], self.data["euvalues"][good], sigma=sigma)
                if np.isfinite(avg):
                    self.mean.append(avg)
                    self.median.append(med)
                    self.stdev.append(dev)
                    self.max.append(maxval)
                    self.min.append(minval)
                    self.median_times.append(calc_median_time(self.data["dates"].data[good]))
        else:
            self.mean = []
            self.median = []
            self.stdev = []
            self.max = []
            self.min = []
            self.median_times = []


def add_limit_boxes(fig, yellow=None, red=None):
    """Add green/yellow/red background colors

    Parameters
    ----------
    fig : bokeh.plotting.figure
        Bokeh figure of the telemetry values

    yellow : list
        2-element list of [low, high] values. If provided, the areas of the plot less than <low>
        and greater than <high> will be given a yellow background, to indicate an area
        of concern.

    red : list
        2-element list of [low, high] values. If provided, the areas of the plot less than <low>
        and greater than <high> will be given a red background, to indicate values that
        may indicate an error. It is assumed that the low value of red is less
        than the low value of yellow, and that the high value of red is
        greater than the high value of yellow.

    Returns
    -------
    fig : bokeh.plotting.figure
        Modified figure with BoxAnnotations added
    """
    if yellow is not None:
        green = BoxAnnotation(bottom=yellow[0], top=yellow[1], fill_color='chartreuse', fill_alpha=0.2)
        fig.add_layout(green)
        if red is not None:
            yellow_high = BoxAnnotation(bottom=yellow[1], top=red[1], fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_high)
            yellow_low = BoxAnnotation(bottom=red[0], top=yellow[0], fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_low)
            red_high = BoxAnnotation(bottom=red[1], top=red[1] + 100, fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_high)
            red_low = BoxAnnotation(bottom=red[0] - 100, top=red[0], fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_low)

        else:
            yellow_high = BoxAnnotation(bottom=yellow[1], top=yellow[1] + 100, fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_high)
            yellow_low = BoxAnnotation(bottom=yellow[0] - 100, top=yellow[0], fill_color='gold', fill_alpha=0.2)
            fig.add_layout(yellow_low)

    else:
        if red is not None:
            green = BoxAnnotation(bottom=red[0], top=red[1], fill_color='chartreuse', fill_alpha=0.2)
            fig.add_layout(green)
            red_high = BoxAnnotation(bottom=red[1], top=red[1] + 100, fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_high)
            red_low = BoxAnnotation(bottom=red[0] - 100, top=red[0], fill_color='red', fill_alpha=0.1)
            fig.add_layout(red_low)

    return fig


def add_time_offset(offset, dt_obj):
    """Add an offset to an input datetime object

    Parameters
    ----------
    offset : float
        Number of seconds to be added

    dt_obj : datetime.datetime
        Datetime object to which the seconds are added

    Returns
    -------
    obj : datetime.datetime
        Sum of the input datetime objects and the offset seconds.
    """
    return dt_obj + timedelta(seconds=offset)


def calc_median_time(time_arr):
    """Calcualte the median time of the input time_arr

    Parameters
    ----------
    time_arr : numpy.ndarray
        1D array of datetime objects

    Returns
    -------
    med_time : datetime.datetime
        Median time, as a datetime object
    """
    if len(time_arr) > 0:
        med_time = time_arr[0] + ((time_arr[-1] - time_arr[0]) / 2.)
    else:
        med_time = np.nan
    return med_time


def change_only_bounding_points(date_list, value_list, starttime, endtime):
    """For data containing change-only values, where bracketing data outside
    the requested time span may be present, create data points at the starting
    and ending times. This can be helpful with later interpolations.

    Parameters
    ----------
    date_list : list
        List of datetime values

    value_list : list
        List of corresponding mnemonic values

    starttime : datetime.datetime
        Start time

    endtime : datetime.datetime
        End time

    Returns
    -------
    date_list : list
        List of datetime values

    value_list : list
        List of corresponding mnemonic values
    """
    date_list_arr = np.array(date_list)

    if isinstance(starttime, Time):
        starttime = starttime.datetime

    if isinstance(endtime, Time):
        endtime = endtime.datetime

    valid_idx = np.where((date_list_arr <= endtime) & (date_list_arr >= starttime))[0]
    before_startime = np.where(date_list_arr < starttime)[0]
    before_endtime = np.where(date_list_arr < endtime)[0]

    # The value at starttime is either the value of the last point before starttime,
    # or NaN if there are no points prior to starttime
    if len(before_startime) == 0:
        value0 = np.nan
    else:
        value0 = value_list[before_startime[-1]]

    # The value at endtime is NaN if there are no times before the endtime.
    # Otherwise the value is equal to the value at the last point before endtime
    if len(before_endtime) == 0:
        value_end = np.nan
    else:
        value_end = value_list[before_endtime[-1]]

    # Crop the arrays down to the times between starttime and endtime
    date_list = list(np.array(date_list)[valid_idx])
    value_list = list(np.array(value_list)[valid_idx])

    # Add an entry for starttime and another for endtime, but not if
    # the values are NaN
    if isinstance(value0, Number):
        if not np.isnan(value0):
            date_list.insert(0, starttime)
            value_list.insert(0, value0)
    elif isinstance(value0, str):
        date_list.insert(0, starttime)
        value_list.insert(0, value0)

    if isinstance(value_end, Number):
        if not np.isnan(value_end):
            date_list.append(endtime)
            value_list.append(value_end)
    elif isinstance(value_end, str):
        date_list.append(endtime)
        value_list.append(value_end)

    return date_list, value_list


def change_only_stats(times, values, sigma=3):
    """Calculate the mean/median/stdev as well as the median time for a
    collection of change-only data.

    Parameters
    ----------
    times : list
        List of datetime objects

    values : list
        List of values corresponding to times

    sigma : float
        Number of sigma to use for sigma-clipping

    Returns
    -------
    meanval : float
        Mean of values

    medianval : float
        Median of values

    stdevval : float
        Standard deviation of values
    """
    # If there is only a single datapoint, then the mean will be
    # equal to it.
    if len(times) == 0:
        return None, None, None, None, None
    if len(times) == 1:
        return values, values, 0., values, values
    else:
        times = np.array(times)
        values = np.array(values)
        delta_time = times[1:] - times[0:-1]
        delta_time_weight = np.array([e.total_seconds() for e in delta_time])

        # Add weight for the final point. Set it to 1 microsecond
        delta_time_weight = np.append(delta_time_weight, 1e-6)

        meanval = np.average(values, weights=delta_time_weight)
        stdevval = np.sqrt(np.average((values - meanval) ** 2, weights=delta_time_weight))
        maxval = np.max(values)
        minval = np.min(values)

        # In order to calculate the median, we need to adjust the weights such that
        # the weight represents the number of times a given value is present. Scale
        # it so that the minimum weight is 1
        delta_time_weight = (delta_time_weight / np.min(delta_time_weight)).astype(int)

        # Now we find the median by sorting the values, keeping a running total of the
        # total number of entries given that each value will have a number of instances
        # dictat<ed by the weight, and selecting the value associated with the central
        # element.
        total_num = np.sum(delta_time_weight)
        if np.mod(total_num, 2) == 1:
            midpt = total_num / 2
            odd = True
        else:
            midpt = total_num / 2 - 1
            odd = False
        sorted_idx = np.argsort(values)
        values = values[sorted_idx]
        delta_time_weight = delta_time_weight[sorted_idx]
        total_idx = 0
        for i, (val, weight) in enumerate(zip(values, delta_time_weight)):
            total_idx += weight
            if total_idx >= midpt:
                if odd:
                    medianval = val
                else:
                    if total_idx > midpt:
                        medianval = val
                    else:
                        medianval = (val + values[i + 1]) / 2.
                break

    return meanval, medianval, stdevval, maxval, minval


def create_time_offset(dt_obj, epoch):
    """Subtract input epoch from a datetime object and return the
    residual number of seconds

    Paramters
    ---------
    dt_obj : datetime.datetime
        Original datetiem object

    epoch : datetime.datetime
        Datetime to be subtracted from dt_obj

    Returns
    -------
    obj : float
        Number of seconds between dt_obj and epoch
    """
    if isinstance(dt_obj, Time):
        return (dt_obj - epoch).to(u.second).value
    elif isinstance(dt_obj, datetime):
        return (dt_obj - epoch).total_seconds()


def get_mnemonic(mnemonic_identifier, start_time, end_time):
    """Execute query and return a ``EdbMnemonic`` instance.

    The underlying MAST service returns data that include the
    datapoint preceding the requested start time and the datapoint
    that follows the requested end time.

    Parameters
    ----------
    mnemonic_identifier : str
        Telemetry mnemonic identifiers, e.g. ``SA_ZFGOUTFOV``

    start_time : astropy.time.Time or datetime.datetime
        Start time

    end_time : astropy.time.Time or datetime.datetime
        End time

    Returns
    -------
    mnemonic : instance of EdbMnemonic
        EdbMnemonic object containing query results
    """
    base_url = get_mast_base_url()
    service = ENGDB_Service(base_url)  # By default, will use the public MAST service.

    meta = service.get_meta(mnemonic_identifier)

    # If the mnemonic is stored as change-only data, then include bracketing values
    # outside of the requested start and stop times. These may be needed later to
    # translate change-only data into all-points data.
    if meta['TlmMnemonics'][0]['AllPoints'] == 0:
        bracket = True
    else:
        bracket = False

    data = service.get_values(mnemonic_identifier, start_time, end_time, include_obstime=True,
                              include_bracket_values=bracket)

    dates = [datetime.strptime(row.obstime.iso, "%Y-%m-%d %H:%M:%S.%f") for row in data]
    values = [row.value for row in data]

    if bracket:
        # For change-only data, check to see how many additional data points there are before
        # the requested start time and how many are after the requested end time. Note that
        # the max for this should be 1, but it's also possible to have zero (e.g. if you are
        # querying up through the present and there are no more recent data values.) Use these
        # to produce entries at the beginning and ending of the queried time range.
        if len(dates) > 0:
            dates, values = change_only_bounding_points(dates, values, start_time, end_time)

    data = Table({'dates': dates, 'euvalues': values})
    info = get_mnemonic_info(mnemonic_identifier)

    # Create and return instance
    mnemonic = EdbMnemonic(mnemonic_identifier, start_time, end_time, data, meta, info)

    # Convert change-only data to "regular" data. If this is not done, checking for
    # dependency conditions may not work well if there are a limited number of points.
    # Also, later interpolations won't be correct with change-only points since we are
    # doing linear interpolation.
    if bracket:
        if len(mnemonic) > 0:
            mnemonic.change_only_add_points()

    return mnemonic


def get_mnemonics(mnemonics, start_time, end_time):
    """Query DMS EDB with a list of mnemonics and a time interval.

    Parameters
    ----------
    mnemonics : list or numpy.ndarray
        Telemetry mnemonic identifiers, e.g. ``['SA_ZFGOUTFOV',
        'IMIR_HK_ICE_SEC_VOLT4']``
    start_time : astropy.time.Time instance
        Start time
    end_time : astropy.time.Time instance
        End time

    Returns
    -------
    mnemonic_dict : dict
        Dictionary. keys are the queried mnemonics, values are
        instances of EdbMnemonic
    """
    if not isinstance(mnemonics, (list, np.ndarray)):
        raise RuntimeError('Please provide a list/array of mnemonic_identifiers')

    mnemonic_dict = OrderedDict()
    for mnemonic_identifier in mnemonics:
        # fill in dictionary
        mnemonic_dict[mnemonic_identifier] = get_mnemonic(mnemonic_identifier, start_time, end_time)

    return mnemonic_dict


def get_mnemonic_info(mnemonic_identifier):
    """Return the mnemonic description.

    Parameters
    ----------
    mnemonic_identifier : str
        Telemetry mnemonic identifier, e.g. ``SA_ZFGOUTFOV``

    Returns
    -------
    info : dict
        Object that contains the returned data
    """
    mast_token = get_mast_token()
    return query_mnemonic_info(mnemonic_identifier, token=mast_token)


def interpolate_datetimes(new_times, old_times, old_data):
    """interpolate a set of datetime/value pairs onto another set
    of datetime objects

    Parameters
    ----------
    new_times : numpy.ndarray
        Array of datetime objects onto which the data will be interpolated

    old_times : numpy.ndarray
        Array of datetime objects associated with the input data values

    old_data : numpy.ndarray
        Array of data values associated with ``old_times``, which will be
        interpolated onto ``new_times``

    Returns
    -------
    new_data : numpy.ndarray
        Array of values interpolated onto ``new_times``
    """
    # We can only linearly interpolate if we have more than one entry
    if len(old_data) >= 2:
        interp_times = np.array([create_time_offset(ele, old_times[0]) for ele in new_times])
        mnem_times = np.array([create_time_offset(ele, old_times[0]) for ele in old_times])
        new_data = np.interp(interp_times, mnem_times, old_data)
    else:
        # If there are not enough data and we are unable to interpolate,
        # then set the data table to be empty
        new_data = np.array([])
    return new_data


def is_valid_mnemonic(mnemonic_identifier):
    """Determine if the given string is a valid EDB mnemonic.

    Parameters
    ----------
    mnemonic_identifier : str
        The mnemonic_identifier string to be examined.

    Returns
    -------
    bool
        Is mnemonic_identifier a valid EDB mnemonic?
    """
    inventory = mnemonic_inventory()[0]
    if mnemonic_identifier in inventory['tlmMnemonic']:
        return True
    else:
        return False


def mnemonic_inventory():
    """Return all mnemonics in the DMS engineering database.
    No authentication is required, this information is public.
    Since this is a rather large and quasi-static table (~15000 rows),
    it is cached using functools.

    Returns
    -------
    data : astropy.table.Table
        Table representation of the mnemonic inventory.
    meta : dict
        Additional information returned by the query.
    """
    out = Mast.service_request_async(MAST_EDB_MNEMONIC_SERVICE, {})
    data, meta = process_mast_service_request_result(out)

    # convert numerical ID to str for homogenity (all columns are str)
    data['tlmIdentifier'] = data['tlmIdentifier'].astype(str)

    return data, meta


def process_mast_service_request_result(result, data_as_table=True):
    """Parse the result of a MAST EDB query.

    Parameters
    ----------
    result : list of requests.models.Response instances
        The object returned by a call to ``Mast.service_request_async``
    data_as_table : bool
        If ``True``, return data as astropy table, else return as json

    Returns
    -------
    data : astropy.table.Table
        Table representation of the returned data.
    meta : dict
        Additional information returned by the query
    """
    json_data = result[0].json()
    if json_data['status'] != 'COMPLETE':
        raise RuntimeError('Mnemonic query did not complete.\nquery status: {}\nmessage: {}'.format(
            json_data['status'], json_data['msg']))

    try:
        # timestamp-value pairs in the form of an astropy table
        if data_as_table:
            data = Table(json_data['data'])
        else:
            if len(json_data['data']) > 0:
                data = json_data['data'][0]
            else:
                warnings.warn('Query did not return any data. Returning None')
                return None, None
    except KeyError:
        warnings.warn('Query did not return any data. Returning None')
        return None, None

    # collect meta data
    meta = {}
    for key in json_data.keys():
        if key.lower() != 'data':
            meta[key] = json_data[key]

    return data, meta


def query_mnemonic_info(mnemonic_identifier, token=None):
    """Query the EDB to return the mnemonic description.

    Parameters
    ----------
    mnemonic_identifier : str
        Telemetry mnemonic identifier, e.g. ``SA_ZFGOUTFOV``
    token : str
        MAST token

    Returns
    -------
    info : dict
        Object that contains the returned data
    """
    parameters = {"mnemonic": "{}".format(mnemonic_identifier)}
    result = Mast.service_request_async(MAST_EDB_DICTIONARY_SERVICE, parameters)
    info = process_mast_service_request_result(result, data_as_table=False)[0]

    return info
