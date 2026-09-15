from csv import reader
from datetime import datetime, timedelta, timezone
import os
from requests import Session

import astropy
import numpy as np


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
    # parse response (ignoring header line) and print new event messages
    vid = ""
    in_selected_visit = False
    in_ta = False
    selected_visit_id = get_visitid(selected_visit_id)  # handle either input format

    messages = []
    if verbose:
        print(f"\tSearching for visit: {selected_visit_id}")
    for row in eventlog:
        msg, time = row["Message"], row["Time"]

        if in_selected_visit and ((not ta_only) or in_ta):
            if verbose:
                print(time[0:22], "\t", msg)
            if return_text:
                messages.append(time[0:22] + "\t" + msg)

        if msg[:6] == "VISIT ":
            if msg[-7:] == "STARTED":
                vstart = "T".join(time.split())[:-3]
                vid = msg.split()[1]

                if vid == selected_visit_id:
                    if verbose:
                        print(f"VISIT {selected_visit_id} START FOUND at {vstart}")
                    in_selected_visit = True
                    if ta_only and verbose:
                        print("Only displaying TARGET ACQUISITION RESULTS:")

            elif msg[-5:] == "ENDED" and in_selected_visit:
                assert vid == msg.split()[1]
                assert selected_visit_id == msg.split()[1]

                vend = "T".join(time.split())[:-3]
                if verbose:
                    print(f"VISIT {selected_visit_id} END FOUND at {vend}")

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
        print(f"Retrieving {url}")
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
