import os
import numpy as np
import argparse
from csv import reader
from datetime import datetime, timedelta, timezone
from getpass import getpass
from requests import Session
from time import sleep
import functools

import astropy.table, astropy.units as u
from jwql.instrument_monitors.common_monitors.ta_monitor import mast, utils

# See also https://jwst-pipeline.readthedocs.io/en/latest/jwst/lib/engdb.html
# for an alternative interface toolkit via the pipeline tools


@functools.lru_cache
def get_mnemonic(mnemonic, startdate='2022-02-01', enddate=None, mast_api_token=None, verbose=False,
                       return_as_table=True, change_only=True):
    """Retrieve a single mnemonic time series from the JWST Engineering database"""

    # constants
    base = 'https://mast.stsci.edu/jwst/api/v0.1/Download/file?uri=mast:jwstedb'
    mastfmt = '%Y%m%dT%H%M%S'
    millisec = timedelta(milliseconds=1)
    tz_utc = timezone(timedelta(hours=0))
    colhead = 'theTime'

    # establish MAST session
    session = Session()
     # set or interactively get mast token
    if not mast_api_token:
        mast_api_token = os.environ.get('MAST_API_TOKEN')
    if mast_api_token is not None:
        session.headers.update({'Authorization': f'token {mast_api_token}'})
    else:
        import warnings
        warnings.warn("Must define MAST_API_TOKEN env variable or specify mast_api_token parameter to access proprietary data")

    # Handle dates as astropy.Time, datetime, or strings
    if isinstance(startdate, astropy.time.Time):
        start = startdate
    elif startdate is None:
        raise ValueError("Start date should not be None when calling get_mnemonic")
    else:
        start = datetime.fromisoformat(f'{startdate}+00:00')

    if enddate is None:
        end = datetime.now(tz=tz_utc)
    elif isinstance(enddate, astropy.time.Time):
        end = enddate
    else:
        end = datetime.fromisoformat(f'{enddate}+23:59:59')

    # fetch event messages from MAST engineering database (lags FOS EDB)

    startstr = start.strftime(mastfmt)
    endstr = end.strftime(mastfmt)
    filename = f'{mnemonic}-{startstr}-{endstr}.csv'
    url = f'{base}/{filename}'

    if verbose:
        print(f"Retrieving {url}")
    response = session.get(url)
    if response.status_code == 401:
        exit('HTTPError 401 - Check your MAST token and EDB authorization. May need to refresh your token if it expired.')
    response.raise_for_status()
    lines = response.content.decode('utf-8').splitlines()

    if return_as_table:
        table =  parse_eventlog_to_table(lines, label=mnemonic)
        if change_only:
            table = mnemonic_get_changes(table)
        return table
    else:
        return lines

def mnemonic_get_changes(table):
    """Trim a mnemonic table down to just the distinct rows when the value changes"""
    prev = None
    change_indices = []
    vals = table.columns[-1]
    for i in range(len(table)):
        if vals[i] != prev:
            prev = vals[i]
            change_indices.append(i)
    return table[change_indices]


@functools.lru_cache
def get_ictm_event_log(startdate='2022-02-01', enddate=None, mast_api_token=None, verbose=False,
                       return_as_table=True):

    # parameters
    mnemonic = 'ICTM_EVENT_MSG'

    lines = get_mnemonic(mnemonic, startdate=startdate, enddate=enddate, mast_api_token=mast_api_token,
                         verbose=verbose, return_as_table=False)

    if return_as_table:
        return parse_eventlog_to_table(lines, label='Message')
    else:
        return lines

#----- Newer/updated version of OSS log message retrieval,
#      using the pipeline interface and retrieving additional fields

