"""Defines the models for the ``jwql`` app.

In Django, "a model is the single, definitive source of information
about your data. It contains the essential fields and behaviors of the
data you’re storing. Generally, each model maps to a single database
table" (from Django documentation). Each model contains fields, such
as character fields or date/time fields, that function like columns in
a data table. This module defines models that might be used to store
data related to the JWQL webpage. Interacts with the database located
at jwql/website/db.sqlite3.

Authors
-------
    - Lauren Chambers
    - Bryan Hilbert
    - Brad Sappington
Use
---
    This module is used as such:

    ::
        from models import MyModel
        data = MyModel.objects.filter(name="JWQL")

References
----------
    For more information please see:
        ```https://docs.djangoproject.com/en/2.0/topics/db/models/```
"""

from django.db import models


INSTRUMENT_LIST = (('FGS', 'FGS'),
                   ('MIRI', 'MIRI'),
                   ('NIRCam', 'NIRCam'),
                   ('NIRISS', 'NIRISS'),
                   ('NIRSpec', 'NIRSpec'))


class Archive(models.Model):
    """A class defining the model used to hold information needed for the archive pages."""

    # Fields
    instrument = models.CharField(max_length=7, help_text="Instrument name", primary_key=True)

    # …
    # Metadata
    class Meta:
        app_label = 'jwql'
        ordering = ['instrument']

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.instrument


class Proposal(models.Model):
    """A class defining the model used to hold information about a given proposal"""
    # Fields
    prop_id = models.CharField(max_length=5, help_text="5-digit proposal ID string")
    thumbnail_path = models.CharField(max_length=100, help_text='Path to the proposal thumbnail', default='')
    archive = models.ForeignKey(Archive, blank=False, null=False, on_delete=models.CASCADE)
    category = models.CharField(max_length=10, help_text="Category Type", default='')

    # Metadata
    class Meta:
        app_label = 'jwql'
        ordering = ['-prop_id']
        unique_together = ('prop_id', 'archive')
        models.UniqueConstraint(fields=['prop_id', 'archive'], name='unique_instrument_proposal')

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.prop_id


class Observation(models.Model):
    """A class defining the model used to hold information about an observation from a given proposal"""
    # Fields
    obsnum = models.CharField(max_length=3, help_text='Observation number, as a 3 digit string')
    number_of_files = models.IntegerField(help_text='Number of files in the proposal', default=0)
    obsstart = models.FloatField(help_text='Time of the beginning of the observation in MJD', default=0.)
    obsend = models.FloatField(help_text='Time of the end of the observation in MJD', default=0.)
    proposal = models.ForeignKey(Proposal, blank=False, null=False, on_delete=models.CASCADE)
    exptypes = models.CharField(max_length=100, help_text='Comma-separated list of exposure types', default='')

    # …
    # Metadata
    class Meta:
        app_label = 'jwql'
        ordering = ['-obsnum']
        models.UniqueConstraint(fields=['proposal', 'obsnum'], name='unique_proposal_obsnum')

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.obsnum


class RootFileInfo(models.Model):
    """ All info stored with root file for ease of sorting """
    instrument = models.CharField(max_length=7, help_text="Instrument name")
    obsnum = models.ForeignKey(Observation, blank=False, null=False, on_delete=models.CASCADE)
    proposal = models.CharField(max_length=5, help_text="5-digit proposal ID string")
    root_name = models.TextField(primary_key=True, max_length=300)
    viewed = models.BooleanField(default=False)
    filter = models.CharField(max_length=7, help_text="Instrument name", default='', null=True, blank=True)
    aperture = models.CharField(max_length=40, help_text="Aperture", default='', null=True, blank=True)
    detector = models.CharField(max_length=40, help_text="Detector", default='', null=True, blank=True)
    read_patt_num = models.IntegerField(help_text='Read Pattern Number', default=0)
    read_patt = models.CharField(max_length=40, help_text="Read Pattern", default='', null=True, blank=True)
    grating = models.CharField(max_length=40, help_text="Grating", default='', null=True, blank=True)
    subarray = models.CharField(max_length=40, help_text="Subarray", default='', null=True, blank=True)
    pupil = models.CharField(max_length=40, help_text="Pupil", default='', null=True, blank=True)
    exp_type = models.CharField(max_length=40, help_text="Exposure Type", default='', null=True, blank=True)
    expstart = models.FloatField(help_text='Exposure Start Time', default=0.0)

    # Metadata
    class Meta:
        app_label = 'jwql'
        ordering = ['-root_name']

    def __str__(self):
        """String for representing the RootFileInfo object (in Admin site etc.)."""
        return self.root_name


class Anomalies(models.Model):
    """ All Potential Anomalies that can be associated with a RootFileInfo """
    # Note: Using one to one relationship.  Cann access Anomalies by 'rootfileinfo_object.anomalies'
    root_file_info = models.OneToOneField(
        RootFileInfo,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    flag_date = models.DateTimeField(help_text="flag date", null=True, blank=True)
    user = models.CharField(max_length=50, help_text="user", default='', null=True, blank=True)
    cosmic_ray_shower = models.BooleanField(default=False)
    diffraction_spike = models.BooleanField(default=False)
    excessive_saturation = models.BooleanField(default=False)
    guidestar_failure = models.BooleanField(default=False)
    persistence = models.BooleanField(default=False)
    crosstalk = models.BooleanField(default=False)
    data_transfer_error = models.BooleanField(default=False)
    ghost = models.BooleanField(default=False)
    unusual_snowballs = models.BooleanField(default=False)
    column_pull_up = models.BooleanField(default=False)
    column_pull_down = models.BooleanField(default=False)
    noticeable_msa_leakage = models.BooleanField(default=False)
    dragons_breath = models.BooleanField(default=False)
    mrs_glow = models.BooleanField(default=False)
    mrs_zipper = models.BooleanField(default=False)
    internal_reflection = models.BooleanField(default=False)
    new_short = models.BooleanField(default=False)
    row_pull_up = models.BooleanField(default=False)
    row_pull_down = models.BooleanField(default=False)
    lrs_contamination = models.BooleanField(default=False)
    tree_rings = models.BooleanField(default=False)
    scattered_light = models.BooleanField(default=False)
    claws = models.BooleanField(default=False)
    wisps = models.BooleanField(default=False)
    tilt_event = models.BooleanField(default=False)
    light_saber = models.BooleanField(default=False)
    other = models.BooleanField(default=False)

    def get_marked_anomalies(self):
        """Return all boolean field names (anomalies) currently set"""
        true_anomalies = []
        for field, value in vars(self).items():
            if isinstance(value, bool) and value:
                true_anomalies.append(field)
        return true_anomalies

    @classmethod
    def get_all_anomalies(cls):
        """Return list of all anomalies (assumed as any field with default of False)"""
        return [f.name for f in cls._meta.fields if isinstance(f.default, bool)]

    class Meta:
        app_label = 'jwql'
        ordering = ['-root_file_info']

    def __str__(self):
        """Container for all anomalies associated with each RootFileInfo object """
        return self.root_file_info.root_name
