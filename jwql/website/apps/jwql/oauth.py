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


def auth_info(fn):
    """
    """

    def user_info(request):
        """
        """

        cookie = request.COOKIES.get("ASB-AUTH")
        # TODO if cookie not set, don't hit auth.mast
        resp = requests.get(
            "https://auth.mastdev.stsci.edu/info",
            headers={"Accept": "application/json",
                     "Authorization": "token %s" % cookie})

        return fn(request, resp.json())

    return user_info


def register_oauth():
    """
    """

    oauth = OAuth()
    client_kwargs = {'scope' : 'mast:user:info'}
    oauth.register(
        'mast_auth',
        client_id='4263f8e374e6de22',
        client_secret='dea4340c583ce126bc735746b49568ec864f98339bd7b2484c943d05d7ef2d13',
        access_token_url='https://auth.mastdev.stsci.edu/oauth/access_token?client_secret=dea4340c583ce126bc735746b49568ec864f98339bd7b2484c943d05d7ef2d13',
        access_token_params=None,
        refresh_token_url=None,
        authorize_url='https://auth.mastdev.stsci.edu/oauth/authorize',
        api_base_url='https://auth.mastdev.stsci.edu/1.1/',
        client_kwargs=client_kwargs)

    return oauth

JWQL_OATH = register_oauth()
