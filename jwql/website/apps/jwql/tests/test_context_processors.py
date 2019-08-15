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

from jwql.website.apps.jwql import context_processors
from jwql.utils.utils import get_base_url


class TestBaseContext(TestCase):
    def test_base_context(self):
        """Tests the ``base_context`` function."""

        client = Client()
        request = client.get('{}/about/'.format(get_base_url()))
        request.COOKIES = {}
        context = context_processors.base_context(request)

        assert isinstance(context, dict)

        keys = ['inst_list', 'tools', 'user', 'version']
        for key in keys:
            assert key in context
