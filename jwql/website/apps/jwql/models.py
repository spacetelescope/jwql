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
