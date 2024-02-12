"""Defines the models for the ``jwql`` EDB monitors.

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


class FgsEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FgsEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FgsEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = models.TextField(blank=True, null=True)  # This field type is a guess.
    mnemonic_value = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FgsEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FgsEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = models.TextField(blank=True, null=True)  # This field type is a guess.
    mnemonic_value = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = models.TextField(blank=True, null=True)  # This field type is a guess.
    mnemonic_value = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = models.TextField(blank=True, null=True)  # This field type is a guess.
    mnemonic_value = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = models.TextField(blank=True, null=True)  # This field type is a guess.
    mnemonic_value = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    median = models.TextField(blank=True, null=True)  # This field type is a guess.
    max = models.TextField(blank=True, null=True)  # This field type is a guess.
    min = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = models.TextField(blank=True, null=True)  # This field type is a guess.
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    stdev = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'
