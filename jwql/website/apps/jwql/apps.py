"""Customizes the ``jwql`` app settings.

** CURRENTLY NOT IN USE **

Optionally defines an ``AppConfig`` class that can be called in
``INSTALLED_APPS`` in settings.py to configure the web app.

Authors
-------

    - Lauren Chambers

Use
---

    This module is called in ``settings.py`` as such:
    ::
        INSTALLED_APPS = ['apps.jwql.PlotsExampleConfig',
        ...
        ]

References
----------
    For more information please see:
        ``https://docs.djangoproject.com/en/2.0/ref/applications/``
"""

from django.apps import AppConfig


class PlotsExampleConfig(AppConfig):
    name = 'jwql'
