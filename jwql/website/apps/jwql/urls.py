"""Maps URL paths to views in the ``jwql`` app.

This module connects requested URL paths to the corresponding view in
``views.py`` for each webpage in the ``jwql`` app. When django is
provided a path, it searches through the ``urlpatterns`` list provided
here until it finds one that matches. It then calls the assigned view
to load the appropriate webpage, passing an ``HttpRequest`` object.

Authors
-------

    - Lauren Chambers

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

from . import views

app_name = 'jwql'
urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('jwql/<str:inst>/', views.instrument, name='instrument'),
    path('jwql/<str:inst>/archive/', views.archived_proposals, name='archive'),
    path('jwql/<str:inst>/unlooked/', views.unlooked_images, name='unlooked'),
    path('jwql/<str:inst>/<str:file_root>/', views.view_image, name='view_image'),
    path('jwql/<str:inst>/<str:file>/hdr/', views.view_header, name='view_header'),
    path('jwql/<str:inst>/archive/<str:proposal>', views.archive_thumbnails, name='archive_thumb'),
    path('api/proposals/', views.api_all_proposals, name='api_all_proposals'),
    path('api/<str:proposal>/filenames/', views.api_filenames_by_proposal, name='api_filenames_by_proposal'),
    path('api/<str:inst>/proposals/', views.api_instrument_proposals, name='api_instrument_proposals')
]