@functools.lru_cache
def get_oss_log_messages(visitid=None, start_time=None, end_time=None):
    """ Retrieve OSS event log messages during a given visit or time interval

    See also get_ictm_event_log. This function instead uses the EngDB interface included in the JWST pipeline.
    Returns an astropy Table with the EngDB message, message ID, and message source.

    Parameters
    ----------
    visitid : str
        Visit ID string, like 'V01234001001'

    Returns astropy Table containing the timestamps and message values
    """
    if start_time is None and end_time is None:
        visitid = utils.get_visitid(visitid)  # Handle either allowed format of visit ID

        #----- When was that visit? -----
        start_time, end_time = mast.query_visit_time(visitid)
        if start_time is None:
            raise RuntimeError(f"Cannot find start time for visit {visitid}. That visit may not have happened yet.")
    else:
        start_time = astropy.time.Time(start_time)
        end_time = astropy.time.Time(end_time)

    #----- Retrieve relevant messages from the ICTM event log stream -----
    from jwst.lib.engdb_tools import ENGDB_Service
    service = ENGDB_Service()  # By default, will use the public MAST service.

    # There are multiple mnemonics we care about,
    # in particular the EVENT_MSG has the text, and the MSG_ID and MSG_SRC give metadata on the source
    # Retrieve all of these and organize into a table for convenience.

    msg_times, messages = service.get_values("ICTM_EVENT_MSG", start_time.isot, end_time.isot, include_obstime=True, zip_results=False)
    msg_times_2, msg_ids = service.get_values("ICTM_EVENT_MSG_ID", start_time.isot, end_time.isot, include_obstime=True, zip_results=False)
    msg_times_3, msg_srcs = service.get_values("ICTM_EVENT_MSG_SRC", start_time.isot, end_time.isot, include_obstime=True, zip_results=False)

    #----- Arrange those 3 sets of results into a single Table -----
    # Ideally we should have gotten the same number of rows in all 3 queries above\
    # These -should- all have matching counts and time stamps... but for some reason this is not always the case. Hmm.
    # So check here and if necessary handle the case of an inconsistency.

    if len(messages) == len(msg_ids) and len(messages) == len(msg_srcs):
        #print("consistent number of rows returned")
        msg_table = astropy.table.Table([msg_times, messages, msg_ids, msg_srcs],
                                       names = ['TIME', "EVENT_MSG", "EVENT_MSG_ID", "EVENT_MSG_SRC"])
    else:
        print("INconsistent number of EVENT_MSG and EVENT_MSG_ID records returned; matching based on telemetry time stamps ")
        # This occurs for instance in visit V07344017001, a NIRCam WFSC visit.

        msg_table = astropy.table.Table([msg_times[0:1], messages[0:1], msg_ids[0:1], msg_srcs[0:1]],
                           names = ['TIME', "EVENT_MSG", "EVENT_MSG_ID", "EVENT_MSG_SRC"])
        # match up the rows that do have consistent timestamps
        # When there's not a match, look 1 row before or after to see if we can find a match
        n = min(len(msg_times), len(msg_times_2), len(msg_times_3))
        index_offset = 0  # We will use this to track offsets between mnemonic time series
        for i in range(1, n):
            # Compare time stamps between EVENT_MSG and EVENT_MSG_ID mnemonic time series
            if msg_times[i] - msg_times_2[i+index_offset] == 0*u.second:
                # times match, no need to adjust
                pass
            else:
                if msg_times[i] == msg_times_2[i+index_offset-1]:
                    #print('found extra EVENT_MSG relative to EVENT_MSG_ID')
                    index_offset -= 1
                elif msg_times[i] == msg_times_2[i+index_offset+1]:
                    #print('found skipped EVENT_MSG relative to EVENT_MSG_ID')
                    index_offset += 1
                else:
                    raise RuntimeError("Inconsistent number of telemetry records returned, with bigger gaps than this function can currently sort out.")
            msg_table.add_row([msg_times[i], messages[i], msg_ids[i+index_offset], msg_srcs[i+index_offset]])

    return msg_table


