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


class NIRCamClawQueryHistory(models.Model):
    entry_date = models.DateTimeField(blank=True, null=True)
    instrument = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_claw_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRCamClawStats(models.Model):
    entry_date = models.DateTimeField(blank=True, null=True)
    filename = models.CharField(blank=True, null=True)
    proposal = models.CharField(blank=True, null=True)
    obs = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    filter = models.CharField(blank=True, null=True)
    pupil = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    expstart_mjd = models.FloatField(blank=True, null=True)
    effexptm = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    pa_v3 = models.FloatField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    median = models.FloatField(blank=True, null=True)
    stddev = models.FloatField(blank=True, null=True)
    frac_masked = models.FloatField(blank=True, null=True)
    skyflat_filename = models.CharField(blank=True, null=True)
#     doy = models.FloatField(blank=True, null=True)
#     total_bkg = models.FloatField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_claw_stats'
        unique_together = (('id', 'entry_date'),)
