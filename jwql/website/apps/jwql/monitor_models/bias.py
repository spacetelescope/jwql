"""Defines the models for the ``jwql`` monitors.

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


class NIRCamBiasQueryHistory(models.Model):
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    entries_found = models.IntegerField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_bias_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRCamBiasStats(models.Model):
    aperture = models.CharField(blank=True, null=True)
    uncal_filename = models.CharField(blank=True, null=True)
    cal_filename = models.CharField(blank=True, null=True)
    cal_image = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    median = models.FloatField(blank=True, null=True)
    stddev = models.FloatField(blank=True, null=True)
    collapsed_rows = ArrayField(models.FloatField())
    collapsed_columns = ArrayField(models.FloatField())
    counts = ArrayField(models.FloatField())
    bin_centers = ArrayField(models.FloatField())
    amp1_even_med = models.FloatField(blank=True, null=True)
    amp1_odd_med = models.FloatField(blank=True, null=True)
    amp2_even_med = models.FloatField(blank=True, null=True)
    amp2_odd_med = models.FloatField(blank=True, null=True)
    amp3_even_med = models.FloatField(blank=True, null=True)
    amp3_odd_med = models.FloatField(blank=True, null=True)
    amp4_even_med = models.FloatField(blank=True, null=True)
    amp4_odd_med = models.FloatField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_bias_stats'
        unique_together = (('id', 'entry_date'),)


class NIRISSBiasQueryHistory(models.Model):
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    entries_found = models.IntegerField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_bias_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRISSBiasStats(models.Model):
    aperture = models.CharField(blank=True, null=True)
    uncal_filename = models.CharField(blank=True, null=True)
    cal_filename = models.CharField(blank=True, null=True)
    cal_image = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    median = models.FloatField(blank=True, null=True)
    stddev = models.FloatField(blank=True, null=True)
    collapsed_rows = ArrayField(models.FloatField())
    collapsed_columns = ArrayField(models.FloatField())
    counts = ArrayField(models.FloatField())
    bin_centers = ArrayField(models.FloatField())
    amp1_even_med = models.FloatField(blank=True, null=True)
    amp1_odd_med = models.FloatField(blank=True, null=True)
    amp2_even_med = models.FloatField(blank=True, null=True)
    amp2_odd_med = models.FloatField(blank=True, null=True)
    amp3_even_med = models.FloatField(blank=True, null=True)
    amp3_odd_med = models.FloatField(blank=True, null=True)
    amp4_even_med = models.FloatField(blank=True, null=True)
    amp4_odd_med = models.FloatField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_bias_stats'
        unique_together = (('id', 'entry_date'),)


class NIRSpecBiasQueryHistory(models.Model):
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    entries_found = models.IntegerField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_bias_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRSpecBiasStats(models.Model):
    aperture = models.CharField(blank=True, null=True)
    uncal_filename = models.CharField(blank=True, null=True)
    cal_filename = models.CharField(blank=True, null=True)
    cal_image = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    median = models.FloatField(blank=True, null=True)
    stddev = models.FloatField(blank=True, null=True)
    collapsed_rows = ArrayField(models.FloatField())
    collapsed_columns = ArrayField(models.FloatField())
    counts = ArrayField(models.FloatField())
    bin_centers = ArrayField(models.FloatField())
    amp1_even_med = models.FloatField(blank=True, null=True)
    amp1_odd_med = models.FloatField(blank=True, null=True)
    amp2_even_med = models.FloatField(blank=True, null=True)
    amp2_odd_med = models.FloatField(blank=True, null=True)
    amp3_even_med = models.FloatField(blank=True, null=True)
    amp3_odd_med = models.FloatField(blank=True, null=True)
    amp4_even_med = models.FloatField(blank=True, null=True)
    amp4_odd_med = models.FloatField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_bias_stats'
        unique_together = (('id', 'entry_date'),)
