from django.shortcuts import render, get_object_or_404
from django.views import generic

from .models import ImageData
from .db import DatabaseConnection

# class IndexView(generic.ListView):
#     template_name = 'plots_example/index.html'
#     context_object_name = 'latest_question_list'

#     def get_queryset(self):
#         """Return the last five published questions (not including those set to
#         be published in the future)"""
#         return Question.objects.filter(pub_dat__lte=timezone.now()).\
#                                 order_by('-pub_dat')[:5]

app_name = 'plots_example'

INST_LIST = ['FGS', 'MIRI', 'NIRCam', 'NIRISS', 'NIRSpec']
TOOLS = {'FGS': ['Bad Pixel Monitor'],
         'MIRI': ['Dark Current Monitor',
                  'Bad Pixel Monitor', 'Cosmic Ray Monitor', 'Photometry Monitor',
                  'TA Failure Monitor', 'Blind Pointing Accuracy Monitor',
                  'Filter and Calibration Lamp Monitor', 'Thermal Emission Monitor'],
         'NIRCam': ['Bias Monitor',
                    'Readnoise Monitor', 'Gain Level Monitor',
                    'Mean Dark Current Rate Monitor', 'Photometric Stability Monitor'],
         'NIRISS': ['Bad Pixel Monitor',
                    'Readnoise Monitor', 'AMI Calibrator Monitor', 'TSO RMS Monitor'],
         'NIRSpec': ['Optical Short Monitor', 'Target Acquisition Monitor',
                     'Detector Health Monitor', 'Ref Pix Monitor',
                     'Internal Lamp Monitor', 'Instrument Model Updates',
                     'Failed-open Shutter Monitor']}

def home(request):
    template = 'plots_example/home.html'
    context = {'inst_list': INST_LIST,
               'tools': TOOLS}
    return render(request, template, context)

def instrument(request, inst):
    imdat = DatabaseConnection().get_filenames_for_instrument(inst)
    template = 'plots_example/instrument.html'
    return render(request, template,
                  {'inst': inst,
                   'imdat': imdat,
                   'tools': TOOLS})

def view_image(request, inst, file):
    template = 'plots_example/view_image.html'
    return render(request, template,
                  {'inst': inst,
                   'file': file,
                   'tools': TOOLS})

def unlooked_images(request, inst):
    imdat = DatabaseConnection().get_filenames_for_instrument(inst)
    template = 'plots_example/unlooked.html'
    return render(request, template,
                  {'inst': inst,
                   'imdat': imdat,
                   'tools': TOOLS})