def filter_oss_log_messages_by_id(msg_table, msg_id):
    """Select a subset of event log messages matching a specified EVENT_MSG_ID

    Parameters
    ----------
    msg_table : astropy.Table
        table returned from get_oss_log_messages()
    msg_id : int
        Value to select from the EVENT_MSG_ID field in that table.

    Returns a subset of rows from the event message table
    """
    return msg_table[msg_table['EVENT_MSG_ID'] == msg_id]


#-------

def pretty_print_event_log(eventlog):
    # Only works on eventtable as list; unnecessary for Table format
    for value in reader(eventlog, delimiter=',', quotechar='"'):
        print(f"{value[0][0:22]:20s}\t {value[2]}")


def _check_log_and_note_issues(msg, prior_note=None):
    """ Check messages to detect issues we should flag for the user to be aware of

    """
    # check for visit guide failures
    if 'FGS fixed target guide star acquisition failed on all attempts, exit FGSVERMAIN' in msg:
        #print(f"FGS ID+Acq failed on all attempts for {vid}")
        note = "SKIPPED. FGS ID failed all attempts"
    elif 'FGS guide star reacquisition failed' in msg:
        note = 'FAILED part way through: FGS guide star reacquisition failed.'
    elif 'FGS loss of ACS Fine Guidance Control, exit FGSGUIDEHEALTH' in msg:
        note = 'FAILED part way through: FGS loss of ACS fine guide control'
    elif 'FGS MT guide star acquisition process unsuccessful' in msg:
        note = 'FAILED guide star acquisition for moving target'
    elif 'MIRI target locate failed' in msg:
        note = 'MIRI target acq failed'
    elif 'NIRCam target locate failed' in msg or 'NRC target locate failed' in msg:
        note = 'NIRCam target acq failed'
    elif ('NIRSpec TA Roll too big' in msg) or ('NIRSpec TA Roll too large' in msg):
        note = "NIRSpec MSATA failed; roll too large"
    elif 'subsystem unavailable' in msg:  # This checks for like 'NRC subsystem unavailable'
        note = msg.split(',')[0]
    elif 'Visit constraint violation' in msg:  # This may follow a subsystem unavailable
        note = msg
        if prior_note is not None:
            note = note + ". " + prior_note
    elif 'GENRTVSTMAIN' in msg:
        note = "Realtime Commanding Visit. "
    else:
        note = None

    return note


