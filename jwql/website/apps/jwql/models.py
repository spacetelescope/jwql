"""Defines the models for the ``jwql`` app.

** CURRENTLY NOT IN USE **

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

import os

from django.db import models

from jwst.datamodels import schemas


INSTRUMENT_LIST = (('FGS', 'FGS'),
                   ('MIRI', 'MIRI'),
                   ('NIRCam', 'NIRCam'),
                   ('NIRISS', 'NIRISS'),
                   ('NIRSpec', 'NIRSpec'))


class BaseModel(models.Model):
    """A base model that other classes will inherit. Created to avoid
    an obscure error about a missing ``app_label``.
    """

    class Meta:
        abstract = True  # specify this model as an Abstract Model
        app_label = 'jwql'


class ImageData(BaseModel):
    """A model that collects image filepaths, instrument labels, and
    publishing date/time. Just an example used for learning django.

    Attributes
    ----------
    filepath : FilePathField object
        The full filepath of the datum
    inst : CharField object
        Name of the corresponding JWST instrument
    pub_date : FilePathField object
        Date and time when datum was added to the database.
    """

    inst = models.CharField('instrument', max_length=7, choices=INSTRUMENT_LIST, default=None)
    pub_date = models.DateTimeField('date published')
    filepath = models.FilePathField(path='/user/lchambers/jwql/')

    def filename(self):
        return os.path.basename(self.filepath)

    def __str__(self):
        return self.filename()

    class Meta:
        verbose_name_plural = "image data"
        db_table = 'imagedata'



class ExposureType(models.Model):
    """A class defining the exposure type for a given observation. Observations can have more
    than one exposure type."""

    # Fields
    #exp_type = models.CharField(max_length=15, help_text="Exposure type abbreviation")

    # Use the exposure type schema entry from the jwst pacakage to create a list of
    # all possible exposure types
    schema_file = os.path.join(os.path.dirname(schemas.__file__), 'core.schema.yaml')
    with open(schema_file, 'r') as fobj:
        temp = yaml.safe_load(fobj)
    exptypes = temp['properties']['meta']['properties']['exposure']['properties']['type']['enum']
    all_exptypes = [(etype, etype) for etype in exptypes]

    exp_type = models.CharField(
        max_length=15,
        choices=all_exptypes,
        blank=False,
        help_text='exposure type',
    )

    class Meta:
        ordering = ['exp_type']

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.exp_type


class Observation(models.Model):
    """
    """
    # Fields
    obsnum = models.CharField(max_length=3, help_text='Observation number, as a 3 digit string')
    number_of_files = models.IntegerField(help_text='Number of files in the proposal')
    exposure_type = models.ManyToManyField(ExposureTypes, blank=False, null=False, on_delete=models.CASCADE)
    obsstart = models.FloatField(help_text='Time of the beginning of the observation in MJD')
    obsend = models.FloatField(help_text='Time of the end of the observation in MJD')

    # …
    # Metadata
    class Meta:
        ordering = ['-obsnum']

    # Methods
    def get_absolute_url(self):
        """Returns the URL to access a particular instance of Archive."""
        return reverse('observation-view', args=[str(self.id)])

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.obsnum


class Proposal(models.Model):
    """
    """
    # Fields
    prop_id = models.CharField(max_length=5, help_text="5-digit proposal ID string")
    observation = models.ForeignKey(Observation, blank=False, null=False, on_delete=models.CASCADE)
    thumbnail_path = models.CharField(max_length=100, help_text='Path to the proposal thumbnail')

    # Metadata
    class Meta:
        ordering = ['-prop_id']

    # Methods
    def get_absolute_url(self):
        """Returns the URL to access a particular instance of Archive."""
        return reverse('proposal-view', args=[str(self.id)])

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.prop_id


class Archive(models.Model):
    """A class defining the model used to hold information needed for the archive pages."""

    # Fields
    instrument = models.CharField(max_length=7, help_text="Instrument name")
    proposal = models.ForeignKey(Proposal, blank=False, null=False, on_delete=models.CASCADE)

    # …
    # Metadata
    class Meta:
        ordering = ['-proposal']

    # Methods
    def get_absolute_url(self):
        """Returns the URL to access a particular instance of Archive."""
        return reverse('archive-view', args=[str(self.id)])

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.instrument
