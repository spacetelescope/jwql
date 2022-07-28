"""Defines the forms for the ``jwql`` web app.

Django allows for an object-oriented model representation of forms for
users to provide input through HTTP POST methods. This module defines
all of the forms that are used across the various webpages used for the
JWQL application.

Authors
-------

    - Lauren Chambers
    - Johannes Sahlmann
    - Matthew Bourque
    - Teagan King
    - Mike Engesser

Use
---

    This module is used within ``views.py`` as such:
    ::

        from .forms import FileSearchForm
        def view_function(request):
            form = FileSearchForm(request.POST or None)

            if request.method == 'POST':
                if form.is_valid():
                    # Process form input and redirect
                    return redirect(new_url)

            template = 'some_template.html'
            context = {'form': form, ...}
            return render(request, template, context)

References
----------
    For more information please see:
        ``https://docs.djangoproject.com/en/2.1/topics/forms/``

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql`` directory.
"""

import datetime
import glob
import os

from astropy.time import Time, TimeDelta
from django import forms
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from jwedb.edb_interface import is_valid_mnemonic

from jwql.database import database_interface as di
from jwql.utils.constants import ANOMALY_CHOICES_PER_INSTRUMENT
from jwql.utils.constants import ANOMALIES_PER_INSTRUMENT
from jwql.utils.constants import APERTURES_PER_INSTRUMENT
from jwql.utils.constants import DETECTOR_PER_INSTRUMENT
from jwql.utils.constants import EXP_TYPE_PER_INSTRUMENT
from jwql.utils.constants import FILTERS_PER_INSTRUMENT
from jwql.utils.constants import GENERIC_SUFFIX_TYPES
from jwql.utils.constants import GRATING_PER_INSTRUMENT
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_SHORTHAND
from jwql.utils.constants import READPATT_PER_INSTRUMENT
from jwql.utils.utils import get_config, filename_parser
from jwql.utils.utils import query_format

from wtforms import SubmitField, StringField


class BaseForm(forms.Form):
    """A generic form with target resolve built in"""
    # Target Resolve
    targname = StringField('targname', default='')
    target_url = StringField('target_url', default='')

    # Submit button
    resolve_submit = SubmitField('Resolve Target')


