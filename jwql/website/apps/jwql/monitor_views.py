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
    placed in the ``jwql`` directory.
"""

import os

from django.shortcuts import render

from . import bokeh_containers
from jwql.website.apps.jwql import bokeh_containers
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config
from jwql.instrument_monitors.nirspec_monitors.ta_monitors import msata_monitor
from jwql.instrument_monitors.nirspec_monitors.ta_monitors import wata_monitor
from jwql.utils import monitor_utils

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


def bad_pixel_monitor(request, inst):
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

    tabs_components = bokeh_containers.bad_pixel_monitor_tabs(inst)

    template = "bad_pixel_monitor.html"

    context = {
        'inst': inst,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


def bias_monitor(request, inst):
    """Generate the bias monitor page for a given instrument

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

    # Get the html and JS needed to render the bias tab plots
    tabs_components = bokeh_containers.bias_monitor_tabs(inst)

    template = "bias_monitor.html"

    context = {
        'inst': inst,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


def cosmic_ray_monitor(request, inst):
    """Generate the cosmic ray monitor page for a given instrument

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
    inst = inst.upper()

    tabs_components = bokeh_containers.cosmic_ray_monitor_tabs(inst)

    template = "cosmic_ray_monitor.html"

    context = {
        'inst': inst,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


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

    tabs_components = bokeh_containers.dark_monitor_tabs(inst)

    template = "dark_monitor.html"

    context = {
        'inst': inst,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


def readnoise_monitor(request, inst):
    """Generate the readnoise monitor page for a given instrument

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

    # Get the html and JS needed to render the readnoise tab plots
    tabs_components = bokeh_containers.readnoise_monitor_tabs(inst)

    template = "readnoise_monitor.html"

    context = {
        'inst': inst,
        'tabs_components': tabs_components,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


def msata_monitoring(request):
    """Container for MSATA monitor

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # run the monitor
    module = 'msata_monitor.py'
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)
    monitor = msata_monitor.MSATA()
    script_and_div = monitor.run()
    monitor_utils.update_monitor_table(module, start_time, log_file)

    # get the template and embed the plots
    template = "msata_monitor.html"

    context = {
        'inst': 'NIRSpec',
        'tabs_components': script_and_div,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)


def wata_monitoring(request):
    """Container for WATA monitor

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """
    # run the monitor
    module = 'wata_monitor.py'
    start_time, log_file = monitor_utils.initialize_instrument_monitor(module)
    monitor = wata_monitor.WATA()
    script_and_div = monitor.run()
    monitor_utils.update_monitor_table(module, start_time, log_file)

    # get the template and embed the plots
    template = "wata_monitor.html"

    context = {
        'inst': 'NIRSpec',
        'tabs_components': script_and_div,
    }

    # Return a HTTP response with the template and dictionary of variables
    return render(request, template, context)
