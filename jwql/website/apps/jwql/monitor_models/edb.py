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
from django.contrib.postgres.fields import ArrayField


class FGSEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class FGSEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class FGSEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = ArrayField(models.DateTimeField())
    mnemonic_value = ArrayField(models.FloatField())
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class FGSEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class FGSEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class MIRIEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class MIRIEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class MIRIEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = ArrayField(models.DateTimeField())
    mnemonic_value = ArrayField(models.FloatField())
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class MIRIEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class MIRIEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRCamEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRCamEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRCamEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = ArrayField(models.DateTimeField())
    mnemonic_value = ArrayField(models.FloatField())
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRCamEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRCamEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRISSEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRISSEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRISSEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = ArrayField(models.DateTimeField())
    mnemonic_value = ArrayField(models.FloatField())
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRISSEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRISSEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRSpecEdbBlocksStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_blocks_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRSpecEdbDailyStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_daily_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRSpecEdbEveryChangeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    time = ArrayField(models.DateTimeField())
    mnemonic_value = ArrayField(models.FloatField())
    median = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    dependency_mnemonic = models.CharField(blank=True, null=True)
    dependency_value = models.CharField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_every_change_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRSpecEdbTimeIntervalStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    median = ArrayField(models.FloatField())
    max = ArrayField(models.FloatField())
    min = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_time_interval_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'


class NIRSpecEdbTimeStats(models.Model):
    mnemonic = models.CharField(blank=True, null=True)
    latest_query = models.DateTimeField(blank=True, null=True)
    times = ArrayField(models.DateTimeField())
    data = ArrayField(models.FloatField())
    stdev = ArrayField(models.FloatField())
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_edb_time_stats'
        unique_together = (('id', 'entry_date'),)
        db_table_comments = 'monitors'
