"""Utility functions related to accessing remote services and databases.

Authors
-------

    - Johannes Sahlmann
    - Lauren Chambers
    - Mees Fix

Use
---

    This module can be imported as such:
    ::

        import credentials
        token = credentials.get_mast_token()

 """
import os

from astroquery.mast import Mast

from jwql.utils.utils import check_config_for_key, get_config


def get_mast_base_url(request=None):
    """Return base url for mnemonic query.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    token : str or None
        Base url for MAST JWST EDB API.
    """

    try:
        # check if token is available via config file
        check_config_for_key('mast_base_url')
        base_url = get_config()['mast_base_url']
        print('Base URL returned from config file.')
        return base_url
    except (KeyError, ValueError):
        # check if token is available via environment variable
        # see https://auth.mast.stsci.edu/info
        try:
            base_url = os.environ['ENG_BASE_URL']
            print('Base URL returned from environment variable.')
            return base_url
        except KeyError:
            return None


def get_mast_token(request=None):
    """Return MAST token from either Astroquery.Mast, webpage cookies,
    the JWQL configuration file, or an environment variable.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    token : str or None
        User-specific MAST token string, if available
    """

    if Mast.authenticated():
        print('Authenticated with Astroquery MAST magic')
        return None
    else:
        try:
            # check if token is available via config file
            check_config_for_key('mast_token')
            token = get_config()['mast_token']
            print('Authenticated with config.json MAST token.')
            return token
        except (KeyError, ValueError):
            # check if token is available via environment variable
            # see https://auth.mast.stsci.edu/info
            try:
                token = os.environ['MAST_API_TOKEN']
                print('Authenticated with MAST token environment variable.')
                return token
            except KeyError:
                return None
