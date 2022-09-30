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
    - Bryan Hilbert

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
        ordering = ['instrument']

    # Methods
    #def get_absolute_url(self):
    #    """Returns the URL to access a particular instance of Archive."""
    #    return reverse('archive-view', args=[str(self.id)])

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.instrument


class Proposal(models.Model):
    """A class defining the model used to hold information about a given proposal"""
    # Fields
    prop_id = models.CharField(max_length=5, help_text="5-digit proposal ID string")
    thumbnail_path = models.CharField(max_length=100, help_text='Path to the proposal thumbnail', default='')
    archive = models.ForeignKey(Archive, blank=False, null=False, on_delete=models.CASCADE)

    # Metadata
    class Meta:
        ordering = ['-prop_id']
        unique_together = ('prop_id', 'archive')
        models.UniqueConstraint(fields=['prop_id', 'archive'], name='unique_instrument_proposal')

    # Methods
    #def get_absolute_url(self):
    #    """Returns the URL to access a particular instance of Archive."""
    #    return reverse('proposal-view', args=[str(self.id)])

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
        ordering = ['-obsnum']
        models.UniqueConstraint(fields=['proposal', 'obsnum'], name='unique_proposal_obsnum')

    # Methods
    #def get_absolute_url(self):
    #    """Returns the URL to access a particular instance of Archive."""
    #    return reverse('observation-view', args=[str(self.id)])

    def __str__(self):
        """String for representing the Archive object (in Admin site etc.)."""
        return self.obsnum