def visit_start_end_times(eventlog, visitid=None, return_table=False, verbose=True):
    """ Find visit start and end times for all visits

    Note, 'visitstart' is the start time of the SLEW before a visit.
    'visit_fgs_start' gives the time of when the FGSMAIN ID/Acq/Track/FG began;
      this corresponds to the start time column in the public schedule on stsci.edu

    Parameters
    ----------
    return_table : bool
        Return astropy table of the outputs


    """
    # parse response (ignoring header line) and print new event messages
    vid = ''
    in_visit = False
    in_selected_visit = False
    in_parallel_list = False

    outputs = {k: [] for k in ['visitid', 'visitstart', 'visit_fgs_start', 'visitend', 'duration', 'parallels', 'notes']}

    output = []
    output.append('Visit ID     | Visit Start             | Visit End'
                  '               | Duration |')
    for row in eventlog:
        msg, time = row['Message'], row['Time']
        if msg[:6] == 'VISIT ':
            if msg[-7:] == 'STARTED':
                if in_visit == True:
                    output.append(f'*** Missing end for visit {vid}')
                vstart = 'T'.join(time.split())[:-3]
                vid = msg.split()[1]
                vid_fgs_start = None
                current_visit_parallels = []

                # for debugging:
                #print("**", value)
                in_visit = True
                note = ""
            elif ((msg[-5:] == 'ENDED' and vid!='')  # Normal visit end log message
                  or (msg[-28:] == 'ENDED, EXCEEDED ALLOWED TIME' and vid!='')):
                if vid != msg.split()[1]:
                    output.append(f"Unexpected end for visit {msg} instead of {vid}")
                if msg.endswith('ENDED, EXCEEDED ALLOWED TIME'):
                    output.append("Visit TERMINATED; Exceeded allowed time.")
                    note += "ERROR: Terminated by OSS; Exceeded allowed time."
                vend = 'T'.join(time.split())[:-3]
                dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                output.append(f'{vid} | {vstart:23} | {vend:23} | '
                      f' {round(dur.total_seconds()):6}  | {note}')
                outputs['visitid'].append(vid)
                outputs['visitstart'].append(vstart)
                outputs['visit_fgs_start'].append(str(vid_fgs_start))
                outputs['visitend'].append(vend)
                outputs['duration'].append(dur.total_seconds())
                outputs['parallels'].append(current_visit_parallels)
                outputs['notes'].append(note)

                in_visit = False
            elif msg.endswith('SKIPPED'):  # Visit latest allowed start time has passed, so it gets skipped.
                # Still include this in the table, but with start and end time exactly the same
                vstart = 'T'.join(time.split())[:-3]
                vend = vstart
                vid = msg.split()[1]
                vid_fgs_start = None
                current_visit_parallels = []
                note = msg[21:]+"."  # drop 'VISIT V01234005006 -' from the start, keep the rest
                dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                output.append(f'{vid} | {vstart:23} | {vend:23} | '
                      f' {round(dur.total_seconds()):6}  | {note}')
                outputs['visitid'].append(vid)
                outputs['visitstart'].append(vstart)
                outputs['visit_fgs_start'].append(str(vid_fgs_start))
                outputs['visitend'].append(vend)
                outputs['duration'].append(dur.total_seconds())
                outputs['parallels'].append(current_visit_parallels)
                outputs['notes'].append(note)
        elif msg[:31] == f'Script terminated: {vid}':
            if msg[-5:] == 'ERROR':
                script = msg.split(':')[2]
                vend = 'T'.join(time.split())[:-3]
                dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                note = f'Error in {script}'
                output.append(f'{vid} | {vstart:23} | {vend:23} | '
                      f' {round(dur.total_seconds()):6}  | {note}')
                in_visit = False
        else:
            if in_visit:
                alert_note = _check_log_and_note_issues(msg, note)
                if alert_note:
                    note = alert_note
                if (vid_fgs_start is None) and ('Script activated' in msg) and (msg.endswith('FGSMAIN') or msg.endswith('FGSMTMAIN')):
                    vid_fgs_start = 'T'.join(time.split())[:-3]
                    if msg.endswith('FGSMTMAIN'):
                        note = "[Moving Target] " if note == '' else note + " [Moving Target] "
                if 'contains the following Parallel IDs' in msg:
                    in_parallel_list = True
                elif in_parallel_list:
                    current_visit_parallels = msg.split()
                    in_parallel_list = False
    else:
        if in_visit:
            output.append(f'{vid} | {vstart:23} | ongoing            | '
                  f' ongoing  | as of end of log')
            outputs['visitid'].append(vid)
            outputs['visitstart'].append(vstart)
            outputs['visit_fgs_start'].append(str(vid_fgs_start))
            outputs['visitend'].append('T'.join(time.split())[:-3])
            outputs['duration'].append(-1)
            outputs['parallels'].append(current_visit_parallels)
            note += 'Still ongoing at end of available log.'
            outputs['notes'].append(note )





    if visitid and verbose:
        print(output[0])
        visitid_std = utils.get_visitid(visitid)  # handle either possible input format
        for row in output:
            if visitid_std in row:
                print(row)
    elif verbose:
        for row in output:
            print(row)

    if return_table:
        t = astropy.table.Table(list(outputs.values()), names = outputs.keys() )
        t["notes"] = t["notes"].astype("<U100")  # ensure we can stick in quite long text notes, if needed
        t['visitstart'] = astropy.time.Time(t['visitstart'])
        t['visitend'] = astropy.time.Time(t['visitend'])
        try:
            t['visit_fgs_start'] = astropy.time.Time(t['visit_fgs_start'])
        except ValueError:
            # Gracefully handle edge case, in which there may be gaps in telemetry or visits without guiding
            # This is imperfect, but in this case just swap in the visit start time for the guiding start time as a placeholder,
            # so at least the code doesn't hard stop with an exception.
            for i in range(len(t)):
                if t[i]['visit_fgs_start'] is None or t[i]['visit_fgs_start']=='None':
                    # swap in the visit script start time in place of FGS start, since it's all we have
                    t[i]['visit_fgs_start'] = t[i]['visitstart'].isot
                    # print a note to let the user know -- but don't do this if there is already a note of
                    # some issue with the visit, such that it halted before taking FGSMAIN.
                    if 'visit halted' not in t[i]['notes'] and verbose:
                        print(f'could not find FGSMAIN start time in log for visit {t[i]["visitid"]}')
                    # Mark if no FGSMAIN found, except if it's a kind of visit for which we don't expect guiding.
                    if 'Realtime' not in t[i]['notes']:
                        t[i]['notes'] = t[i]['notes'] + " No FGSMAIN start time in log."
            t['visit_fgs_start'] = astropy.time.Time(t['visit_fgs_start'])

        return(t)


