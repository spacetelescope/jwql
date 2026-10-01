from csv import reader
from datetime import datetime, timedelta, timezone
import os
from requests import Session
import logging

import astropy
import numpy as np

from support_ta_monitor_mast import query_visit_time
from support_ta_monitor_utils import get_visitid


def get_visitid(visitstr):
    """Common util function to handle several various kinds of visit specification"""
    if visitstr.startswith("V"):
        # Full visit ID like V04503031001
        return visitstr
    elif ":" in visitstr:
        # This is PPS format visit ID, like 4503:31:1
        parts = [int(p) for p in visitstr.split(":")]
        if len(parts) == 2:
            # if given only like 4503:31, assume the visit number is 1
            parts.append(1)
        return f"V{parts[0]:05d}{parts[1]:03d}{parts[2]:03d}"
    elif len(visitstr) == 11:
        # Full visit ID but without the leading V, like 04503031001
        return "V" + visitstr


def extract_oss_event_msgs_for_visit(
    eventlog, selected_visit_id, ta_only=False, verbose=False, return_text=True
):
    vid = ""
    in_selected_visit = False
    in_ta = False
    selected_visit_id = get_visitid(selected_visit_id)  # handle either input format

    messages = []
    if verbose:
        logging.debug(f"\tSearching for visit: {selected_visit_id}")
    for row in eventlog:
        msg, time = row["Message"], row["Time"]

        if in_selected_visit and ((not ta_only) or in_ta):
            if verbose:
                logging.debug(f"{time[0:22]}\tmsg")
            if return_text:
                messages.append(time[0:22] + "\t" + msg)

        if msg[:6] == "VISIT ":
            if msg[-7:] == "STARTED":
                vstart = "T".join(time.split())[:-3]
                vid = msg.split()[1]

                if vid == selected_visit_id:
                    if verbose:
                        logging.debug(f"VISIT {selected_visit_id} START FOUND at {vstart}")
                    in_selected_visit = True
                    if ta_only and verbose:
                        logging.debug("Only displaying TARGET ACQUISITION RESULTS:")

            elif msg[-5:] == "ENDED" and in_selected_visit:
                assert vid == msg.split()[1]
                assert selected_visit_id == msg.split()[1]

                vend = "T".join(time.split())[:-3]
                if verbose:
                    logging.debug(f"VISIT {selected_visit_id} END FOUND at {vend}")

                in_selected_visit = False
        elif msg[:31] == f"Script terminated: {vid}":
            if msg[-5:] == "ERROR":
                script = msg.split(":")[2]
                vend = "T".join(time.split())[:-3]
                dur = datetime.fromisoformat(vend) - datetime.fromisoformat(vstart)
                note = f"Halt in {script}"
                in_selected_visit = False
        elif in_selected_visit and msg.startswith(
            "*"
        ):  # this string is used to mark the start and end of TA sections
            in_ta = not in_ta

    if return_text:
        return messages


def parse_eventlog_to_table(eventlog, label=None):
    """Parse an eventlog as returned from the EngDB to an astropy table, for ease of use"""

    if label is None:
        label = "Value"
    timestr = []
    mjd = []
    messages = []
    for value in reader(eventlog, delimiter=",", quotechar='"'):
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
        pass  # it's string type so leave it as string

    # assemble into astropy table
    event_table = astropy.table.Table(
        (timestr, mjd, messages), names=("Time", "MJD", label)
    )
    return event_table


