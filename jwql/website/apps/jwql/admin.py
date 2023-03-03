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
    list_display = ('root_file_info', 'cosmic_ray_shower', 'diffraction_spike', 'excessive_saturation', 'guidestar_failure', 'persistence', 'crosstalk', 'data_transfer_error',
                    'ghost', 'snowball', 'column_pull_up', 'column_pull_down', 'dominant_msa_leakage', 'dragons_breath', 'mrs_glow', 'mrs_zipper', 'internal_reflection', 'optical_short', 'row_pull_up',
                    'row_pull_down', 'lrs_contamination', 'tree_rings', 'scattered_light', 'claws', 'wisps', 'tilt_event', 'light_saber', 'other')
    list_filter = ('cosmic_ray_shower', 'diffraction_spike', 'excessive_saturation', 'guidestar_failure', 'persistence', 'crosstalk', 'data_transfer_error',
                   'ghost', 'snowball', 'column_pull_up', 'column_pull_down', 'dominant_msa_leakage', 'dragons_breath', 'mrs_glow', 'mrs_zipper', 'internal_reflection', 'optical_short', 'row_pull_up',
                   'row_pull_down', 'lrs_contamination', 'tree_rings', 'scattered_light', 'claws', 'wisps', 'tilt_event', 'light_saber', 'other', 'root_file_info')