def extract_oss_event_msgs_for_visit(eventlog, selected_visit_id, ta_only=False, verbose=False, return_text=True):
    # parse response (ignoring header line) and print new event messages
    vid = ''
    in_selected_visit = False
    in_ta = False
    selected_visit_id = utils.get_visitid(selected_visit_id)  # handle either input format

    messages = []
    if verbose:
        print(f"\tSearching for visit: {selected_visit_id}")
    for row in eventlog:
        msg, time = row['Message'], row['Time']

        if in_selected_visit and ((not ta_only) or in_ta) :
            if verbose:
                print(time[0:22], "\t", msg)
            if return_text:
                messages.append(time[0:22]+ "\t" + msg)

        if msg[:6] == 'VISIT ':
            if msg[-7:] == 'STARTED':
                vstart = 'T'.join(time.split())[:-3]
                vid = msg.split()[1]

                if vid==selected_visit_id:
                    if verbose:
                        print(f"VISIT {selected_visit_id} START FOUND at {vstart}")
                    in_selected_visit = True
                    if ta_only and verbose:
                        print("Only displaying TARGET ACQUISITION RESULTS:")

            elif msg[-5:] == 'ENDED' and in_selected_visit:
                assert vid == msg.split()[1]
                assert selected_visit_id  == msg.split()[1]

                vend = 'T'.join(time.split())[:-3]
                if verbose:
                    print(f"VISIT {selected_visit_id} END FOUND at {vend}")


                in_selected_visit = False
        elif msg[:31] == f'Script terminated: {vid}':
            if msg[-5:] == 'ERROR':
                script = msg.split(':')[2]
                vend = 'T'.join(time.split())[:-3]
                dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                note = f'Halt in {script}'
                in_selected_visit = False
        elif in_selected_visit and msg.startswith('*'): # this string is used to mark the start and end of TA sections
            in_ta = not in_ta

    if return_text:
        return messages


def extract_oss_TA_centroids(eventlog, selected_visit_id):
    """ Return the TA centroid values from OSS
    Note, pretty sure these values from OSS are 1-based pixel coordinates - to be confirmed!

    returns (X,Y) tuple
    """

    msgs = extract_oss_event_msgs_for_visit(eventlog, selected_visit_id,
                                            ta_only=True,
                                            verbose=False, return_text=True)
    for m in msgs:
        if m.split('\t')[1].startswith("detector coord"):
            xy = ([float(p.strip('(),')) for p in m.split()[-2:]])
            return tuple(xy)
    else:
        raise RuntimeError("Could not parse TA centroid coordinates in that visit log")


