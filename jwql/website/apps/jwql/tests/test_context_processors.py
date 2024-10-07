#!/usr/bin/env python

"""Tests for the ``context_processors`` module in the ``jwql`` web
application.

Authors
-------

    - Matthew Bourque

Use
---

    These tests can be run via the command line from the ``website``
    subpackage as such:

    ::

        python manage.py test apps.jwql.tests
"""

from django.test import TestCase
from django.test.client import Client
import os
from unittest import skipIf

from jwql.utils.constants import ON_GITHUB_ACTIONS

if not ON_GITHUB_ACTIONS:
    from jwql.website.apps.jwql import context_processors
    from jwql.utils.utils import get_base_url


@skipIf(ON_GITHUB_ACTIONS, "Can't access webpage without VPN access")
class TestBaseContext(TestCase):
    def test_base_context(self):
        """Tests the ``base_context`` function."""

        # These lines are needed in order to use the Django models in a standalone
        # script (as opposed to code run as a result of a webpage request). If these
        # lines are not run, the script will crash when attempting to import the
        # Django models in the line below.
        from django import setup
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
        setup()

        client = Client()
        request = client.get('{}/about/'.format(get_base_url()))
        request.COOKIES = {}
        context = context_processors.base_context(request)

        assert isinstance(context, dict)

        keys = ['inst_list', 'tools', 'version']
        for key in keys:
            assert key in context