def get_mnemonic(
    mnemonic,
    startdate="2022-02-01",
    enddate=None,
    mast_api_token=None,
    verbose=False,
    return_as_table=True,
    change_only=True,
):
    """Retrieve a single mnemonic time series from the JWST Engineering database"""

    # constants
    base = "https://mast.stsci.edu/jwst/api/v0.1/Download/file?uri=mast:jwstedb"
    mastfmt = "%Y%m%dT%H%M%S"
    millisec = timedelta(milliseconds=1)
    tz_utc = timezone(timedelta(hours=0))
    colhead = "theTime"

    # establish MAST session
    session = Session()
    # set or interactively get mast token
    if not mast_api_token:
        mast_api_token = os.environ.get("MAST_API_TOKEN")
    if mast_api_token is not None:
        session.headers.update({"Authorization": f"token {mast_api_token}"})
    else:
        import warnings

        warnings.warn(
            "Must define MAST_API_TOKEN env variable or specify mast_api_token parameter to access proprietary data"
        )

    # Handle dates as astropy.Time, datetime, or strings
    if isinstance(startdate, astropy.time.Time):
        start = startdate
    elif startdate is None:
        raise ValueError("Start date should not be None when calling get_mnemonic")
    else:
        start = datetime.fromisoformat(f"{startdate}+00:00")

    if enddate is None:
        end = datetime.now(tz=tz_utc)
    elif isinstance(enddate, astropy.time.Time):
        end = enddate
    else:
        end = datetime.fromisoformat(f"{enddate}+23:59:59")

    # fetch event messages from MAST engineering database (lags FOS EDB)

    startstr = start.strftime(mastfmt)
    endstr = end.strftime(mastfmt)
    filename = f"{mnemonic}-{startstr}-{endstr}.csv"
    url = f"{base}/{filename}"

    if verbose:
        logging.debug(f"Retrieving {url}")
    response = session.get(url)
    if response.status_code == 401:
        exit(
            "HTTPError 401 - Check your MAST token and EDB authorization. May need to refresh your token if it expired."
        )
    response.raise_for_status()
    lines = response.content.decode("utf-8").splitlines()

    if return_as_table:
        table = parse_eventlog_to_table(lines, label=mnemonic)
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


def get_ictm_event_log(
    startdate="2022-02-01",
    enddate=None,
    mast_api_token=None,
    verbose=False,
    return_as_table=True,
):
    # parameters
    mnemonic = "ICTM_EVENT_MSG"

    lines = get_mnemonic(
        mnemonic,
        startdate=startdate,
        enddate=enddate,
        mast_api_token=mast_api_token,
        verbose=verbose,
        return_as_table=False,
    )

    if return_as_table:
        return parse_eventlog_to_table(lines, label="Message")
    else:
        return lines


def eventtable_extract_visit(event_table, selected_visit_id, verbose=False):
    """Find just the log message rows for a given visit"""
    visit_id = get_visitid(selected_visit_id)  # handle either input format

    vmessages = [m.startswith(f'VISIT {visit_id}') for m in event_table['Message']]

    if verbose:
        logging.debug(event_table[vmessages])

    line_indices = np.where(vmessages)[0]
    if len(line_indices) == 0:
        raise RuntimeError(f"No messages were found for visit {visit_id} within the search time period.")
    elif len(line_indices) == 2:
        istart, istop = line_indices
        return event_table[istart:istop+1]
    else: # visit ongoing, has not ended as of end of available log
        istart = line_indices[0]
        return event_table[istart:]


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
        visitid = get_visitid(visitid)  # Handle either allowed format of visit ID

        #----- When was that visit? -----
        start_time, end_time = query_visit_time(visitid)
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
        msg_table = astropy.table.Table([msg_times, messages, msg_ids, msg_srcs],
                                       names = ['TIME', "EVENT_MSG", "EVENT_MSG_ID", "EVENT_MSG_SRC"])
    else:
        logging.debug("INconsistent number of EVENT_MSG and EVENT_MSG_ID records returned; matching based on telemetry time stamps ")
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
                    index_offset -= 1
                elif msg_times[i] == msg_times_2[i+index_offset+1]:
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


def check_log_and_note_issues(msg):
    """ 
    Check messages to detect issues we should flag for the user to be aware of
    """
    # check for visit guide failures
    if 'FGS fixed target guide star acquisition failed on all attempts, exit FGSVERMAIN' in msg:
        note = "SKIPPED. FGS ID failed all attempts"
    elif 'FGS guide star reacquisition failed' in msg:
        note = 'FAILED part way through: FGS guide star reacquisition failed.'
    elif 'FGS Track unsuccessful on all attempts' in msg:
        note = f"{msg[23:]}."
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
    elif 'GENRTVSTMAIN' in msg:
        note = "Realtime Commanding Visit. "
    else:
        note = None

    return note
