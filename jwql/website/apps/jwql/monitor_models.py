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

class Monitor(models.Model):
    monitor_name = models.CharField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)  # This field type is a guess.
    log_file = models.CharField()

    class Meta:
        managed = True
        db_table = 'monitor'


# ----------------------------------------------------------------------------------------
# FGS 
# ----------------------------------------------------------------------------------------
class FgsBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)


class FgsBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'fgs_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class FgsCosmicRayQueryHistory(models.Model):
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


class FgsCosmicRayStats(models.Model):
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


class FgsReadnoiseQueryHistory(models.Model):
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


class FgsReadnoiseStats(models.Model):
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
    full_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    full_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    diff_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp1_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'fgs_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


# ----------------------------------------------------------------------------------------
# FGS 
# ----------------------------------------------------------------------------------------
class MiriBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)


class MiriBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class MiriCosmicRayQueryHistory(models.Model):
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


class MiriCosmicRayStats(models.Model):
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


class MiriReadnoiseQueryHistory(models.Model):
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


class MiriReadnoiseStats(models.Model):
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
    full_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    full_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    diff_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp1_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'miri_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


class MiriTaQueryHistory(models.Model):
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
        db_table = 'miri_ta_query_history'
        unique_together = (('id', 'entry_date'),)


class MiriTaStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    cal_file_name = models.CharField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    targx = models.FloatField(blank=True, null=True)
    targy = models.FloatField(blank=True, null=True)
    offset = models.FloatField(blank=True, null=True)
    full_im_path = models.CharField(blank=True, null=True)
    zoom_im_path = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'miri_ta_stats'
        unique_together = (('id', 'entry_date'),)


# ----------------------------------------------------------------------------------------
# NIRCam 
# ----------------------------------------------------------------------------------------
class NircamBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)


class NircamBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class NircamBiasQueryHistory(models.Model):
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


class NircamBiasStats(models.Model):
    aperture = models.CharField(blank=True, null=True)
    uncal_filename = models.CharField(blank=True, null=True)
    cal_filename = models.CharField(blank=True, null=True)
    cal_image = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    median = models.FloatField(blank=True, null=True)
    stddev = models.FloatField(blank=True, null=True)
    collapsed_rows = models.TextField(blank=True, null=True)  # This field type is a guess.
    collapsed_columns = models.TextField(blank=True, null=True)  # This field type is a guess.
    counts = models.TextField(blank=True, null=True)  # This field type is a guess.
    bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
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


class NircamClawQueryHistory(models.Model):
    entry_date = models.DateTimeField(blank=True, null=True)
    instrument = models.CharField(blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nircam_claw_query_history'
        unique_together = (('id', 'entry_date'),)


class NircamClawStats(models.Model):
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

    class Meta:
        managed = True
        db_table = 'nircam_claw_stats'
        unique_together = (('id', 'entry_date'),)


class NircamCosmicRayQueryHistory(models.Model):
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


class NircamCosmicRayStats(models.Model):
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


class NircamReadnoiseQueryHistory(models.Model):
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


class NircamReadnoiseStats(models.Model):
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
    full_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    full_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    diff_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp1_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'nircam_readnoise_stats'
        unique_together = (('id', 'entry_date'),)

# ----------------------------------------------------------------------------------------
# NIRISS 
# ----------------------------------------------------------------------------------------
class NirissBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)


class NirissBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'niriss_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class NirissBiasQueryHistory(models.Model):
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


class NirissBiasStats(models.Model):
    aperture = models.CharField(blank=True, null=True)
    uncal_filename = models.CharField(blank=True, null=True)
    cal_filename = models.CharField(blank=True, null=True)
    cal_image = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    median = models.FloatField(blank=True, null=True)
    stddev = models.FloatField(blank=True, null=True)
    collapsed_rows = models.TextField(blank=True, null=True)  # This field type is a guess.
    collapsed_columns = models.TextField(blank=True, null=True)  # This field type is a guess.
    counts = models.TextField(blank=True, null=True)  # This field type is a guess.
    bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
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


class NirissCosmicRayQueryHistory(models.Model):
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


class NirissCosmicRayStats(models.Model):
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


class NirissReadnoiseQueryHistory(models.Model):
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


class NirissReadnoiseStats(models.Model):
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
    full_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    full_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    diff_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp1_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'niriss_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