# Old/obsolete dev code. To be deleted once it's confirmed we don't need any of this:
#
# def extract_oss_TA_SAM(eventlog, selected_visit_id, verbose=False):
#     """ Return the TA SAM values from OSS
#
#     returns (X,Y) tuple
#
#     Examples of what the logs can look like for this:
# ---NIRSpec WATA---
# 2022-11-16 17:52:54.21 	 NIRSpec TA offset vehicle slew calc and SAM
# 2022-11-16 17:52:56.26 	 From guiding: guider 1 X ideal -24.5140000 Y ideal -31.6730000
# 2022-11-16 17:52:57.28 	 target location (v2, v3)                           = (321.376298, -474.149793)
# 2022-11-16 17:52:58.30 	 TA SAM for NRS (x, y) = -0.106834449, 0.300889673
#     """
#
#     msgs = extract_oss_event_msgs_for_visit(eventlog, selected_visit_id,
#                                             ta_only=False,  # note, the SAM happens after the TA analysis block
#                                             verbose=False, return_text=True)
#     for m in msgs:
#         if verbose:
#             print(m)
#         # first find which detector is used for TA
#         if m.split('\t')[1].startswith("DETECTOR"):
#             ta_detector = m.split()[-1]
#
#         if m.split('\t')[1].startswith("TA SAM"):
#             print("Found TA SAM message:", m)
#             print("      for TA using:  ", ta_detector)
#             if ta_detector in ['NRS1']:
#                 xy = ([float(p.strip('(),')) for p in m.split()[-2:]])
#                 return tuple(xy)
#             elif ta_detector.startswith("NRCA") or ta_detector == 'NIS' or ta_detector.startswith('MIRI'):
#                 # like "TA SAM (x, y) = 0.0342236531, -0.0112909576"
#                 xy = [float(p.strip(',')) for p in m.split()[-2:]]
#                 return tuple(xy)
#
#             # TODO determine how to handle other TA modes for this
#     else:
#         raise RuntimeError(f"Could not parse TA centroid coordinates in that visit log for {selected_visit_id}")
#
#
#
# def get_nrs_ta_sam():
#
#     """ OSS logs hav text like:
# 2022-11-16 17:52:56.26 	 From guiding: guider 1 X ideal -24.5140000 Y ideal -31.6730000
# 2022-11-16 17:52:57.28 	 target location (v2, v3)                           = (321.376298, -474.149793)
# 2022-11-16 17:52:58.30 	 TA SAM for NRS (x, y) = -0.106834449, 0.300889673
# """
#
#

def parse_eventlog_to_table(eventlog, label=None):
    """Parse an eventlog as returned from the EngDB to an astropy table, for ease of use

    """

    if label is None:
        label = "Value"
    timestr = []
    mjd = []
    messages = []
    for value in reader(eventlog, delimiter=',', quotechar='"'):
        timestr.append(value[0])
        mjd.append(value[1])
        messages.append(value[2])

    # drop initial header row
    timestr = timestr[1:]
    mjd = np.asarray(mjd[1:], float)
    messages = messages[1:]

    try:
        messages = np.asarray(messages, float)
    except ValueError:
        pass # it's string type so leave it as string

    # assemble into astropy table
    event_table = astropy.table.Table((timestr, mjd, messages),
                                      names=("Time", "MJD", label))
    return event_table


def eventtable_extract_visit(event_table, selected_visit_id, verbose=False):
    """Find just the log message rows for a given visit"""
    visit_id = utils.get_visitid(selected_visit_id)  # handle either input format

    vmessages = [m.startswith(f'VISIT {visit_id}') for m in event_table['Message']]

    if verbose:
        print(event_table[vmessages])

    line_indices = np.where(vmessages)[0]
    if len(line_indices) == 0:
        raise RuntimeError(f"No messages were found for visit {visit_id} within the search time period.")
    elif len(line_indices) == 2:
        istart, istop = line_indices
        return event_table[istart:istop+1]
    else: # visit ongoing, has not ended as of end of available log
        istart = line_indices[0]
        return event_table[istart:]


