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
    - Bryan Hilbert
    - Maria Pena-Guerrero

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
from . import views

app_name = 'jwql'
instruments = 'nircam|NIRCam|niriss|NIRISS|nirspec|NIRSpec|miri|MIRI|fgs|FGS'

urlpatterns = [

    # Home
    path('', views.home, name='home'),

    # NIRSpec-specific views
    path('nirspec/msata_monitor/', monitor_views.msata_monitoring, name='msata_monitor'),
    path('nirspec/wata_monitor/', monitor_views.wata_monitoring, name='wata_monitor'),

    # Common monitor views
    re_path(r'^(?P<inst>({}))/dark_monitor/$'.format(instruments), monitor_views.dark_monitor, name='dark_monitor'),
    re_path(r'^(?P<inst>({}))/bad_pixel_monitor/$'.format(instruments), monitor_views.bad_pixel_monitor, name='bad_pixel_monitor'),
    re_path(r'^(?P<inst>({}))/bias_monitor/$'.format(instruments), monitor_views.bias_monitor, name='bias_monitor'),
    re_path(r'^(?P<inst>({}))/readnoise_monitor/$'.format(instruments), monitor_views.readnoise_monitor, name='readnoise_monitor'),
    re_path(r'^(?P<inst>({}))/edb_monitor/$'.format(instruments), monitor_views.edb_monitor, name='edb_monitor'),
    re_path(r'^(?P<inst>({}))/cosmic_ray_monitor/$'.format(instruments), monitor_views.cosmic_ray_monitor, name='cosmic_ray_monitor'),

    # Main site views
    path('about/', views.about, name='about'),
    path('jwql_query/', views.jwql_query, name='jwql_query'),
    path('api/', views.api_landing, name='api'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('download_table/<str:tablename>', views.export, name='download_table'),
    path('edb/', views.engineering_database, name='edb'),
    path('jwqldb/', views.jwqldb_table_viewer, name='jwqldb'),
    path('jwqldb/<str:tablename_param>', views.jwqldb_table_viewer, name='jwqldb_table_viewer'),
    path('log_view/', views.log_view, name='log_view'),
    path('query_submit/', views.query_submit, name='query_submit'),
    re_path(r'^(?P<inst>({}))/$'.format(instruments), views.instrument, name='instrument'),
    re_path(r'^(?P<inst>({}))/archive/$'.format(instruments), views.archived_proposals, name='archive'),
    re_path(r'^(?P<inst>({}))/archive_date_range/$'.format(instruments), views.archive_date_range, name='archive_date_range'),
    re_path(r'^(?P<inst>({}))/unlooked/$'.format(instruments), views.unlooked_images, name='unlooked'),
    re_path(r'^(?P<inst>({}))/report/$'.format(instruments), views.download_report, name='download_report'),
    re_path(r'^(?P<inst>({}))/(?P<file_root>[\w-]+)/$'.format(instruments), views.view_image, name='view_image'),
    re_path(r'^(?P<inst>({}))/(?P<file_root>.+)_(?P<filetype>.+)/explore_image/'.format(instruments), views.explore_image, name='explore_image'),
    re_path(r'^(?P<inst>({}))/(?P<filename>.+)_(?P<filetype>.+)/header/'.format(instruments), views.view_header, name='view_header'),
    re_path(r'^(?P<inst>({}))/archive/(?P<proposal>[\d]{{1,5}})/obs(?P<observation>[\d]{{1,3}})/$'.format(instruments), views.archive_thumbnails_per_observation, name='archive_thumb_per_obs'),

    # AJAX views
    re_path('ajax/query_submit/', views.archive_thumbnails_query_ajax, name='archive_thumb_query_ajax'),
    re_path(r'^ajax/(?P<inst>({}))/archive/$'.format(instruments), views.archived_proposals_ajax, name='archive_ajax'),
    re_path(r'^ajax/(?P<inst>({}))/(?P<file_root>.+)_(?P<filetype>.+)/explore_image/$'.format(instruments), views.explore_image_ajax, name='explore_image_ajax'),
    re_path(r'^ajax/(?P<inst>({}))/(?P<file_root>.+)_(?P<filetype>.+)/explore_image/scaling_(?P<scaling>.+)/low_(?P<low_lim>.+)/high_(?P<high_lim>.+)/ext_(?P<ext_name>.+)/int1_(?P<int1_nr>.+)/grp1_(?P<grp1_nr>.+)/int2_(?P<int2_nr>.+)/grp2_(?P<grp2_nr>.+)/$'.format(instruments), views.explore_image_ajax, name='explore_image_ajax'),
    re_path(r'^ajax/(?P<inst>({}))/archive/(?P<proposal>[\d]{{1,5}})/obs(?P<observation>[\d]{{1,3}})/$'.format(instruments), views.archive_thumbnails_ajax, name='archive_thumb_ajax'),
    re_path(r'^ajax/viewed/(?P<file_root>.+)/$', views.toggle_viewed_ajax, name='toggle_viewed_ajax'),
    re_path(r'^ajax/(?P<inst>({}))/archive_date_range/start_date_(?P<start_date>.+)/stop_date_(?P<stop_date>.+)/$'.format(instruments), views.archive_date_range_ajax, name='archive_date_range_ajax'),
    re_path(r'^ajax/image_group/$', views.save_image_group_ajax, name='save_image_group_ajax'),
    re_path(r'^ajax/image_sort/$', views.save_image_sort_ajax, name='save_image_sort_ajax'),
    re_path(r'^ajax/navigate_filter/$', views.save_page_navigation_data_ajax, name='save_page_navigation_data_ajax'),
    re_path('ajax/nirspec/msata/', monitor_views.msata_monitoring_ajax, name='msata_ajax'),
    re_path('ajax/nirspec/wata/', monitor_views.wata_monitoring_ajax, name='wata_ajax'),

    # REST API views
    path('api/proposals/', api_views.all_proposals, name='all_proposals'),
    re_path(r'^api/(?P<inst>({}))/proposals/$'.format(instruments),
            api_views.instrument_proposals, name='instrument_proposals'),
    re_path(r'^api/(?P<proposal>[\d]{1,5})/filenames/$',
            api_views.filenames_by_proposal, name='filenames_by_proposal'),
    re_path(r'^api/(?P<proposal>[\d]{1,5})/preview_images/$',
            api_views.preview_images_by_proposal, name='preview_images_by_proposal'),
    re_path(r'^api/(?P<proposal>[\d]{1,5})/thumbnails/$',
            api_views.thumbnails_by_proposal, name='preview_images_by_proposal'),
    re_path(r'^api/(?P<rootname>[\w]+)/filenames/$',
            api_views.filenames_by_rootname, name='filenames_by_rootname'),
    re_path(r'^api/(?P<rootname>[\w]+)/preview_images/$',
            api_views.preview_images_by_rootname, name='preview_images_by_rootname'),
    re_path(r'^api/(?P<rootname>[\w]+)/thumbnails/$',
            api_views.thumbnail_by_rootname, name='thumbnail_by_rootname'),
    re_path(r'^api/(?P<inst>({}))/looks/$'.format(instruments),
            api_views.instrument_looks, name='instrument_looks'),
    re_path(r'^api/(?P<inst>({}))/looks/(?P<status>(viewed|new))/$'.format(instruments),
            api_views.instrument_looks, name='instrument_looks_by_status'),
]
