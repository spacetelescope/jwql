"""Customizes the ``jwql`` web app administrative page.

** CURRENTLY NOT IN USE **

Used to customize django's admin interface, and how the data contained
in specific models is portrayed.

Authors
-------

    - Lauren Chambers

References
----------

    For more information please see:
        ``https://docs.djangoproject.com/en/2.0/ref/contrib/admin/``
"""

from django.contrib import admin

from .models import ImageData


class ImageDataAdmin(admin.ModelAdmin):
    # fieldsets = [('Filepath', {'fields': ['filepath']}),
    # 			 ('Instrument', {'fields': ['inst']}),
    #              ('Date information', {'fields': ['pub_date']})]
    list_display = ('filename', 'inst', 'pub_date')
    list_filter = ['pub_date']

admin.site.register(ImageData, ImageDataAdmin)