# ----------------------------------------------------------------------------------------
# NIRSpec 
# ----------------------------------------------------------------------------------------
class NirspecBadPixelQueryHistory(models.Model):
    entry_date = models.DateTimeField(unique=True)
    instrument = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    dark_start_time_mjd = models.FloatField(blank=True, null=True)
    dark_end_time_mjd = models.FloatField(blank=True, null=True)
    flat_start_time_mjd = models.FloatField(blank=True, null=True)
    flat_end_time_mjd = models.FloatField(blank=True, null=True)
    dark_files_found = models.IntegerField(blank=True, null=True)
    flat_files_found = models.IntegerField(blank=True, null=True)
    run_bpix_from_darks = models.BooleanField(blank=True, null=True)
    run_bpix_from_flats = models.BooleanField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_bad_pixel_query_history'
        unique_together = (('id', 'entry_date'),)


class NirspecBadPixelStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    detector = models.CharField(blank=True, null=True)
    x_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    y_coord = models.TextField(blank=True, null=True)  # This field type is a guess.
    type = models.CharField(blank=True, null=True)
    source_files = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_start_time = models.DateTimeField(blank=True, null=True)
    obs_mid_time = models.DateTimeField(blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    baseline_file = models.CharField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_bad_pixel_stats'
        unique_together = (('id', 'entry_date'),)


class NirspecBiasQueryHistory(models.Model):
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


class NirspecBiasStats(models.Model):
    aperture = models.CharField(blank=True, null=True)
    uncal_filename = models.CharField(blank=True, null=True)
    cal_filename = models.CharField(blank=True, null=True)
    cal_image = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    mean = models.FloatField(blank=True, null=True)
    median = models.FloatField(blank=True, null=True)
    stddev = models.FloatField(blank=True, null=True)
    collapsed_rows = models.TextField(blank=True, null=True)  # This field type is a guess.
    collapsed_columns = models.TextField(blank=True, null=True)  # This field type is a guess.
    counts = models.TextField(blank=True, null=True)  # This field type is a guess.
    bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
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


class NirspecCosmicRayQueryHistory(models.Model):
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


class NirspecCosmicRayStats(models.Model):
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


class NirspecGratingQueryHistory(models.Model):
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'nirspec_grating_query_history'
        unique_together = (('id', 'entry_date'),)


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


class NirspecReadnoiseQueryHistory(models.Model):
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


class NirspecReadnoiseStats(models.Model):
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
    full_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    full_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    readnoise_diff_image = models.CharField(blank=True, null=True)
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    diff_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    entry_date = models.DateTimeField(blank=True, null=True)
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp1_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'nirspec_readnoise_stats'
        unique_together = (('id', 'entry_date'),)


class NirspecTaQueryHistory(models.Model):
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
        db_table = 'nirspec_ta_query_history'
        unique_together = (('id', 'entry_date'),)


class NirspecTaStats(models.Model):
    entry_date = models.DateTimeField(blank=True, null=True)
    uncal_filename = models.CharField(blank=True, null=True)
    aperture = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    subarray = models.CharField(blank=True, null=True)
    read_pattern = models.CharField(blank=True, null=True)
    nints = models.CharField(blank=True, null=True)
    ngroups = models.CharField(blank=True, null=True)
    expstart = models.CharField(blank=True, null=True)
    full_image_mean = models.FloatField(blank=True, null=True)
    full_image_stddev = models.FloatField(blank=True, null=True)
    full_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    full_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    diff_image_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp1_mean = models.FloatField(blank=True, null=True)
    amp1_stddev = models.FloatField(blank=True, null=True)
    amp1_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp1_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_mean = models.FloatField(blank=True, null=True)
    amp2_stddev = models.FloatField(blank=True, null=True)
    amp2_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp2_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_mean = models.FloatField(blank=True, null=True)
    amp3_stddev = models.FloatField(blank=True, null=True)
    amp3_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp3_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_mean = models.FloatField(blank=True, null=True)
    amp4_stddev = models.FloatField(blank=True, null=True)
    amp4_n = models.TextField(blank=True, null=True)  # This field type is a guess.
    amp4_bin_centers = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'nirspec_ta_stats'
        unique_together = (('id', 'entry_date'),)


# Below this line are legacy tables (or tables unrelated to the monitors themselves) that
# are not (or should not be) managed by django.
# ----------------------------------------------------------------------------------------
class CentralStorage(models.Model):
    date = models.DateTimeField()
    area = models.CharField()
    size = models.FloatField()
    used = models.FloatField()
    available = models.FloatField()

    class Meta:
        managed = True
        db_table = 'central_storage'


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


class FilesystemCharacteristics(models.Model):
    date = models.DateTimeField()
    instrument = models.TextField()  # This field type is a guess.
    filter_pupil = models.TextField(blank=True, null=True)  # This field type is a guess.
    obs_per_filter_pupil = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'filesystem_characteristics'


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