class AnomalyQueryForm(BaseForm):
    """Form validation for the anomaly viewing tool"""

    # Form submits
    calculate_submit = SubmitField()

    # Generate lists of form options for each instrument
    params = {}
    for instrument in ['miri', 'niriss', 'nircam', 'nirspec', 'fgs']:
        params[instrument] = {}
        params[instrument]['aperture_list'] = []
        params[instrument]['filter_list'] = []
        params[instrument]['detector_list'] = []
        params[instrument]['readpatt_list'] = []
        params[instrument]['exptype_list'] = []
        params[instrument]['grating_list'] = []
        params[instrument]['anomalies_list'] = []
        # Generate dynamic lists of apertures to use in forms
        for aperture in APERTURES_PER_INSTRUMENT[instrument.upper()]:
            params[instrument]['aperture_list'].append([query_format(aperture), query_format(aperture)])
        # Generate dynamic lists of filters to use in forms
        for filt in FILTERS_PER_INSTRUMENT[instrument]:
            filt = query_format(filt)
            params[instrument]['filter_list'].append([filt, filt])
        # Generate dynamic lists of detectors to use in forms
        for detector in DETECTOR_PER_INSTRUMENT[instrument]:
            detector = query_format(detector)
            params[instrument]['detector_list'].append([detector, detector])
        # Generate dynamic lists of read patterns to use in forms
        for readpatt in READPATT_PER_INSTRUMENT[instrument]:
            readpatt = query_format(readpatt)
            params[instrument]['readpatt_list'].append([readpatt, readpatt])
        # Generate dynamic lists of exposure types to use in forms
        for exptype in EXP_TYPE_PER_INSTRUMENT[instrument]:
            exptype = query_format(exptype)
            params[instrument]['exptype_list'].append([exptype, exptype])
        # Generate dynamic lists of grating options to use in forms
        for grating in GRATING_PER_INSTRUMENT[instrument]:
            grating = query_format(grating)
            params[instrument]['grating_list'].append([grating, grating])
        # Generate dynamic lists of anomalies to use in forms
        for anomaly in ANOMALIES_PER_INSTRUMENT.keys():
            if instrument in ANOMALIES_PER_INSTRUMENT[anomaly]:
                item = [query_format(anomaly), query_format(anomaly)]
                params[instrument]['anomalies_list'].append(item)

    # Anomaly Parameters
    instrument = forms.MultipleChoiceField(required=False,
                                           choices=[(inst, JWST_INSTRUMENT_NAMES_MIXEDCASE[inst]) for inst in JWST_INSTRUMENT_NAMES_MIXEDCASE],
                                           widget=forms.CheckboxSelectMultiple)
    exp_time_max = forms.DecimalField(required=False, initial="685")
    exp_time_min = forms.DecimalField(required=False, initial="680")

    miri_aper = forms.MultipleChoiceField(required=False, choices=params['miri']['aperture_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_aper = forms.MultipleChoiceField(required=False, choices=params['nirspec']['aperture_list'], widget=forms.CheckboxSelectMultiple)
    niriss_aper = forms.MultipleChoiceField(required=False, choices=params['niriss']['aperture_list'], widget=forms.CheckboxSelectMultiple)
    nircam_aper = forms.MultipleChoiceField(required=False, choices=params['nircam']['aperture_list'], widget=forms.CheckboxSelectMultiple)
    fgs_aper = forms.MultipleChoiceField(required=False, choices=params['fgs']['aperture_list'], widget=forms.CheckboxSelectMultiple)

    miri_filt = forms.MultipleChoiceField(required=False, choices=params['miri']['filter_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_filt = forms.MultipleChoiceField(required=False, choices=params['nirspec']['filter_list'], widget=forms.CheckboxSelectMultiple)
    niriss_filt = forms.MultipleChoiceField(required=False, choices=params['niriss']['filter_list'], widget=forms.CheckboxSelectMultiple)
    nircam_filt = forms.MultipleChoiceField(required=False, choices=params['nircam']['filter_list'], widget=forms.CheckboxSelectMultiple)
    fgs_filt = forms.MultipleChoiceField(required=False, choices=params['fgs']['filter_list'], widget=forms.CheckboxSelectMultiple)

    miri_detector = forms.MultipleChoiceField(required=False, choices=params['miri']['detector_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_detector = forms.MultipleChoiceField(required=False, choices=params['nirspec']['detector_list'], widget=forms.CheckboxSelectMultiple)
    niriss_detector = forms.MultipleChoiceField(required=False, choices=params['niriss']['detector_list'], widget=forms.CheckboxSelectMultiple)
    nircam_detector = forms.MultipleChoiceField(required=False, choices=params['nircam']['detector_list'], widget=forms.CheckboxSelectMultiple)
    fgs_detector = forms.MultipleChoiceField(required=False, choices=params['fgs']['detector_list'], widget=forms.CheckboxSelectMultiple)

    miri_anomalies = forms.MultipleChoiceField(required=False, choices=params['miri']['anomalies_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_anomalies = forms.MultipleChoiceField(required=False, choices=params['nirspec']['anomalies_list'], widget=forms.CheckboxSelectMultiple)
    niriss_anomalies = forms.MultipleChoiceField(required=False, choices=params['niriss']['anomalies_list'], widget=forms.CheckboxSelectMultiple)
    nircam_anomalies = forms.MultipleChoiceField(required=False, choices=params['nircam']['anomalies_list'], widget=forms.CheckboxSelectMultiple)
    fgs_anomalies = forms.MultipleChoiceField(required=False, choices=params['fgs']['anomalies_list'], widget=forms.CheckboxSelectMultiple)

    miri_readpatt = forms.MultipleChoiceField(required=False, choices=params['miri']['readpatt_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_readpatt = forms.MultipleChoiceField(required=False, choices=params['nirspec']['readpatt_list'], widget=forms.CheckboxSelectMultiple)
    niriss_readpatt = forms.MultipleChoiceField(required=False, choices=params['niriss']['readpatt_list'], widget=forms.CheckboxSelectMultiple)
    nircam_readpatt = forms.MultipleChoiceField(required=False, choices=params['nircam']['readpatt_list'], widget=forms.CheckboxSelectMultiple)
    fgs_readpatt = forms.MultipleChoiceField(required=False, choices=params['fgs']['readpatt_list'], widget=forms.CheckboxSelectMultiple)

    miri_exptype = forms.MultipleChoiceField(required=False, choices=params['miri']['exptype_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_exptype = forms.MultipleChoiceField(required=False, choices=params['nirspec']['exptype_list'], widget=forms.CheckboxSelectMultiple)
    niriss_exptype = forms.MultipleChoiceField(required=False, choices=params['niriss']['exptype_list'], widget=forms.CheckboxSelectMultiple)
    nircam_exptype = forms.MultipleChoiceField(required=False, choices=params['nircam']['exptype_list'], widget=forms.CheckboxSelectMultiple)
    fgs_exptype = forms.MultipleChoiceField(required=False, choices=params['fgs']['exptype_list'], widget=forms.CheckboxSelectMultiple)

    miri_grating = forms.MultipleChoiceField(required=False, choices=params['miri']['grating_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_grating = forms.MultipleChoiceField(required=False, choices=params['nirspec']['grating_list'], widget=forms.CheckboxSelectMultiple)
    niriss_grating = forms.MultipleChoiceField(required=False, choices=params['niriss']['grating_list'], widget=forms.CheckboxSelectMultiple)
    nircam_grating = forms.MultipleChoiceField(required=False, choices=params['nircam']['grating_list'], widget=forms.CheckboxSelectMultiple)
    fgs_grating = forms.MultipleChoiceField(required=False, choices=params['fgs']['grating_list'], widget=forms.CheckboxSelectMultiple)

    def clean_inst(self):

        inst = self.cleaned_data['instrument']

        return inst


class InstrumentAnomalySubmitForm(forms.Form):
    """A multiple choice field for specifying flagged anomalies."""

    def __init__(self, *args, **kwargs):
        instrument = kwargs.pop('instrument')
        super(InstrumentAnomalySubmitForm, self).__init__(*args, **kwargs)
        self.fields['anomaly_choices'] = forms.MultipleChoiceField(choices=ANOMALY_CHOICES_PER_INSTRUMENT[instrument], widget=forms.CheckboxSelectMultiple())
        self.instrument = instrument

    def update_anomaly_table(self, rootname, user, anomaly_choices):
        """Updated the ``anomaly`` table of the database with flagged
        anomaly information

        Parameters
        ----------
        rootname : str
            The rootname of the image to flag (e.g.
            ``jw86600008001_02101_00001_guider2``)
        user : str
            The user that is flagging the anomaly
        anomaly_choices : list
            A list of anomalies that are to be flagged (e.g.
            ``['snowball', 'crosstalk']``)
        """

        data_dict = {}
        data_dict['rootname'] = rootname
        data_dict['flag_date'] = datetime.datetime.now()
        data_dict['user'] = user
        for choice in anomaly_choices:
            data_dict[choice] = True
        if self.instrument == 'fgs':
            di.engine.execute(di.FGSAnomaly.__table__.insert(), data_dict)
        elif self.instrument == 'nirspec':
            di.engine.execute(di.NIRSpecAnomaly.__table__.insert(), data_dict)
        elif self.instrument == 'miri':
            di.engine.execute(di.MIRIAnomaly.__table__.insert(), data_dict)
        elif self.instrument == 'niriss':
            di.engine.execute(di.NIRISSAnomaly.__table__.insert(), data_dict)
        elif self.instrument == 'nircam':
            di.engine.execute(di.NIRCamAnomaly.__table__.insert(), data_dict)

    def clean_anomalies(self):

        anomalies = self.cleaned_data['anomaly_choices']

        return anomalies


class FileSearchForm(forms.Form):
    """Single-field form to search for a proposal or fileroot."""

    # Define search field
    search = forms.CharField(label='', max_length=500, required=True,
                             empty_value='Search')

    fileroot_dict = None
    search_type = None
    instrument = None

    def clean_search(self):
        """Validate the "search" field.

        Check that the input is either a proposal or fileroot, and one
        that matches files in the filesystem.

        Returns
        -------
        str
            The cleaned data input into the "search" field
        """

        # Get the cleaned search data
        search = self.cleaned_data['search']

        # Make sure the search is either a proposal or fileroot
        if search.isnumeric() and 1 < int(search) < 99999:
            self.search_type = 'proposal'
        elif self._search_is_fileroot(search):
            self.search_type = 'fileroot'
        else:
            raise forms.ValidationError('Invalid search term {}. Please provide proposal number '
                                        'or file root.'.format(search))

        # If they searched for a proposal...
        if self.search_type == 'proposal':
            # See if there are any matching proposals and, if so, what
            # instrument they are for
            proposal_string = '{:05d}'.format(int(search))
            search_string_public = os.path.join(get_config()['filesystem'], 'public', 'jw{}'.format(proposal_string), '*', '*{}*.fits'.format(proposal_string))
            search_string_proprietary = os.path.join(get_config()['filesystem'], 'proprietary', 'jw{}'.format(proposal_string), '*', '*{}*.fits'.format(proposal_string))
            all_files = glob.glob(search_string_public)
            all_files.extend(glob.glob(search_string_proprietary))

            # Ignore "original" files
            all_files = [filename for filename in all_files if 'original' not in filename]

            if len(all_files) > 0:
                all_instruments = []
                all_observations = []
                for file in all_files:
                    instrument = filename_parser(file)['instrument']
                    observation = filename_parser(file)['observation']
                    all_instruments.append(instrument)
                    all_observations.append(observation)

                all_observations = sorted(all_observations)

                if len(set(all_instruments)) > 1:
                    instrument_routes = ['<a href="/{}/archive/{}/obs{}">{}</a>'.format(instrument, proposal_string[1:], all_observations[0], instrument) for instrument in set(all_instruments)]
                    raise forms.ValidationError(
                        mark_safe(('Proposal contains multiple instruments, please click instrument link to view data: {}.').format(', '.join(instrument_routes))))

                self.instrument = all_instruments[0]
            else:
                raise forms.ValidationError('Proposal {} not in the filesystem.'.format(search))

        # If they searched for a fileroot...
        elif self.search_type == 'fileroot':
            # See if there are any matching fileroots and, if so, what instrument they are for
            search_string_public = os.path.join(get_config()['filesystem'], 'public', search[:7], search[:13], '{}*.fits'.format(search))
            search_string_proprietary = os.path.join(get_config()['filesystem'], 'proprietary', search[:7], search[:13], '{}*.fits'.format(search))
            all_files = glob.glob(search_string_public)
            all_files.extend(glob.glob(search_string_proprietary))

            # Ignore "original" files
            all_files = [filename for filename in all_files if 'original' not in filename]

            if len(all_files) == 0:
                raise forms.ValidationError('Fileroot {} not in the filesystem.'.format(search))

            instrument = search.split('_')[-1][:3]
            self.instrument = JWST_INSTRUMENT_NAMES_SHORTHAND[instrument]

        return self.cleaned_data['search']

    def _search_is_fileroot(self, search):
        """Determine if a search value is formatted like a fileroot.

        Parameters
        ----------
        search : str
            The search term input by the user.

        Returns
        -------
        bool
            Is the search term formatted like a fileroot?
        """

        try:
            self.fileroot_dict = filename_parser(search)
            return True
        except ValueError:
            return False

    def redirect_to_files(self):
        """Determine where to redirect the web app based on user input.

        Returns
        -------
        HttpResponseRedirect object
            Outgoing redirect response sent to the webpage

        """

        # Process the data in form.cleaned_data as required
        search = self.cleaned_data['search']

        # If they searched for a proposal
        if self.search_type == 'proposal':
            proposal_string = '{:05d}'.format(int(search))
            return redirect('/{}/archive/{}'.format(self.instrument, proposal_string))

        # If they searched for a file root
        elif self.search_type == 'fileroot':
            return redirect('/{}/{}'.format(self.instrument, search))


class FiletypeForm(forms.Form):
    """Creates a ``FiletypeForm`` object that allows for ``filetype``
    input in a form field."""

    file_type_list = []
    for filetype in GENERIC_SUFFIX_TYPES:
        item = [filetype, filetype]
        file_type_list.append(item)
    filetype = forms.MultipleChoiceField(required=False, choices=file_type_list, widget=forms.CheckboxSelectMultiple)

    def clean_filetypes(self):

        file_types = self.cleaned_data['filetype']

        return file_types


class MnemonicSearchForm(forms.Form):
    """A single-field form to search for a mnemonic in the DMS EDB."""

    # Define search field
    search = forms.CharField(label='', max_length=500, required=True,
                             empty_value='Search', initial='SA_ZFGOUTFOV')

    # Initialize attributes
    search_type = None

    def __init__(self, *args, **kwargs):
        try:
            self.logged_in = kwargs.pop('logged_in')
        except KeyError:
            self.logged_in = True

        super(MnemonicSearchForm, self).__init__(*args, **kwargs)

    def clean_search(self):
        """Validate the "search" field.

        Check that the input is a valid mnemonic identifier.

        Returns
        -------
        str
            The cleaned data input into the "search" field

        """
        # Stop now if not logged in
        if not self.logged_in:
            raise forms.ValidationError('Could not log into MAST. Please login or provide MAST '
                                        'token in environment variable or config.json.')

        # Get the cleaned search data
        search = self.cleaned_data['search']

        # Make sure the search is a valid mnemonic identifier
        if is_valid_mnemonic(search):
            self.search_type = 'mnemonic'
        else:
            raise forms.ValidationError('Invalid search term {}. Please enter a valid DMS EDB '
                                        'mnemonic.'.format(search))

        return self.cleaned_data['search']


class MnemonicQueryForm(forms.Form):
    """A triple-field form to query mnemonic records in the DMS EDB."""

    production_mode = False

    if production_mode:
        # times for default query (one day one week ago)
        now = Time.now()
        delta_day = -7.
        range_day = 1.
        default_start_time = now + TimeDelta(delta_day, format='jd')
        default_end_time = now + TimeDelta(delta_day + range_day, format='jd')
    else:
        # example for testing
        default_start_time = Time('2019-04-02 00:00:00.000', format='iso')
        default_end_time = Time('2019-04-02 00:01:00.000', format='iso')

    default_mnemonic_identifier = 'IMIR_HK_ICE_SEC_VOLT4'

    # Define search fields
    search = forms.CharField(label='mnemonic', max_length=500, required=True,
                             initial=default_mnemonic_identifier, empty_value='Search',
                             help_text="Mnemonic identifier")

    start_time = forms.CharField(label='start', max_length=500, required=False,
                                 initial=default_start_time.iso, help_text="Start time")

    end_time = forms.CharField(label='end', max_length=500, required=False,
                               initial=default_end_time.iso, help_text="End time")

    # Initialize attributes
    search_type = None

    def __init__(self, *args, **kwargs):
        try:
            self.logged_in = kwargs.pop('logged_in')
        except KeyError:
            self.logged_in = True

        super(MnemonicQueryForm, self).__init__(*args, **kwargs)

    def clean_search(self):
        """Validate the "search" field.

        Check that the input is a valid mnemonic identifier.

        Returns
        -------
        str
            The cleaned data input into the "search" field
        """

        # Stop now if not logged in
        if not self.logged_in:
            raise forms.ValidationError('Could not log into MAST. Please login or provide MAST '
                                        'token in environment variable or config.json.')

        # Get the cleaned search data
        search = self.cleaned_data['search']

        if is_valid_mnemonic(search):
            self.search_type = 'mnemonic'
        else:
            raise forms.ValidationError('Invalid search term {}. Please enter a valid DMS EDB '
                                        'mnemonic.'.format(search))

        return self.cleaned_data['search']

    def clean_start_time(self):
        """Validate the start time.

        Returns
        -------
        str
           The cleaned data input into the start_time field
        """

        start_time = self.cleaned_data['start_time']
        try:
            Time(start_time, format='iso')
        except ValueError:
            raise forms.ValidationError('Invalid start time {}. Please enter a time in iso format, '
                                        'e.g. {}'.format(start_time, self.default_start_time))

        return self.cleaned_data['start_time']

    def clean_end_time(self):
        """Validate the end time.

        Returns
        -------
        str
           The cleaned data input into the end_time field
        """

        end_time = self.cleaned_data['end_time']
        try:
            Time(end_time, format='iso')
        except ValueError:
            raise forms.ValidationError('Invalid end time {}. Please enter a time in iso format, '
                                        'e.g. {}.'.format(end_time, self.default_end_time))

        if 'start_time' in self.cleaned_data.keys():
            # verify that end_time is later than start_time
            if self.cleaned_data['end_time'] <= self.cleaned_data['start_time']:
                raise forms.ValidationError('Invalid time inputs. End time is required to be after'
                                            ' Start time.')

        return self.cleaned_data['end_time']


class MnemonicExplorationForm(forms.Form):
    """A sextuple-field form to explore the EDB mnemonic inventory."""

    default_description = 'centroid data'

    # Define search fields
    description = forms.CharField(label='description', max_length=500, required=False,
                                  initial=default_description, help_text="Description")
    sql_data_type = forms.CharField(label='sqlDataType', max_length=500, required=False,
                                    help_text="sqlDataType")
    subsystem = forms.CharField(label='subsystem', max_length=500, required=False,
                                help_text="subsystem")
    tlm_identifier = forms.CharField(label='tlmIdentifier', max_length=500, required=False,
                                     help_text="Numerical ID (tlmIdentifier)")
    tlm_mnemonic = forms.CharField(label='tlmMnemonic', max_length=500, required=False,
                                   help_text="String ID (tlmMnemonic)")
    unit = forms.CharField(label='unit', max_length=500, required=False,
                           help_text="unit")
