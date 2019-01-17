"""Provides an OAuth object for authentication of the ``jwql`` web app.


Authors
-------

    - Matthew Bourque
    - Christian Mesh

Use
---

    This module is intended to be imported and used as such:
    ::

        from .oauth import JWQL_OAUTH

References
----------
    Much of this code was taken from the ``authlib`` documentation,
    found here: ``http://docs.authlib.org/en/latest/client/django.html``

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql/utils/`` directory.
"""

import requests

from authlib.django.client import OAuth

from jwql.utils.utils import get_config


def auth_required(fn):
    """
    """

    @auth_info
    def check_auth(request, user):
        """
        """

        # If user is currently anonymous, require a login
        if user["anon"]:
            # Redirect to oauth login
            redirect_uri = request.build_absolute_uri('/authorize')
            return JWQL_OAUTH.mast_auth.authorize_redirect(request, redirect_uri)

        return fn(request, user)

    return check_auth


def auth_info(fn):
    """
    """

    def user_info(request):
        """
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
    """
    """

    # Get configuration parameters
    client_id = get_config()['client_id']
    client_secret = get_config()['client_secret']
    auth_mast = get_config()['auth_mast']

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