def visit_script_durations(event_table, selected_visit_id, verbose=True, return_table=False):
    visittable = eventtable_extract_visit(event_table, selected_visit_id)



    scriptevents = visittable[ [msg.startswith('Script') for msg in visittable['Message']]]


    total_visit_duration = visittable[-1]['MJD'] - visittable[0]['MJD']


    summary_durations = dict()

    def vprint(*args):
        if verbose: print(*args)

#    scriptevents = eventtable_extract_scripts(event_table, selected_visit_id)

    vprint(f"OSS Script Durations for {selected_visit_id} (total duration: {total_visit_duration*86400:.1f} s)")

    starts = dict()
    stops = dict()
    for row in scriptevents:
        if row['Message'].startswith("Script activated: "):
            key = row['Message'].split()[2]
            starts[key] = row['MJD']
        elif row['Message'].startswith("Script terminated: "):
            key = row['Message'].split()[2]

            keyparts = key.split(":")
            # Some terminate messages have extra statuses appended at the end.
            # Drop these, so the keys match up with the activate messages
            if len(keyparts) > 2:
                key = ":".join(keyparts[0:2])

            stops[key] = row['MJD']

    cumulative_time = 0

    sci_plus_overheads = 'Science + inst. overheads'

    for key in starts:
        deltatime = stops[key]-starts[key]
        vprint(f"  {key:50s}{deltatime*86400:6.1f} s")
        cumulative_time += deltatime
        activity_id, script = key.split(":")

        #summarize into categories: slews, FGS, TA, science obs
        if script=='SCSLEWMAIN':
            category='Slew'
        elif script in ['FGSMAIN', 'FGSMTMAIN']:
            category='FGS'
        elif 'TA' in script:
            category='TA'
        elif script[0:3] in ['NRC','NIS','NRS','MIR']:
            category = 'Parallel' if ('P' in activity_id and not activity_id.split('P')[1].startswith('00000')) else sci_plus_overheads
        elif 'WAIT' in script:
            category = 'Wait'
        else:
            category='Other'

        summary_durations[category] = summary_durations.get(category,0) + deltatime


    cumulative_time -= summary_durations.get('Parallel', 0)  # Parallels do not add to total time, by construction
    vprint(f"  Other overheads not included in the above:        {(total_visit_duration-cumulative_time)*86400:6.1f} s")
    summary_durations['Other'] += (total_visit_duration-cumulative_time)

    vprint("\nSummary by category:")
    label='Visit total'
    vprint(f"\t{label:25s}\t{total_visit_duration*86400:6.1f} s")

    categories = ['Slew', 'FGS', 'Wait', 'TA', sci_plus_overheads, 'Other']
    if 'Parallel' in summary_durations:
        categories.insert(4, 'Parallel')

    parts = []
    for category in categories:
        label=category+":"
        if category not in summary_durations: # Skip if e.g. there's no TA in this visit
            parts.append(0)
            continue
        parts.append(summary_durations[category]*86400)
        vprint(f"\t{label:30s}\t{summary_durations[category]*86400:7.1f} s")
    vprint("\n")

    if return_table:
        t = astropy.table.Table([categories, parts], names = ['category', 'duration'])
        return(t)


