"""Defines the views for the ``jwql`` web app instrument monitors.

Authors
-------

    - Lauren Chambers

Use
---

    This module is called in ``urls.py`` as such:
    ::

        from django.urls import path
        from . import monitor_views
        urlpatterns = [path('web/path/to/view/', monitor_views.view_name,
        name='view_name')]

References
----------
    For more information please see:
        ``https://docs.djangoproject.com/en/2.0/topics/http/views/``

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql/utils/`` directory.
"""

import os

from django.shortcuts import render

from . import monitor_containers
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


def bias_monitor(request, instrument):
    """Generate the bias monitor page for a given instrument

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    instrument : str
        Name of JWST instrument

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]

    # Deal with the fact that only the NIRCam database is populated
    if instrument == 'NIRCam':
        tabs_components = monitor_containers.bias_monitor_tabs(inst)
    else:
        tabs_components = None

    template = 'bias_monitor.html'

    context = {
        'inst': instrument,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


def dark_monitor(request, instrument):
    """Generate the dark monitor page for a given instrument

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    instrument : str
        Name of JWST instrument

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    instrument = JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]

    # Deal with the fact that only the NIRCam database is populated
    if instrument == 'NIRCam':
        tabs_components = monitor_containers.dark_monitor_tabs(inst)
    else:
        tabs_components = None

    template = 'dark_monitor.html'

    context = {
        'inst': instrument,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)
