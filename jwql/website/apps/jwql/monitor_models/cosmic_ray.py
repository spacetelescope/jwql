"""Defines the models for the ``jwql`` cosmic ray monitors.

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
from django.contrib.postgres.fields import ArrayField


class FGSCosmicRayQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_cosmic_ray_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FGSCosmicRayStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    source_file = models.CharField(blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    jump_count = models.IntegerField(blank=True, null=True)
    jump_rate = models.FloatField(blank=True, null=True)
    magnitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    outliers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'fgs_cosmic_ray_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MIRICosmicRayQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_cosmic_ray_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MIRICosmicRayStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    source_file = models.CharField(blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    jump_count = models.IntegerField(blank=True, null=True)
    jump_rate = models.FloatField(blank=True, null=True)
    magnitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    outliers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'miri_cosmic_ray_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NIRCamCosmicRayQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_cosmic_ray_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NIRCamCosmicRayStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    source_file = models.CharField(blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    jump_count = models.IntegerField(blank=True, null=True)
    jump_rate = models.FloatField(blank=True, null=True)
    magnitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    outliers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'nircam_cosmic_ray_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NIRISSCosmicRayQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_cosmic_ray_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NIRISSCosmicRayStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    source_file = models.CharField(blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    jump_count = models.IntegerField(blank=True, null=True)
    jump_rate = models.FloatField(blank=True, null=True)
    magnitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    outliers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'niriss_cosmic_ray_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NIRSpecCosmicRayQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_cosmic_ray_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NIRSpecCosmicRayStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    source_file = models.CharField(blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    jump_count = models.IntegerField(blank=True, null=True)
    jump_rate = models.FloatField(blank=True, null=True)
    magnitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    outliers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'nirspec_cosmic_ray_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'
