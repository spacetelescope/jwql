"""Provides an OAuth object for authentication of the ``jwql`` web app,
as well as decorator functions to require user authentication in other
views of the web application.


Authors
-------

    - Matthew Bourque
    - Christian Mesh

Use
---

    This module is intended to be imported and used as such:
    ::

        from .oauth import auth_info
        from .oauth import auth_required
        from .oauth import JWQL_OAUTH

        @auth_info
        def some_view(request):
            pass

        @auth_required
        def login(request):
            pass

References
----------
    Much of this code was taken from the ``authlib`` documentation,
    found here: ``http://docs.authlib.org/en/latest/client/django.html``

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql/utils/`` directory.
"""

import os
import requests

from authlib.django.client import OAuth

from jwql.utils.utils import get_base_url
from jwql.utils.utils import get_config


def auth_required(fn):
    """A decorator function that requires the given function to have
    authentication through ``auth.mast`` set up.

    Parameters
    ----------
    fn : function
        The function to decorate

    Returns
    -------
    check_auth : function
        The decorated function
    """

    @auth_info
    def check_auth(request, user):
        """Check if the user is authenticated through ``auth.mast``.
        If not, perform the authorization.

        Parameters
        ----------
        request : HttpRequest object
            Incoming request from the webpage
        user : dict
            A dictionary of user credentials

        Returns
        -------
        fn : function
            The decorated function
        """

        # If user is currently anonymous, require a login
        if user["anon"]:
            # Redirect to oauth login
            redirect_uri = os.path.join(get_base_url(), 'authorize')
            return JWQL_OAUTH.mast_auth.authorize_redirect(request, redirect_uri)

        return fn(request, user)

    return check_auth


def auth_info(fn):
    """A decorator function that will return user credientials along
    with what is returned by the original function.

    Parameters
    ----------
    fn : function
        The function to decorate

    Returns
    -------
    user_info : function
        The decorated function
    """

    def user_info(request):
        """Store authenticated user credentials in a cookie and return
        it.  If the user is not authenticated, store no credentials in
        the cookie.

        Parameters
        ----------
        request : HttpRequest object
            Incoming request from the webpage

        Returns
        -------
        fn : function
            The decorated function
        """

        cookie = request.COOKIES.get("ASB-AUTH")

        # If user is authenticated, return user credentials
        if cookie is not None:
            response = requests.get(
                'https://{}/info'.format(get_config()['auth_mast']),
                headers={'Accept': 'application/json',
                         'Authorization': 'token {}'.format(cookie)})
            response = response.json()

        # If user is not authenticated, return no credentials
        else:
            response = {'ezid' : None, "anon": True}

        return fn(request, response)

    return user_info


def register_oauth():
    """Register the ``jwql`` application with the ``auth.mast``
    authentication service.

    Returns
    -------
    oauth : Object
        An object containing methods to authenticate a user, provided
        by the ``auth.mast`` service.
    """

    # Get configuration parameters
    client_id = get_config()['client_id']
    client_secret = get_config()['client_secret']
    auth_mast = get_config()['auth_mast']

    # Register with auth.mast
    oauth = OAuth()
    client_kwargs = {'scope' : 'mast:user:info'}
    oauth.register(
        'mast_auth',
        client_id='{}'.format(client_id),
        client_secret='{}'.format(client_secret),
        access_token_url='https://{}/oauth/access_token?client_secret={}'.format(auth_mast, client_secret),
        access_token_params=None,
        refresh_token_url=None,
        authorize_url='https://{}/oauth/authorize'.format(auth_mast),
        api_base_url='https://{}/1.1/'.format(auth_mast),
        client_kwargs=client_kwargs)

    return oauth


JWQL_OAUTH = register_oauth()
