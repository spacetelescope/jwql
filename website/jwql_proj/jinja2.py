"""Jinja2 config for ``jwql`` project.

Set up Jinja2 environment and configure it to read Django ``static``
and ``url`` tags. Define custom Jinja extensions.

References
----------
    Environment definition copied from blog post about integrating Django
    with Jinja2, found here:
        ``https://medium.com/@samuh/using-jinja2-with-django-1-8-onwards-9c58fe1204dc``
    Re-implementation of the Django "now" tag found here:
        ``https://www.webforefront.com/django/useandcreatejinjaextensions.html``
"""

from datetime import datetime

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.template.defaultfilters import date
from django.contrib.staticfiles.storage import staticfiles_storage
from jinja2 import Environment, lexer, nodes
from jinja2.ext import Extension


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
    })

    return env


class DjangoNow(Extension):
    tags = set(['now'])

    def _now(self, date_format):
        tzinfo = timezone.get_current_timezone() if settings.USE_TZ else None
        formatted = date(datetime.now(tz=tzinfo), date_format)
        return formatted

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        token = parser.stream.expect(lexer.TOKEN_STRING)
        date_format = nodes.Const(token.value)
        call = self.call_method('_now', [date_format], lineno=lineno)
        token = parser.stream.current
        if token.test('name:as'):
            next(parser.stream)
            as_var = parser.stream.expect(lexer.TOKEN_NAME)
            as_var = nodes.Name(as_var.value, 'store', lineno=as_var.lineno)
            return nodes.Assign(as_var, call, lineno=lineno)
        else:
            return nodes.Output([call], lineno=lineno)
