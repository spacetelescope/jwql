"""Defines the models for the ``jwql`` bad pixel monitors.

In Django, "a model is the single, definitive source of information
about your data. It contains the essential fields and behaviors of the
data you’re storing. Generally, each model maps to a single database
table" (from Django documentation). Each model contains fields, such
as character fields or date/time fields, that function like columns in
a data table. This module defines models that are used to store data
related to the JWQL monitors.

Authors
-------
    - Brian York
Use
---
    This module is used as such:

    ::
        from monitor_models import MyModel
        data = MyModel.objects.filter(name="JWQL")

References
----------
    For more information please see:
        ```https://docs.djangoproject.com/en/2.0/topics/db/models/```
"""
# This is an auto-generated Django model module.
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class FgsBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FgsBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'
