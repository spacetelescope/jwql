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

from . import bokeh_containers
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


def dark_monitor(request, inst):
    """Generate the dark monitor page for a given instrument

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    inst : str
        Name of JWST instrument

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Ensure the instrument is correctly capitalized
    inst = JWST_INSTRUMENT_NAMES_MIXEDCASE[inst.lower()]

    # Deal with the fact that only the NIRCam database is populated
    if inst == 'NIRCam':
        tabs_components = bokeh_containers.dark_monitor_tabs(inst)
    else:
        tabs_components = None

    template = "dark_monitor.html"

    context = {
        'inst': inst,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)
