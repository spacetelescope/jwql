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


class NirspecGratingQueryHistory(models.Model):
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_grating_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecGratingStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    time = models.CharField(blank=True, null=True)
    inrsh_gwa_adcmgain = models.FloatField(blank=True, null=True)
    inrsh_gwa_adcmoffset = models.FloatField(blank=True, null=True)
    inrsh_gwa_motor_vref = models.FloatField(blank=True, null=True)
    prism_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    prism_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)
    mirror_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    mirror_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)
    g140h_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    g140h_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)
    g235h_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    g235h_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)
    g395h_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    g395h_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)
    g140m_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    g140m_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)
    g235m_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    g235m_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)
    g395m_inrsi_c_gwa_x_position = models.FloatField(blank=True, null=True)
    g395m_inrsi_c_gwa_y_position = models.FloatField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_grating_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'
