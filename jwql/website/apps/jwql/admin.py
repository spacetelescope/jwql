"""Customizes the ``jwql`` web app administrative page.

** CURRENTLY NOT IN USE **

Used to customize django's admin interface, and how the data contained
in specific models is portrayed.

Authors
-------

    - Lauren Chambers
    - Bryan Hilbert
    - Brad Sappington

References
----------

    For more information please see:
        ``https://docs.djangoproject.com/en/2.0/ref/contrib/admin/``
"""

from django.contrib import admin

from .models import Archive, Observation, Proposal, RootFileInfo


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    pass


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('archive', 'prop_id')
    list_filter = ('archive',)


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'obsnum')
    list_filter = ('proposal', 'obsstart', 'exptypes')


@admin.register(RootFileInfo)
class RootFileInfoAdmin(admin.ModelAdmin):
    list_display = ('root_name', 'obsnum', 'proposal', 'instrument', 'viewed')
    list_filter = ('viewed', 'instrument', 'proposal', 'obsnum')
