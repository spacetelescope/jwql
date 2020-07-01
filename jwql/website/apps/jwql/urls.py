"""Maps URL paths to views in the ``jwql`` app.

This module connects requested URL paths to the corresponding view in
``views.py`` for each webpage in the ``jwql`` app. When django is
provided a path, it searches through the ``urlpatterns`` list provided
here until it finds one that matches. It then calls the assigned view
to load the appropriate webpage, passing an ``HttpRequest`` object.

Authors
-------

    - Lauren Chambers
    - Matthew Bourque
    - Johannes Sahlmann
    - Teagan King

Use
---

    Function views
        1. Add an import:  from my_app import views
        2. Add a URL to urlpatterns:  path('', views.home, name='home')
    Class-based views
        1. Add an import:  from other_app.views import Home
        2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
    Including another URLconf
        1. Import the include() function: from django.urls import include, path
        2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

References
----------
    For more information please see:
        ``https://docs.djangoproject.com/en/2.0/topics/http/urls/``

Notes
-----
    Be aware that when a url is requested, it will be directed to the
    first matching path in the ``urlpatterns`` list that it finds. The
    ``<str:var>`` tag is just a placeholder. To avoid complications,
    users should order their paths in order from shortest to longest,
    and after that from most to least specific.
"""

from django.urls import path
from django.urls import re_path

from . import api_views
from . import monitor_views
from . import oauth
from . import views

app_name = 'jwql'
instruments = 'nircam|NIRCam|niriss|NIRISS|nirspec|NIRSpec|miri|MIRI|fgs|FGS'

urlpatterns = [

    # Home
    path('', views.home, name='home'),

    # Authentication
    path('login/', oauth.login, name='login'),
    path('logout/', oauth.logout, name='logout'),
    path('authorize/', oauth.authorize, name='authorize'),

    # MIRI-specific views
    path('miri/miri_data_trending/', views.miri_data_trending, name='miri_data_trending'),

    # NIRSpec-specific views
    path('nirspec/nirspec_data_trending/', views.nirspec_data_trending, name='nirspec_data_trending'),

    # Common monitor views
    re_path(r'^(?P<inst>({}))/.+_monitor/$'.format(instruments), monitor_views.dark_monitor, name='dark_monitor'),

    # Main site views
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edb/', views.engineering_database, name='edb'),
    path('query_anomaly/', views.query_anomaly, name='query_anomaly'),
    path('query_anomaly_2/', views.query_anomaly_2, name='query_anomaly_2'),
    path('query_anomaly_3/', views.query_anomaly_3, name='query_anomaly_3'),
    path('query_submit/', views.query_submit, name='query_submit'),
    path('table_viewer', views.jwqldb_table_viewer, name='table_viewer'),
    re_path(r'^(?P<inst>({}))/$'.format(instruments), views.instrument, name='instrument'),
    re_path(r'^(?P<inst>({}))/archive/$'.format(instruments), views.archived_proposals, name='archive'),
    re_path(r'^(?P<inst>({}))/unlooked/$'.format(instruments), views.unlooked_images, name='unlooked'),
    re_path(r'^(?P<inst>({}))/(?P<file_root>[\w]+)/$'.format(instruments), views.view_image, name='view_image'),
    re_path(r'^(?P<inst>({}))/(?P<filename>.+)/header/$'.format(instruments), views.view_header, name='view_header'),
    re_path(r'^(?P<inst>({}))/archive/(?P<proposal>[\d]{{1,5}})/$'.format(instruments), views.archive_thumbnails, name='archive_thumb'),

    # AJAX views
    re_path(r'^ajax/(?P<inst>({}))/archive/$'.format(instruments), views.archived_proposals_ajax, name='archive_ajax'),
    re_path(r'^ajax/(?P<inst>({}))/archive/(?P<proposal>[\d]{{1,5}})/$'.format(instruments), views.archive_thumbnails_ajax, name='archive_thumb_ajax'),

    # REST API views
    path('api/proposals/', api_views.all_proposals, name='all_proposals'),
    #path('api/queried_thumbnails/', api_views.thumbnails_all_instruments, name='thumbnails_all_instruments'),
    re_path(r'^api/(?P<inst>({}))/proposals/$'.format(instruments), api_views.instrument_proposals, name='instrument_proposals'),
    re_path(r'^api/(?P<inst>({}))/preview_images/$'.format(instruments), api_views.preview_images_by_instrument, name='preview_images_by_instrument'),
    re_path(r'^api/(?P<inst>({}))/thumbnails/$'.format(instruments), api_views.thumbnails_by_instrument, name='thumbnails_by_instrument'),
    re_path(r'^api/(?P<proposal>[\d]{1,5})/filenames/$', api_views.filenames_by_proposal, name='filenames_by_proposal'),
    re_path(r'^api/(?P<proposal>[\d]{1,5})/preview_images/$', api_views.preview_images_by_proposal, name='preview_images_by_proposal'),
    re_path(r'^api/(?P<proposal>[\d]{1,5})/thumbnails/$', api_views.thumbnails_by_proposal, name='preview_images_by_proposal'),
    re_path(r'^api/(?P<rootname>[\w]+)/filenames/$', api_views.filenames_by_rootname, name='filenames_by_rootname'),
    re_path(r'^api/(?P<rootname>[\w]+)/preview_images/$', api_views.preview_images_by_rootname, name='preview_images_by_rootname'),
    re_path(r'^api/(?P<rootname>[\w]+)/thumbnails/$', api_views.thumbnails_by_rootname, name='thumbnails_by_rootname'),
]
