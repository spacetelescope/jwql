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


class FGSReadnoiseQueryHistory(models.Model):
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
        db_table = 'fgs_readnoise_query_history'
        unique_together = (('id', 'entry_date'),)


class FGSReadnoiseStats(models.Model):
    uncal_filename = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    subarray = models.CharField(blank=True, null=True)
    read_pattern = models.CharField(blank=True, null=True)
    nints = models.CharField(blank=True, null=True)
    ngroups = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    readnoise_filename = models.CharField(blank=True, null=True)
    full_image_mean = models.FloatField(blank=True, null=True)
    full_image_stddev = models.FloatField(blank=True, null=True)
    full_image_n = ArrayField(models.FloatField())
    full_image_bin_centers = ArrayField(models.FloatField())
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = ArrayField(models.FloatField())
    diff_image_bin_centers = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = ArrayField(models.FloatField())
    amp1_bin_centers = ArrayField(models.FloatField())
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = ArrayField(models.FloatField())
    amp2_bin_centers = ArrayField(models.FloatField())
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = ArrayField(models.FloatField())
    amp3_bin_centers = ArrayField(models.FloatField())
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = ArrayField(models.FloatField())
    amp4_bin_centers = ArrayField(models.FloatField())

    class Meta:
        managed = True
        db_table = 'fgs_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


class MIRIReadnoiseQueryHistory(models.Model):
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
        db_table = 'miri_readnoise_query_history'
        unique_together = (('id', 'entry_date'),)


class MIRIReadnoiseStats(models.Model):
    uncal_filename = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    subarray = models.CharField(blank=True, null=True)
    read_pattern = models.CharField(blank=True, null=True)
    nints = models.CharField(blank=True, null=True)
    ngroups = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    readnoise_filename = models.CharField(blank=True, null=True)
    full_image_mean = models.FloatField(blank=True, null=True)
    full_image_stddev = models.FloatField(blank=True, null=True)
    full_image_n = ArrayField(models.FloatField())
    full_image_bin_centers = ArrayField(models.FloatField())
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = ArrayField(models.FloatField())
    diff_image_bin_centers = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = ArrayField(models.FloatField())
    amp1_bin_centers = ArrayField(models.FloatField())
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = ArrayField(models.FloatField())
    amp2_bin_centers = ArrayField(models.FloatField())
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = ArrayField(models.FloatField())
    amp3_bin_centers = ArrayField(models.FloatField())
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = ArrayField(models.FloatField())
    amp4_bin_centers = ArrayField(models.FloatField())

    class Meta:
        managed = True
        db_table = 'miri_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


class NIRCamReadnoiseQueryHistory(models.Model):
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
        db_table = 'nircam_readnoise_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRCamReadnoiseStats(models.Model):
    uncal_filename = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    subarray = models.CharField(blank=True, null=True)
    read_pattern = models.CharField(blank=True, null=True)
    nints = models.CharField(blank=True, null=True)
    ngroups = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    readnoise_filename = models.CharField(blank=True, null=True)
    full_image_mean = models.FloatField(blank=True, null=True)
    full_image_stddev = models.FloatField(blank=True, null=True)
    full_image_n = ArrayField(models.FloatField())
    full_image_bin_centers = ArrayField(models.FloatField())
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = ArrayField(models.FloatField())
    diff_image_bin_centers = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = ArrayField(models.FloatField())
    amp1_bin_centers = ArrayField(models.FloatField())
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = ArrayField(models.FloatField())
    amp2_bin_centers = ArrayField(models.FloatField())
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = ArrayField(models.FloatField())
    amp3_bin_centers = ArrayField(models.FloatField())
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = ArrayField(models.FloatField())
    amp4_bin_centers = ArrayField(models.FloatField())

    class Meta:
        managed = True
        db_table = 'nircam_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


class NIRISSReadnoiseQueryHistory(models.Model):
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
        db_table = 'niriss_readnoise_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRISSReadnoiseStats(models.Model):
    uncal_filename = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    subarray = models.CharField(blank=True, null=True)
    read_pattern = models.CharField(blank=True, null=True)
    nints = models.CharField(blank=True, null=True)
    ngroups = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    readnoise_filename = models.CharField(blank=True, null=True)
    full_image_mean = models.FloatField(blank=True, null=True)
    full_image_stddev = models.FloatField(blank=True, null=True)
    full_image_n = ArrayField(models.FloatField())
    full_image_bin_centers = ArrayField(models.FloatField())
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = ArrayField(models.FloatField())
    diff_image_bin_centers = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = ArrayField(models.FloatField())
    amp1_bin_centers = ArrayField(models.FloatField())
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = ArrayField(models.FloatField())
    amp2_bin_centers = ArrayField(models.FloatField())
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = ArrayField(models.FloatField())
    amp3_bin_centers = ArrayField(models.FloatField())
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = ArrayField(models.FloatField())
    amp4_bin_centers = ArrayField(models.FloatField())

    class Meta:
        managed = True
        db_table = 'niriss_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


class NIRSpecReadnoiseQueryHistory(models.Model):
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
        db_table = 'nirspec_readnoise_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRSpecReadnoiseStats(models.Model):
    uncal_filename = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    subarray = models.CharField(blank=True, null=True)
    read_pattern = models.CharField(blank=True, null=True)
    nints = models.CharField(blank=True, null=True)
    ngroups = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    readnoise_filename = models.CharField(blank=True, null=True)
    full_image_mean = models.FloatField(blank=True, null=True)
    full_image_stddev = models.FloatField(blank=True, null=True)
    full_image_n = ArrayField(models.FloatField())
    full_image_bin_centers = ArrayField(models.FloatField())
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = ArrayField(models.FloatField())
    diff_image_bin_centers = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = ArrayField(models.FloatField())
    amp1_bin_centers = ArrayField(models.FloatField())
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = ArrayField(models.FloatField())
    amp2_bin_centers = ArrayField(models.FloatField())
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = ArrayField(models.FloatField())
    amp3_bin_centers = ArrayField(models.FloatField())
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = ArrayField(models.FloatField())
    amp4_bin_centers = ArrayField(models.FloatField())

    class Meta:
        managed = True
        db_table = 'nirspec_readnoise_stats'
        unique_together = (('id', 'entry_date'),)
