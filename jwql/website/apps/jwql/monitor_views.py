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
from jwql.website.apps.jwql import bokeh_containers_no_templating_for_cosmicrays
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config

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

    tabs_components = bokeh_containers_no_templating_for_cosmicrays.cosmic_ray_monitor_tabs(inst)

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
