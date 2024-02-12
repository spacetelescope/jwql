"""Defines the models for the ``jwql`` dark current monitors.

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


class FgsDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    amplifier = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_peak = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_width = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_chisq = models.FloatField(blank=True, null=True)
    double_gauss_amplitude1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_amplitude2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_chisq = models.FloatField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    hist_dark_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    hist_amplitudes = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'fgs_dark_dark_current'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FgsDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class FgsDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_dark_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    amplifier = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_peak = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_width = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_chisq = models.FloatField(blank=True, null=True)
    double_gauss_amplitude1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_amplitude2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_chisq = models.FloatField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    hist_dark_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    hist_amplitudes = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'miri_dark_dark_current'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class MiriDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_dark_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    amplifier = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_peak = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_width = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_chisq = models.FloatField(blank=True, null=True)
    double_gauss_amplitude1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_amplitude2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_chisq = models.FloatField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    hist_dark_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    hist_amplitudes = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'nircam_dark_dark_current'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NircamDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_dark_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    amplifier = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_peak = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_width = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_chisq = models.FloatField(blank=True, null=True)
    double_gauss_amplitude1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_amplitude2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_chisq = models.FloatField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    hist_dark_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    hist_amplitudes = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'niriss_dark_dark_current'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirissDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_dark_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(blank=True, null=True)
    amplifier = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    stdev = models.FloatField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_peak = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_width = models.TextField(blank=True, null=True)  # This field type is a guess.
    gauss_chisq = models.FloatField(blank=True, null=True)
    double_gauss_amplitude1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width1 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_amplitude2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_peak2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_width2 = models.TextField(blank=True, null=True)  # This field type is a guess.
    double_gauss_chisq = models.FloatField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    hist_dark_values = models.TextField(blank=True, null=True)  # This field type is a guess.
    hist_amplitudes = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'nirspec_dark_dark_current'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'


class NirspecDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    readpattern = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_dark_query_history'
        unique_together = (('id', 'entry_date'),)
        app_label = 'monitors'
