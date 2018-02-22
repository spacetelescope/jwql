import datetime
import os

from django.db import models

INSTRUMENT_LIST = (('FGS', 'FGS'),
                   ('MIRI', 'MIRI'),
                   ('NIRCam', 'NIRCam'),
                   ('NIRISS', 'NIRISS'),
                   ('NIRSpec', 'NIRSpec'))

# Define this BaseModel to avoid an obscure error about a missing app_label
class BaseModel(models.Model):
    class Meta:
        abstract = True  # specify this model as an Abstract Model
        app_label = 'plots_example'

class ImageData(BaseModel):
    inst = models.CharField('instrument', max_length=6, choices=INSTRUMENT_LIST, default=None)
    pub_date = models.DateTimeField('date published')
    filepath = models.FilePathField(path='/user/lchambers/jwql/')#upload_to=str(inst))

    def filename(self):
        return os.path.basename(self.filepath)

    def __str__(self):
        return self.filename()

    class Meta:
        verbose_name_plural = "image data"
        db_table = 'imagedata'
