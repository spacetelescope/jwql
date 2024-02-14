"""Defines the models for the ``jwql`` common monitor database tables.

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


class MonitorRouter:
    """
    A router to control all database operations on models in the
    JWQLDB (monitors) database.
    """

    route_app_labels = {"monitors"}

    def db_for_read(self, model, **hints):
        """
        Attempts to read monitor models go to monitors db.
        """
        if model._meta.app_label in self.route_app_labels:
            return "monitors"
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write  monitor models go to monitors db.
        """
        if model._meta.app_label in self.route_app_labels:
            return "monitors"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between tables in the monitors DB.
        """
        if (
            obj1._meta.app_label in self.route_app_labels
            or obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the monitors apps only appear in the 'monitors' database.
        """
        if app_label in self.route_app_labels:
            return db == "monitors"
        return None


class Monitor(models.Model):
    monitor_name = models.CharField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)  # This field type is a guess.
    log_file = models.CharField()

    class Meta:
        managed = True
        db_table = 'monitor'
        app_label = 'monitors'


class CentralStorage(models.Model):
    date = models.DateTimeField()
    area = models.CharField()
    size = models.FloatField()
    used = models.FloatField()
    available = models.FloatField()

    class Meta:
        managed = True
        db_table = 'central_storage'
        app_label = 'monitors'


class FilesystemCharacteristics(models.Model):
    date = models.DateTimeField()
    instrument = models.TextField()  # This field type is a guess.
    filter_pupil = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_per_filter_pupil = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'filesystem_characteristics'
        app_label = 'monitors'


class FilesystemGeneral(models.Model):
    date = models.DateTimeField(unique=True)
    total_file_count = models.IntegerField()
    total_file_size = models.FloatField()
    fits_file_count = models.IntegerField()
    fits_file_size = models.FloatField()
    used = models.FloatField()
    available = models.FloatField()

    class Meta:
        managed = True
        db_table = 'filesystem_general'
        app_label = 'monitors'


class FilesystemInstrument(models.Model):
    date = models.DateTimeField()
    instrument = models.TextField()  # This field type is a guess.
    filetype = models.TextField()  # This field type is a guess.
    count = models.IntegerField()
    size = models.FloatField()

    class Meta:
        managed = True
        db_table = 'filesystem_instrument'
        unique_together = (('date', 'instrument', 'filetype'),)
        app_label = 'monitors'


class FgsAnomaly(models.Model):
    rootname = models.CharField()
    flag_date = models.DateTimeField()
    user = models.CharField()
    cosmic_ray_shower = models.BooleanField()
    diffraction_spike = models.BooleanField()
    excessive_saturation = models.BooleanField()
    guidestar_failure = models.BooleanField()
    persistence = models.BooleanField()
    crosstalk = models.BooleanField()
    data_transfer_error = models.BooleanField()
    ghost = models.BooleanField()
    snowball = models.BooleanField()
    other = models.BooleanField()

    class Meta:
        managed = True
        db_table = 'fgs_anomaly'
        app_label = 'monitors'


class MiriAnomaly(models.Model):
    rootname = models.CharField()
    flag_date = models.DateTimeField()
    user = models.CharField()
    cosmic_ray_shower = models.BooleanField()
    diffraction_spike = models.BooleanField()
    excessive_saturation = models.BooleanField()
    guidestar_failure = models.BooleanField()
    persistence = models.BooleanField()
    column_pull_up = models.BooleanField()
    internal_reflection = models.BooleanField()
    row_pull_down = models.BooleanField()
    other = models.BooleanField()
    column_pull_down = models.BooleanField()
    mrs_glow = models.BooleanField(db_column='MRS_Glow')  # Field name made lowercase.
    mrs_zipper = models.BooleanField(db_column='MRS_Zipper')  # Field name made lowercase.
    row_pull_up = models.BooleanField()
    lrs_contamination = models.BooleanField(db_column='LRS_Contamination')  # Field name made lowercase.
    tree_rings = models.BooleanField()

    class Meta:
        managed = True
        db_table = 'miri_anomaly'
        app_label = 'monitors'


class NircamAnomaly(models.Model):
    rootname = models.CharField()
    flag_date = models.DateTimeField()
    user = models.CharField()
    cosmic_ray_shower = models.BooleanField()
    diffraction_spike = models.BooleanField()
    excessive_saturation = models.BooleanField()
    guidestar_failure = models.BooleanField()
    persistence = models.BooleanField()
    crosstalk = models.BooleanField()
    data_transfer_error = models.BooleanField()
    ghost = models.BooleanField()
    snowball = models.BooleanField()
    dragons_breath = models.BooleanField()
    other = models.BooleanField()
    scattered_light = models.BooleanField()
    claws = models.BooleanField()
    wisps = models.BooleanField()
    tilt_event = models.BooleanField()

    class Meta:
        managed = True
        db_table = 'nircam_anomaly'
        app_label = 'monitors'


class NirissAnomaly(models.Model):
    rootname = models.CharField()
    flag_date = models.DateTimeField()
    user = models.CharField()
    cosmic_ray_shower = models.BooleanField()
    diffraction_spike = models.BooleanField()
    excessive_saturation = models.BooleanField()
    guidestar_failure = models.BooleanField()
    persistence = models.BooleanField()
    crosstalk = models.BooleanField()
    data_transfer_error = models.BooleanField()
    ghost = models.BooleanField()
    snowball = models.BooleanField()
    other = models.BooleanField()
    scattered_light = models.TextField()
    light_saber = models.TextField()

    class Meta:
        managed = True
        db_table = 'niriss_anomaly'
        app_label = 'monitors'


class NirspecAnomaly(models.Model):
    rootname = models.CharField()
    flag_date = models.DateTimeField()
    user = models.CharField()
    cosmic_ray_shower = models.BooleanField()
    diffraction_spike = models.BooleanField()
    excessive_saturation = models.BooleanField()
    guidestar_failure = models.BooleanField()
    persistence = models.BooleanField()
    crosstalk = models.BooleanField()
    data_transfer_error = models.BooleanField()
    ghost = models.BooleanField()
    snowball = models.BooleanField()
    dominant_msa_leakage = models.BooleanField(db_column='Dominant_MSA_Leakage')  # Field name made lowercase.
    optical_short = models.BooleanField()
    other = models.BooleanField()

    class Meta:
        managed = True
        db_table = 'nirspec_anomaly'
        app_label = 'monitors'
