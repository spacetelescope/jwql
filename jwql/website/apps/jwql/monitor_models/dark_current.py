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
from django.contrib.postgres.fields import ArrayField
from django.db import models

from jwql.utils.constants import (
    DEFAULT_MODEL_CHARFIELD,
    MAX_LEN_AMPLIFIER,
    MAX_LEN_APERTURE,
    MAX_LEN_DETECTOR,
    MAX_LEN_FILENAME,
    MAX_LEN_INSTRUMENT,
    MAX_LEN_READPATTERN,
    MAX_LEN_TYPE,
)


class FGSDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    amplifier = models.CharField(max_length=MAX_LEN_AMPLIFIER, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    mean = models.FloatField(default=0., blank=True, null=True)
    stdev = models.FloatField(default=0., blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = ArrayField(models.FloatField(default=0.))
    gauss_peak = ArrayField(models.FloatField(default=0.))
    gauss_width = ArrayField(models.FloatField(default=0.))
    gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    double_gauss_amplitude1 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak1 = ArrayField(models.FloatField(default=0.))
    double_gauss_width1 = ArrayField(models.FloatField(default=0.))
    double_gauss_amplitude2 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak2 = ArrayField(models.FloatField(default=0.))
    double_gauss_width2 = ArrayField(models.FloatField(default=0.))
    double_gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    hist_dark_values = ArrayField(models.FloatField(default=0.))
    hist_amplitudes = ArrayField(models.FloatField(default=0.))

    class Meta:
        managed = True
        db_table = 'fgs_dark_dark_current'
        unique_together = (('id', 'entry_date'),)


class FGSDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(max_length=MAX_LEN_DETECTOR, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    x_coord = ArrayField(models.IntegerField())
    y_coord = ArrayField(models.IntegerField())
    type = models.CharField(max_length=MAX_LEN_TYPE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    baseline_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class FGSDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(max_length=MAX_LEN_INSTRUMENT, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(default=0, blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_dark_query_history'
        unique_together = (('id', 'entry_date'),)


class MIRIDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    amplifier = models.CharField(max_length=MAX_LEN_AMPLIFIER, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    mean = models.FloatField(default=0., blank=True, null=True)
    stdev = models.FloatField(default=0., blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = ArrayField(models.FloatField(default=0.))
    gauss_peak = ArrayField(models.FloatField(default=0.))
    gauss_width = ArrayField(models.FloatField(default=0.))
    gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    double_gauss_amplitude1 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak1 = ArrayField(models.FloatField(default=0.))
    double_gauss_width1 = ArrayField(models.FloatField(default=0.))
    double_gauss_amplitude2 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak2 = ArrayField(models.FloatField(default=0.))
    double_gauss_width2 = ArrayField(models.FloatField(default=0.))
    double_gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    hist_dark_values = ArrayField(models.FloatField(default=0.))
    hist_amplitudes = ArrayField(models.FloatField(default=0.))

    class Meta:
        managed = True
        db_table = 'miri_dark_dark_current'
        unique_together = (('id', 'entry_date'),)


class MIRIDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(max_length=MAX_LEN_DETECTOR, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    x_coord = ArrayField(models.IntegerField())
    y_coord = ArrayField(models.IntegerField())
    type = models.CharField(max_length=MAX_LEN_TYPE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    baseline_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)

    class Meta:
        managed = True
        db_table = 'miri_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class MIRIDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(max_length=MAX_LEN_INSTRUMENT, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(default=0, blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_dark_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRCamDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    amplifier = models.CharField(max_length=MAX_LEN_AMPLIFIER, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    mean = models.FloatField(default=0., blank=True, null=True)
    stdev = models.FloatField(default=0., blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = ArrayField(models.FloatField(default=0.))
    gauss_peak = ArrayField(models.FloatField(default=0.))
    gauss_width = ArrayField(models.FloatField(default=0.))
    gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    double_gauss_amplitude1 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak1 = ArrayField(models.FloatField(default=0.))
    double_gauss_width1 = ArrayField(models.FloatField(default=0.))
    double_gauss_amplitude2 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak2 = ArrayField(models.FloatField(default=0.))
    double_gauss_width2 = ArrayField(models.FloatField(default=0.))
    double_gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    hist_dark_values = ArrayField(models.FloatField(default=0.))
    hist_amplitudes = ArrayField(models.FloatField(default=0.))

    class Meta:
        managed = True
        db_table = 'nircam_dark_dark_current'
        unique_together = (('id', 'entry_date'),)


class NIRCamDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(max_length=MAX_LEN_DETECTOR, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    x_coord = ArrayField(models.IntegerField())
    y_coord = ArrayField(models.IntegerField())
    type = models.CharField(max_length=MAX_LEN_TYPE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    baseline_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class NIRCamDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(max_length=MAX_LEN_INSTRUMENT, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(default=0, blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_dark_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRISSDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    amplifier = models.CharField(max_length=MAX_LEN_AMPLIFIER, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    mean = models.FloatField(default=0., blank=True, null=True)
    stdev = models.FloatField(default=0., blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = ArrayField(models.FloatField(default=0.))
    gauss_peak = ArrayField(models.FloatField(default=0.))
    gauss_width = ArrayField(models.FloatField(default=0.))
    gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    double_gauss_amplitude1 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak1 = ArrayField(models.FloatField(default=0.))
    double_gauss_width1 = ArrayField(models.FloatField(default=0.))
    double_gauss_amplitude2 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak2 = ArrayField(models.FloatField(default=0.))
    double_gauss_width2 = ArrayField(models.FloatField(default=0.))
    double_gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    hist_dark_values = ArrayField(models.FloatField(default=0.))
    hist_amplitudes = ArrayField(models.FloatField(default=0.))

    class Meta:
        managed = True
        db_table = 'niriss_dark_dark_current'
        unique_together = (('id', 'entry_date'),)


class NIRISSDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(max_length=MAX_LEN_DETECTOR, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    x_coord = ArrayField(models.IntegerField())
    y_coord = ArrayField(models.IntegerField())
    type = models.CharField(max_length=MAX_LEN_TYPE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    baseline_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class NIRISSDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(max_length=MAX_LEN_INSTRUMENT, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(default=0, blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_dark_query_history'
        unique_together = (('id', 'entry_date'),)


class NIRSpecDarkDarkCurrent(models.Model):
    entry_date = models.DateTimeField(unique=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    amplifier = models.CharField(max_length=MAX_LEN_AMPLIFIER, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    mean = models.FloatField(default=0., blank=True, null=True)
    stdev = models.FloatField(default=0., blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    gauss_amplitude = ArrayField(models.FloatField(default=0.))
    gauss_peak = ArrayField(models.FloatField(default=0.))
    gauss_width = ArrayField(models.FloatField(default=0.))
    gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    double_gauss_amplitude1 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak1 = ArrayField(models.FloatField(default=0.))
    double_gauss_width1 = ArrayField(models.FloatField(default=0.))
    double_gauss_amplitude2 = ArrayField(models.FloatField(default=0.))
    double_gauss_peak2 = ArrayField(models.FloatField(default=0.))
    double_gauss_width2 = ArrayField(models.FloatField(default=0.))
    double_gauss_chisq = models.FloatField(default=0., blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    hist_dark_values = ArrayField(models.FloatField(default=0.))
    hist_amplitudes = ArrayField(models.FloatField(default=0.))

    class Meta:
        managed = True
        db_table = 'nirspec_dark_dark_current'
        unique_together = (('id', 'entry_date'),)


class NIRSpecDarkPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(max_length=MAX_LEN_DETECTOR, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    x_coord = ArrayField(models.IntegerField())
    y_coord = ArrayField(models.IntegerField())
    type = models.CharField(max_length=MAX_LEN_TYPE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    source_files = ArrayField(models.CharField(max_length=MAX_LEN_FILENAME, help_text="source file names"),
                                               default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    mean_dark_image_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)
    baseline_file = models.CharField(max_length=MAX_LEN_FILENAME, default=DEFAULT_MODEL_CHARFIELD, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_dark_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class NIRSpecDarkQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(max_length=MAX_LEN_INSTRUMENT, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    readpattern = models.CharField(max_length=MAX_LEN_READPATTERN, default=DEFAULT_MODEL_CHARFIELD, blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    files_found = models.IntegerField(default=0, blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_dark_query_history'
        unique_together = (('id', 'entry_date'),)
