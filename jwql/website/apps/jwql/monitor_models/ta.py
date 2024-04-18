"""Defines the models for the ``jwql`` TA monitors.

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
    MAX_LEN_APERTURE,
    MAX_LEN_DETECTOR,
    MAX_LEN_TIME,
    MAX_LEN_FILENAME,
    MAX_LEN_INSTRUMENT,
    MAX_LEN_NGROUPS,
    MAX_LEN_NINTS,
    MAX_LEN_PATH,
    MAX_LEN_READPATTERN,
    MAX_LEN_SUBARRAY,
)


class MIRITaQueryHistory(models.Model):
    instrument = models.CharField(max_length=MAX_LEN_INSTRUMENT, blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    entries_found = models.IntegerField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "miri_ta_query_history"
        unique_together = (("id", "entry_date"),)


class MIRITaStats(models.Model):
    entry_date = models.DateTimeField(unique=True)
    cal_file_name = models.CharField(max_length=MAX_LEN_FILENAME, blank=True, null=True)
    obs_end_time = models.DateTimeField(blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, blank=True, null=True)
    detector = models.CharField(max_length=MAX_LEN_DETECTOR, blank=True, null=True)
    targx = models.FloatField(blank=True, null=True)
    targy = models.FloatField(blank=True, null=True)
    offset = models.FloatField(blank=True, null=True)
    full_im_path = models.CharField(max_length=MAX_LEN_PATH, blank=True, null=True)
    zoom_im_path = models.CharField(max_length=MAX_LEN_PATH, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "miri_ta_stats"
        unique_together = (("id", "entry_date"),)


class NIRSpecTaQueryHistory(models.Model):
    instrument = models.CharField(max_length=MAX_LEN_INSTRUMENT, blank=True, null=True)
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, blank=True, null=True)
    start_time_mjd = models.FloatField(blank=True, null=True)
    end_time_mjd = models.FloatField(blank=True, null=True)
    entries_found = models.IntegerField(blank=True, null=True)
    files_found = models.IntegerField(blank=True, null=True)
    run_monitor = models.BooleanField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "nirspec_ta_query_history"
        unique_together = (("id", "entry_date"),)


class NIRSpecWataStats(models.Model):
    filename = models.CharField(max_length=MAX_LEN_FILENAME, blank=True, null=True)
    date_obs = models.DateTimeField(blank=True, null=True)
    visit_id = models.CharField(blank=True, null=True)
    tafilter = models.CharField(blank=True, null=True)
    readout = models.CharField(blank=True, null=True)
    ta_status = models.CharField(blank=True, null=True)
    status_reason = models.FloatField(blank=True, null=True)
    star_name = models.IntegerField(blank=True, null=True)
    star_ra = models.FloatField(blank=True, null=True)
    star_dec = models.FloatField(blank=True, null=True)
    star_mag = models.FloatField(blank=True, null=True)
    star_catalog = models.IntegerField(blank=True, null=True)
    planned_v2 = models.FloatField(blank=True, null=True)
    planned_v3 = models.FloatField(blank=True, null=True)
    stamp_start_col = models.IntegerField(blank=True, null=True)
    stamp_start_row = models.IntegerField(blank=True, null=True)
    star_detector = models.CharField(blank=True, null=True)
    max_val_box = models.FloatField(blank=True, null=True)
    max_val_box_col = models.IntegerField(blank=True, null=True)
    max_val_box_row = models.IntegerField(blank=True, null=True)
    iterations = models.IntegerField(blank=True, null=True)
    corr_col = models.IntegerField(blank=True, null=True)
    corr_row = models.IntegerField(blank=True, null=True)
    stamp_final_col = models.FloatField(blank=True, null=True)
    stamp_final_row = models.FloatField(blank=True, null=True)
    detector_final_col = models.FloatField(blank=True, null=True)
    detector_final_row = models.FloatField(blank=True, null=True)
    final_sci_x = models.FloatField(blank=True, null=True)
    final_sci_y = models.FloatField(blank=True, null=True)
    measured_v2 = models.FloatField(blank=True, null=True)
    measured_v3 = models.FloatField(blank=True, null=True)
    ref_v2 = models.FloatField(blank=True, null=True)
    ref_v3 = models.FloatField(blank=True, null=True)
    v2_offset = models.FloatField(blank=True, null=True)
    v3_offset = models.FloatField(blank=True, null=True)
    sam_x = models.FloatField(blank=True, null=True)
    sam_y = models.FloatField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "nirspec_wata_stats"
        unique_together = (("id", "entry_date"),)


class NIRSpecMsataStats(models.Model):
    filename = models.CharField(max_length=MAX_LEN_FILENAME, blank=True, null=True)
    date_obs = models.DateTimeField(blank=True, null=True)
    visit_id = models.CharField(blank=True, null=True)
    tafilter = models.CharField(blank=True, null=True)
    detector = models.CharField(blank=True, null=True)
    readout = models.CharField(blank=True, null=True)
    subarray = models.CharField(blank=True, null=True)
    num_refstars = models.IntegerField(blank=True, null=True)
    ta_status = models.CharField(max_length=MAX_LEN_FILENAME, blank=True, null=True)
    status_rsn = models.FloatField(blank=True, null=True)
    v2halffacet = models.FloatField(blank=True, null=True)
    v3halffacet = models.FloatField(blank=True, null=True)
    v2msactr = models.FloatField(blank=True, null=True)
    v3msactr = models.FloatField(blank=True, null=True)
    lsv2offset = models.FloatField(blank=True, null=True)
    lsv3offset = models.FloatField(blank=True, null=True)
    lsoffsetmag = models.FloatField(blank=True, null=True)
    lsrolloffset = models.FloatField(blank=True, null=True)
    lsv2sigma = models.FloatField(blank=True, null=True)
    lsv3sigma = models.FloatField(blank=True, null=True)
    lsiterations = models.IntegerField(blank=True, null=True)
    guidestarid = models.IntegerField(blank=True, null=True)
    guidestarx = models.FloatField(blank=True, null=True)
    guidestary = models.FloatField(blank=True, null=True)
    guidestarroll = models.FloatField(blank=True, null=True)
    samx = models.FloatField(blank=True, null=True)
    samy = models.FloatField(blank=True, null=True)
    samroll = models.FloatField(blank=True, null=True)
    box_peak_value = ArrayField(models.FloatField())
    reference_star_mag = ArrayField(models.FloatField())
    convergence_status = ArrayField(models.CharField())
    reference_star_number = ArrayField(models.IntegerField())
    lsf_removed_status = ArrayField(models.CharField())
    lsf_removed_reason = ArrayField(models.CharField())
    lsf_removed_x = ArrayField(models.FloatField())
    lsf_removed_y = ArrayField(models.FloatField())
    planned_v2 = ArrayField(models.FloatField())
    planned_v3 = ArrayField(models.FloatField())
    stars_in_fit = models.IntegerField(blank=True, null=True)
    entry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "nirspec_msata_stats"
        unique_together = (("id", "entry_date"),)


class NIRSpecTaStats(models.Model):
    entry_date = models.DateTimeField(blank=True, null=True)
    uncal_filename = models.CharField(
        max_length=MAX_LEN_FILENAME, blank=True, null=True
    )
    aperture = models.CharField(max_length=MAX_LEN_APERTURE, blank=True, null=True)
    detector = models.CharField(max_length=MAX_LEN_DETECTOR, blank=True, null=True)
    subarray = models.CharField(max_length=MAX_LEN_SUBARRAY, blank=True, null=True)
    read_pattern = models.CharField(
        max_length=MAX_LEN_READPATTERN, blank=True, null=True
    )
    nints = models.CharField(max_length=MAX_LEN_NINTS, blank=True, null=True)
    ngroups = models.CharField(max_length=MAX_LEN_NGROUPS, blank=True, null=True)
    expstart = models.CharField(max_length=MAX_LEN_TIME, blank=True, null=True)
    full_image_mean = models.FloatField(blank=True, null=True)
    full_image_stddev = models.FloatField(blank=True, null=True)
    full_image_n = ArrayField(models.FloatField())
    full_image_bin_centers = ArrayField(models.FloatField())
    diff_image_mean = models.FloatField(blank=True, null=True)
    diff_image_stddev = models.FloatField(blank=True, null=True)
    diff_image_n = ArrayField(models.FloatField())
    diff_image_bin_centers = ArrayField(models.FloatField())
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
        db_table = "nirspec_ta_stats"
        unique_together = (("id", "entry_date"),)
