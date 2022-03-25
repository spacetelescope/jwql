#! /usr/bin/env python

"""Do we really need this in a separate utils file?
"""
from datetime import timedelta

import astropy.units as u


def check_key(dictionary, key):
    """Check if a given key exists in the input dictionary. If so, return the value
    for that key. If not, return None.

    Parameters
    ----------
    dictionary : dict
        Dictionary

    key : string
        Key to search for

    Returns
    -------
    obj: obj
        Value associated with key, or None
    """
    try:
        return dictionary[key]
    except KeyError:
        return None


def get_averaging_time_duration(duration_string):
    """Turn the string from the mnemonic json file that specifies the time
    span to average the data over into an astropy quantity. This function
    is intended to be called only for "time_interval" mnemonic types, where
    the duration string is assumed to be of the form "X_UNIT", where X is
    a number, and UNIT is a unit of time (e.g. sec, min, hour, day).

    Parameters
    ----------
    duration_string : str
        Length of time for the query

    Returns
    -------
    time : astropy.units.quantity.Quantity
    """
    try:
        length, unit = duration_string.split('_')
        length = float(length)

        if "min" in unit:
            unit = u.minute
        elif "sec" in unit:
            unit = u.second
        elif "hour" in unit:
            unit = u.hour
        elif "day" in unit:
            unit = u.day
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

        time = length * unit

    except ValueError:
        raise ValueError(f"Unexpected/unsupported mnemonic duration string: {duration_string}")
    return time


def get_query_duration(mnemonic_type):
    """Turn the string version of the EDB query duration into a timedelta
    quantity. Allowed duration_string values include "daily_means",
    "every_change", "block_means", or "time_interval", or "none". These terms
    describe more how the mnemonic's data will be processed after it is
    retrieved, but we can map each mnemonic type to a length of time to
    use for the EDB query.

    Parameters
    ----------
    duration_string : str
        Length of time for the query

    Returns
    -------
    time : datetime.timedelta
    """
    if mnemonic_type.lower() == "daily_means":
        #time = 15. * u.minute
        time = timedelta(days=0.01)
    elif mnemonic_type in ["every_change", "block_means", "time_interval", "none"]:
        #time = 1. * u.day
        time = timedelta(days=1)
    else:
        raise ValueError(f"Unrecognized mnemonic type: {mnemonic_type}. Unsure what duration to use for EDB query.")
    return time


def remove_outer_points(telemetry):
    """Strip the first and last data points from the input telemetry data. This is because
    MAST includes the two datapoints immediately outside the requested time range.

    Parameters
    ----------
    telemetry : jwql.edb.engineering_database.EDBMnemonic
        Results from an EDB query.

    Returns
    -------
    telemetry : jwql.edb.engineering_database.EDBMnemonic
        EDBMnemonic object with first and last points removed
    """
    telemetry.data.remove_row(0)
    telemetry.data.remove_row(-1)
    #return telemetry
