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
from django.shortcuts import redirect, render

import jwql
from jwql.utils.constants import MONITORS
from jwql.utils.utils import get_base_url, get_config, check_config_for_key

PREV_PAGE = '/'


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
    for key in ['client_id', 'client_secret', 'auth_mast']:
        check_config_for_key(key)
    client_id = get_config()['client_id']
    client_secret = get_config()['client_secret']
    auth_mast = get_config()['auth_mast']

    # Register with auth.mast
    oauth = OAuth()
    client_kwargs = {'scope': 'mast:user:info'}
    oauth.register(
        'mast_auth',
        client_id='{}'.format(client_id),
        client_secret='{}'.format(client_secret),
        access_token_url='https://{}/oauth/access_token?client_secret={}'.format(
            auth_mast, client_secret
        ),
        access_token_params=None,
        refresh_token_url=None,
        authorize_url='https://{}/oauth/authorize'.format(auth_mast),
        api_base_url='https://{}/1.1/'.format(auth_mast),
        client_kwargs=client_kwargs)

    return oauth


JWQL_OAUTH = register_oauth()


def authorize(request):
    """Spawn the authentication process for the user

    The authentication process involves retreiving an access token
    from ``auth.mast`` and porting the data to a cookie.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Get auth.mast token
    token = JWQL_OAUTH.mast_auth.authorize_access_token(
        request, headers={'Accept': 'application/json'}
    )

    # Determine domain
    base_url = get_base_url()
    if '127' in base_url:
        domain = '127.0.0.1'
    else:
        domain = base_url.split('//')[-1]

    # Set secure cookie parameters
    cookie_args = {}
    # cookie_args['domain'] = domain  # Currently broken
    # cookie_args['secure'] = True  # Currently broken
    cookie_args['httponly'] = True

    # Set the cookie
    response = redirect(PREV_PAGE)
    response.set_cookie("ASB-AUTH", token["access_token"], **cookie_args)

    return response


def auth_info(fn):
    """A decorator function that will return user credentials along
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

    def user_info(request, **kwargs):
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
            check_config_for_key('auth_mast')
            # Note: for now, this must be the development version
            auth_mast = get_config()['auth_mast']

            response = requests.get(
                'https://{}/info'.format(auth_mast),
                headers={'Accept': 'application/json',
                         'Authorization': 'token {}'.format(cookie)})
            response = response.json()
            response['access_token'] = cookie

        # If user is not authenticated, return no credentials
        else:
            response = {'ezid': None, "anon": True, 'access_token': None}

        return fn(request, response, **kwargs)

    return user_info


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
    def check_auth(request, user, **kwargs):
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
        if user['ezid']:

            return fn(request, user, **kwargs)

        else:
            template = 'not_authenticated.html'
            context = {'inst': ''}

            return render(request, template, context)

    return check_auth


@auth_info
def login(request, user):
    """Spawn a login process for the user

    The ``auth_requred`` decorator is used to require that the user
    authenticate through ``auth.mast``, then the user is redirected
    back to the homepage.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    user : dict
        A dictionary of user credentials.

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    # Redirect to oauth login
    global PREV_PAGE
    PREV_PAGE = request.META.get('HTTP_REFERER')
    redirect_uri = os.path.join(get_base_url(), 'authorize')

    return JWQL_OAUTH.mast_auth.authorize_redirect(request, redirect_uri)


def logout(request):
    """Spawn a logout process for the user

    Upon logout, the user's ``auth.mast`` credientials are removed and
    the user is redirected back to the homepage.

    Parameters
    ----------
    request : HttpRequest object
        Incoming request from the webpage
    user : dict
        A dictionary of user credentials.

    Returns
    -------
    HttpResponse object
        Outgoing response sent to the webpage
    """

    global PREV_PAGE
    PREV_PAGE = request.META.get('HTTP_REFERER')
    response = redirect(PREV_PAGE)
    response.delete_cookie("ASB-AUTH")

    return response
