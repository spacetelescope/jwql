#!/usr/bin/env python
#
"""
This module contains a class that can be used to retrieve OSS event messages from the engineering DB.
The messages are initially retrieved between a user-supplied starting and ending date/time.
The messages can be further filtered by visit ID (e.g. "V02235003001").

For visits that include a target acquisition (TA) observation, details of the TA performace
can also be extracted from the relevant log entries.

Original script created by Marshall Perrin, based on engdb_visit_times.py by Jeff Valenti
Modified by M.Gennaro to return the TA centroid values. Converted into a class, and expanded
to return more TA info by Bryan Hilbert
"""

import os
import argparse
from csv import reader
from datetime import datetime, timedelta, timezone
from getpass import getpass
from requests import Session
from time import sleep
import numpy as np


class EventLog():
    def __init__(self, startdate='2022-02-01T02:00:00.0', enddate='', mast_api_token='', verbose=False):
        self.startdate = datetime.fromisoformat(startdate)
        self.mast_api_token = mast_api_token
        self.verbose = verbose

        # set or interactively get mast token
        if not mast_api_token:
            self.mast_api_token = os.environ.get('MAST_API_TOKEN')
            if self.mast_api_token is None:
                raise ValueError("Must define MAST_API_TOKEN env variable or specify mast_api_token parameter")

        if not enddate:
            tz_utc = timezone(timedelta(hours=0))
            self.enddate = datetime.now(tz=tz_utc)
        else:
            self.enddate = datetime.fromisoformat(enddate)

        self.get_ictm_event_log()


    def get_ictm_event_log(self):
        """Retrieve the log entries corresponding to the given starting and ending times
        """
        # parameters
        mnemonic = 'ICTM_EVENT_MSG'

        # constants
        base = 'https://mast.stsci.edu/jwst/api/v0.1/Download/file?uri=mast:jwstedb'
        mastfmt = '%Y%m%dT%H%M%S'
        colhead = 'theTime'

        # establish MAST session
        session = Session()
        session.headers.update({'Authorization': f'token {self.mast_api_token}'})

        startstr = self.startdate.strftime(mastfmt)
        endstr = self.enddate.strftime(mastfmt)
        filename = f'{mnemonic}-{startstr}-{endstr}.csv'
        url = f'{base}/{filename}'

        if self.verbose:
            print(f"Retrieving {url}")
        response = session.get(url)
        if response.status_code == 401:
            exit('HTTPError 401 - Check your MAST token and EDB authorization. May need to refresh your token if it expired.')
        response.raise_for_status()
        self.eventlog = response.content.decode('utf-8').splitlines()


    def extract_oss_event_msgs_for_visit(self, selected_visit_id, ta_only=False, verbose=False):
        """Extract lines from self.eventlog that are for the given visit ID.
        """
        # parse response (ignoring header line) and print new event messages
        vid = ''
        in_selected_visit = False
        in_ta = False

        self.visit_messages = []

        if verbose:
            print(f"\tSearching for visit: {selected_visit_id}")
        for value in reader(self.eventlog, delimiter=',', quotechar='"'):
            if in_selected_visit and ((not ta_only) or in_ta) :
                #print(value[0][0:22], "\t", value[2])
                self.visit_messages.append(f'{value[0][0:22]}\t{value[2]}')

            if value[2][:6] == 'VISIT ':
                if value[2][-7:] == 'STARTED':
                    vstart = 'T'.join(value[0].split())[:-3]
                    vid = value[2].split()[1]

                    if vid == selected_visit_id:
                        if verbose:
                            print(f"VISIT {selected_visit_id} START FOUND at {vstart}")
                        self.visit_start = vstart
                        in_selected_visit = True
                        if ta_only:
                            if verbose:
                                print("Only displaying TARGET ACQUISITION RESULTS:")

                elif value[2][-5:] == 'ENDED' and in_selected_visit:
                    assert vid == value[2].split()[1]
                    assert selected_visit_id  == value[2].split()[1]

                    vend = 'T'.join(value[0].split())[:-3]
                    if verbose:
                        print(f"VISIT {selected_visit_id} END FOUND at {vend}")
                    self.visit_end = vend

                    in_selected_visit = False
            elif value[2][:31] == f'Script terminated: {vid}':
                if value[2][-5:] == 'ERROR':
                    script = value[2].split(':')[2]
                    vend = 'T'.join(value[0].split())[:-3]
                    self.visit_end = vend
                    dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                    note = f'Halt in {script}'
                    in_selected_visit = False
            elif in_selected_visit and value[2].startswith('*'): # this string is used to mark the start and end of TA sections
                in_ta = not in_ta


    def extract_oss_SAM(self, selected_visit_id, verbose=False):

        # parse response (ignoring header line) and print new event messages
        vid = ''
        in_selected_visit = False

        self.sam_info = {}

        if verbose:
            print(f"\tSearching for visit: {selected_visit_id}")
        for value in reader(self.eventlog, delimiter=',', quotechar='"'):
            if in_selected_visit :
                if "TA SAM (x, y) = " in value[2]:
                    out = value[2].split('=')[1]
                    self.sam_info['SAM_XY'] = np.float_(out.split(','))

                if "From guiding:" in value[2]:
                    out = value[2].split('ideal')[1:]
                    self.sam_info['XY_Idl'] = np.array([out[0].replace('Y',''),out[1]],dtype=np.float_)
                    self.sam_info['Guider'] = ((value[2].split('ideal')[0]).split('guider')[1]).replace('X','').strip()
                if "target location (v2, v3)" in value[2]:
                    out = value[2].split('=')[1]
                    for c in "()'":
                        out = out.replace(c,'')
                    self.sam_info['Target (v2,v3)'] = np.float_(out.split(','))

            if value[2][:6] == 'VISIT ':
                if value[2][-7:] == 'STARTED':
                    vstart = 'T'.join(value[0].split())[:-3]
                    vid = value[2].split()[1]

                    if vid==selected_visit_id:
                        in_selected_visit = True

                elif value[2][-5:] == 'ENDED' and in_selected_visit:
                    assert vid == value[2].split()[1]
                    assert selected_visit_id  == value[2].split()[1]

                    vend = 'T'.join(value[0].split())[:-3]
                    print(f"VISIT {selected_visit_id} END FOUND at {vend}")

                    in_selected_visit = False
            elif value[2][:31] == f'Script terminated: {vid}':
                if value[2][-5:] == 'ERROR':
                    script = value[2].split(':')[2]
                    vend = 'T'.join(value[0].split())[:-3]
                    dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                    note = f'Halt in {script}'
                    in_selected_visit = False


    def extract_oss_centroid(self, selected_visit_id, verbose=False):
        """Retrieve information about the TA object's centroid value

        Parameters
        ----------
        eventlog : list
            List of log entries. (Output from get_ictm_event_log())

        selected_visit_id : str
            ID of the visit containing the TA exposure. e.g. 'V01275004001'

        verbose : bool
            If True, print more information to the screen

        Returns
        -------

        """
        # parse response (ignoring header line) and print new event messages
        vid = ''
        in_selected_visit = False
        in_ta = False

        self.ta_info = {}

        if verbose:
            print(f"\tSearching for visit: {selected_visit_id}")
        for value in reader(self.eventlog, delimiter=',', quotechar='"'):
            if in_selected_visit and in_ta :
                if "postage-stamp coord (colCentroid, rowCentroid)" in value[2]:
                    out = value[2].split('=')[1]
                    for c in "()'":
                        out = out.replace(c,'')
                    self.ta_info["aperture_centroid"] = np.float_(out.split(','))

                if "detector coord (colCentroid, rowCentroid)" in value[2]:
                    out = value[2].split('=')[1]
                    for c in "()'":
                        out = out.replace(c,'')
                    self.ta_info["detector_centroid"] = np.float_(out.split(','))

                if "postage-stamp coord (colPeak, rowPeak)" in value[2]:
                    out = value[2].split('=')[1]
                    for c in "()'":
                        out = out.replace(c,'')
                    self.ta_info["peak_pixel"] = np.float_(out.split(','))

                if "(convergenceFlag, convergenceThres)" in value[2]:
                    out = value[2].split('=')[1]
                    for c in "()'":
                        out = out.replace(c,'')
                    convergence, conv_thresh = out.split(',')
                    self.ta_info["convergence"] = convergence
                    self.ta_info["conv_thresh"] = np.float_(conv_thresh)

                if "(total, numIter)" in value[2]:
                    out = value[2].split('=')[1]
                    for c in "()'":
                        out = out.replace(c,'')
                    self.ta_info["peak_signal"] = np.float_(out.split(',')[0])

                if "peakValue" in value[2]:
                    out = value[2].split('=')[1]
                    self.ta_info["peak_bkgd"] = np.float_(out)

            if value[2][:6] == 'VISIT ':
                if value[2][-7:] == 'STARTED':
                    vstart = 'T'.join(value[0].split())[:-3]
                    vid = value[2].split()[1]

                    if vid==selected_visit_id:
                        in_selected_visit = True

                elif value[2][-5:] == 'ENDED' and in_selected_visit:
                    assert vid == value[2].split()[1]
                    assert selected_visit_id  == value[2].split()[1]

                    vend = 'T'.join(value[0].split())[:-3]
                    in_selected_visit = False

            elif value[2][:31] == f'Script terminated: {vid}':
                if value[2][-5:] == 'ERROR':
                    script = value[2].split(':')[2]
                    vend = 'T'.join(value[0].split())[:-3]
                    dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                    note = f'Halt in {script}'
                    in_selected_visit = False
            elif in_selected_visit and value[2].startswith('*'): # this string is used to mark the start and end of TA sections
                in_ta = not in_ta

def main():
    """ Main function for command line arguments """
    parser = argparse.ArgumentParser(
        description='Get OSS ICTM Event Messages from Eng DB'
    )
    parser.add_argument('visit_id', type=str, help='Visit ID as a string starting with V i.e. "V01234003001"')
    parser.add_argument('-m', '--mast_api_token', help='MAST API token. Either set this parameter or define environment variable $MAST_API_TOKEN')
    parser.add_argument('-s', '--start_date', help='Start date for search, as YYYY-MM-DD. Defaults to 2022-02-02 if not set. ', default='2022-02-02')
    parser.add_argument('-e', '--end_date', help='End date for search, as YYYY-MM-DD. Defaults to today if not set. ', default='')
    parser.add_argument('-t', '--ta_only', action='store_true', help='Only show the Target Acquisition set of log messages')
    parser.add_argument('-v', '--verbose', action='store_true', help='Be more verbose for debugging')

    args = parser.parse_args()

    visit_info = EventLog(startdate=args.start_date, enddate=args.end_date, mast_api_token=args.mast_api_token, verbose=args.verbose)
    visit_info.extract_oss_event_msgs_for_visit(args.visit_id, ta_only=args.ta_only, verbose=args.verbose)


if __name__=="__main__":
    main()
