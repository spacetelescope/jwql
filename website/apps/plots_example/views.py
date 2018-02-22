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
         'MIRI': ['Visual Examination and Anamoly Tracking', 'Dark Current Monitor',
                  'Bad Pixel Monitor', 'Cosmic Ray Monitor', 'Photometry Monitor',
                  'TA Failure Monitor', 'Blind Pointing Accuracy Monitor',
                  'Filter and Calibration Lamp Monitor', 'Thermal Emission Monitor'],
         'NIRCam': ['Visual Examination and Anamoly Tracking', 'Bias Monitor',
                    'Readnoise Monitor', 'Gain Level Monitor',
                    'Mean Dark Current Rate', 'Photometric Stability Monitor'],
         'NIRISS': ['Visual Examination and Anamoly Tracking', 'Bad Pixel Monitor',
                    'Readnoise Monitor', 'AMI Calibrator Monitor', 'TSO RMS Monitor'],
         'NIRSpec': ['Visual Examination and Anaomoly Tracking',
                     'Optical Short Monitoring', 'Target Acquisition Monitor',
                     'Detector Health Monitor', 'Ref Pix Monitor',
                     'Internal Lamp Monitor', 'Instrument Model Updates',
                     'Failed-open Shutter Monitor']}

def index(request):
    context = {'inst_list': INST_LIST,
               'tools': TOOLS}
    return render(request, 'plots_example/index.html', context)

def detail(request, inst):
    # imdat = ImageData.objects.filter(inst=inst)
    imdat = DatabaseConnection().get_filenames_for_instrument(inst)

    # for im in imdat:
    #     file_ext = im.filepath.split('.')[-1]
    #     if file_ext == 'fits':
    #         raise ValueError('Cannot read .fits files')

    return render(request, 'plots_example/detail.html',
                  {'inst': inst,
                   'imdat': imdat,
                   'tools': TOOLS})

