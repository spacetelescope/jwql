"""Defines the views for the ``jwql`` web app monitors.

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

from . import monitor_pages
from jwql.utils.utils import get_config

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


def dark_monitor(request):
    """Generate the NIRCam dark monitor page

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    monitor_template = monitor_pages.DarkMonitor('NIRCam', 'NRCA3_FULL')
    dark_current_time_components = monitor_template.embed("dark_current_time_figure")
    dark_current_hist_components = monitor_template.embed("dark_full_histogram_figure")

    template = "nircam_dark_monitor.html"

    context = {
        'inst': 'NIRCam',  # Leave as empty string or instrument name; Required for navigation bar
        'dark_current_time_components': dark_current_time_components,
        'dark_current_hist_components': dark_current_hist_components
    }


    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)
