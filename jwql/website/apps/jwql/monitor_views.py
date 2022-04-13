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

from bokeh.resources import CDN, INLINE
from django.shortcuts import render
import json

from . import bokeh_containers
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.utils import get_config

CONFIG = get_config()
FILESYSTEM_DIR = os.path.join(CONFIG['jwql_dir'], 'filesystem')


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


def edb_monitor(request, inst):
    """Generate the EDB telemetry monitor page for a given instrument

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
    inst = inst.lower()
    plot_dir = os.path.join(CONFIG["outputs"], "edb_telemetry_monitor", inst)
    json_file = f'edb_{inst}_tabbed_plots.json'

    # Get the json data that contains the tabbed plots
    #with open(os.path.join(plot_dir, f'edb_{inst}_tabbed_plots.json')), 'r'_ as fp:  # USE THIS LINE FOR PRODUCTION
    #with open("/Users/hilbert/python_repos/jwql/jwql/instrument_monitors/common_monitors/edb_nircam_tabbed_plots.json", 'r') as fp:
    with open(os.path.join(plot_dir, json_file), 'r') as fp:
        data=json.dumps(json.loads(fp.read()))

    template = "edb_monitor.html"

    context = {
        'inst': JWST_INSTRUMENT_NAMES_MIXEDCASE[inst],
        'json_object':data,
        'resources':CDN.render()
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
