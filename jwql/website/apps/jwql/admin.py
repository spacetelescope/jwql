"""Customizes the ``jwql`` web app administrative page.

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

from jwql.utils.constants import ANOMALIES_PER_INSTRUMENT
from .models import Archive, Observation, Proposal, RootFileInfo, Anomalies


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    pass


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('archive', 'prop_id', 'category')
    list_filter = ('archive', 'category')


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'obsnum')
    list_filter = ('proposal', 'obsstart', 'exptypes')


@admin.register(RootFileInfo)
class RootFileInfoAdmin(admin.ModelAdmin):
    list_display = ('root_name', 'obsnum', 'proposal', 'instrument', 'viewed', 'filter', 'aperture', 'detector', 'read_patt_num', 'read_patt', 'grating', 'subarray', 'pupil', 'exp_type', 'expstart')
    list_filter = ('viewed', 'instrument', 'proposal')


@admin.register(Anomalies)
class AnomaliesAdmin(admin.ModelAdmin):
    list_display = ('root_file_info', 'flag_date', 'user') + tuple(ANOMALIES_PER_INSTRUMENT.keys())
    list_filter = ('flag_date', 'user') + tuple(ANOMALIES_PER_INSTRUMENT.keys()) + ('root_file_info')
