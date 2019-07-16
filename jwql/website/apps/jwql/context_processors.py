"""Provides functions that define context inherent to all views.

The functions within this module define ``context`` that will be
included in requests, in addition to any specific ``context`` provided
in the view.

Authors
-------

    - Matthew Bourque

Use
---

    This module is defined under the ``TEMPLATES.OPTIONS`` setting in
    ``settings.py``, e.g.:
    ::

        TEMPLATES = [
            {'OPTIONS': {'context_processors': ['jwql.website.apps.jwql.context_processors.base_context'],},}
        ]

    As such, it will automatically be executed upon each request.
"""

import bokeh

import jwql
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, MONITORS

from .oauth import auth_info


@auth_info
def base_context(request, user):
    """Provide the context needed for the ``base.html`` template.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    context : dict
        A dictionary containing data needed to render the ``base.html``
        template
    """

    context = {}
    context['inst_list'] = JWST_INSTRUMENT_NAMES
    context['tools'] = MONITORS
    context['user'] = user
    context['version'] = jwql.__version__
    context['bokeh_version'] = bokeh.__version__

    return context