#############################################
def main_combined():
    """ Main function for command line arguments """
    parser = argparse.ArgumentParser(
        description='Query OSS Visit Logs from JWST MAST Engineering DB'
    )
    parser.add_argument('-m', '--mast_api_token', help='MAST API token. Either set this parameter or define environment variable $MAST_API_TOKEN')
    parser.add_argument('-s', '--start_date', help='Start date for search, as YYYY-MM-DD. Defaults to 2022-07-12 if not set. ', default='2022-07-12')
    parser.add_argument('-e', '--end_date', help='End date for search, as YYYY-MM-DD. Defaults to current date if not set. ')
    parser.add_argument('-v', '--verbose', action='store_true', help='Be more verbose for debugging')
    parser.add_argument('-f', '--full', action='store_true', help='Retrieve Full OSS log for all completed visits')
    parser.add_argument('-m', '--messages', action='store_true', help='Retrieve OSS Messages for the specified visit')
    parser.add_argument('-d', '--durations', action='store_true', help='Retrieve event durations for the specified visit')
    parser.add_argument('-t', '--ta_only', action='store_true', help='For messages, only show the Target Acquisition set of log messages')
    parser.add_argument('-v', '--verbose', action='store_true', help='Be more verbose for debugging')


    args = parser.parse_args()


    eventlog = get_ictm_event_log(mast_api_token=args.mast_api_token, verbose=args.verbose,
                                  startdate=args.start_date, enddate=args.enddate)

    if args.full:
        pretty_print_event_log(eventlog)

    elif args.durations:
        event_table = eventlog_parse_to_table(eventlog)

        visit_script_durations(event_table, args.visit_id)


def main_full():
    """ Main function for command line arguments """
    parser = argparse.ArgumentParser(
        description='Get OSS ICTM Event Messages from Eng DB'
    )
    parser.add_argument('-m', '--mast_api_token', help='MAST API token. Either set this parameter or define environment variable $MAST_API_TOKEN')
    parser.add_argument('-s', '--start_date', help='Start date for search, as YYYY-MM-DD. Defaults to 2022-02-02 if not set. ', default='2022-02-02')
    parser.add_argument('-v', '--verbose', action='store_true', help='Be more verbose for debugging')

    args = parser.parse_args()


    eventlog = get_ictm_event_log(mast_api_token=args.mast_api_token, verbose=args.verbose, startdate=args.start_date)
    pretty_print_event_log(eventlog)


def main_oss_msgs():
    """ Main function for command line arguments """
    parser = argparse.ArgumentParser(
        description='Get OSS ICTM Event Messages from Eng DB'
    )
    parser.add_argument('visit_id', type=str, help='Visit ID as a string starting with V i.e. "V01234003001"')
    parser.add_argument('-m', '--mast_api_token', help='MAST API token. Either set this parameter or define environment variable $MAST_API_TOKEN')
    parser.add_argument('-s', '--start_date', help='Start date for search, as YYYY-MM-DD. Defaults to 2022-02-02 if not set. ', default='2022-02-02')
    parser.add_argument('-t', '--ta_only', action='store_true', help='Only show the Target Acquisition set of log messages')
    parser.add_argument('-v', '--verbose', action='store_true', help='Be more verbose for debugging')

    args = parser.parse_args()


    eventlog = get_ictm_event_log(mast_api_token=args.mast_api_token, verbose=args.verbose, startdate=args.start_date)

    extract_oss_event_msgs_for_visit(eventlog,  args.visit_id, verbose=args.verbose, ta_only=args.ta_only)


def main_visit_events():
    """ Main function for command line arguments """
    parser = argparse.ArgumentParser(
        description='Get OSS Event Durations from Eng DB'
    )
    parser.add_argument('visit_id', type=str, help='Visit ID as a string starting with V i.e. "V01234003001"')
    parser.add_argument('-m', '--mast_api_token', help='MAST API token. Either set this parameter or define environment variable $MAST_API_TOKEN')
    parser.add_argument('-s', '--start_date', help='Start date for search, as YYYY-MM-DD. Defaults to 2022-02-02 if not set. ', default='2022-02-02')
    parser.add_argument('-v', '--verbose', action='store_true', help='Be more verbose for debugging')

    args = parser.parse_args()


    eventlog = get_ictm_event_log(mast_api_token=args.mast_api_token, verbose=args.verbose, startdate=args.start_date)
    event_table = eventlog_parse_to_table(eventlog)

    visit_script_durations(event_table, args.visit_id)

if __name__=="__main__":
    main()



