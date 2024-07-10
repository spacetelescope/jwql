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

from collections import defaultdict
import datetime
import glob
import os
import logging

from astropy.time import Time, TimeDelta
from django import forms
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from jwql.edb.engineering_database import is_valid_mnemonic
from jwql.website.apps.jwql.models import Anomalies


from jwql.utils.constants import (ANOMALY_CHOICES_PER_INSTRUMENT, ANOMALIES_PER_INSTRUMENT, APERTURES_PER_INSTRUMENT, DETECTOR_PER_INSTRUMENT,
                                  EXP_TYPE_PER_INSTRUMENT, FILTERS_PER_INSTRUMENT, GENERIC_SUFFIX_TYPES, GRATING_PER_INSTRUMENT,
                                  GUIDER_FILENAME_TYPE, JWST_INSTRUMENT_NAMES_MIXEDCASE, JWST_INSTRUMENT_NAMES_SHORTHAND,
                                  READPATT_PER_INSTRUMENT, IGNORED_SUFFIXES, SUBARRAYS_PER_INSTRUMENT, PUPILS_PER_INSTRUMENT,
                                  LOOK_OPTIONS, SORT_OPTIONS, PROPOSAL_CATEGORIES)
from jwql.utils.utils import (get_config, get_rootnames_for_instrument_proposal, filename_parser, query_format)

from wtforms import SubmitField, StringField


class BaseForm(forms.Form):
    """A generic form with target resolve built in"""
    # Target Resolve
    targname = StringField('targname', default='')
    target_url = StringField('target_url', default='')

    # Submit button
    resolve_submit = SubmitField('Resolve Target')


class JwqlQueryForm(BaseForm):
    """Form validation for the JWQL Query viewing tool"""

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
        params[instrument]['subarray_list'] = []
        params[instrument]['pupil_list'] = []
        params[instrument]['anomalies_list'] = []
        # Generate dynamic lists of apertures to use in forms
        for aperture in APERTURES_PER_INSTRUMENT[instrument.lower()]:
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
        # Generate dynamic lists of subarray options to use in forms
        for subarray in SUBARRAYS_PER_INSTRUMENT[instrument]:
            subarray = query_format(subarray)
            params[instrument]['subarray_list'].append([subarray, subarray])
        # Generate dynamic lists of pupil options to use in forms
        for pupil in PUPILS_PER_INSTRUMENT[instrument]:
            pupil = query_format(pupil)
            params[instrument]['pupil_list'].append([pupil, pupil])
        # Generate dynamic lists of anomalies to use in forms
        for anomaly in ANOMALIES_PER_INSTRUMENT.keys():
            if instrument in ANOMALIES_PER_INSTRUMENT[anomaly]:
                item = [query_format(anomaly), query_format(anomaly)]
                params[instrument]['anomalies_list'].append(item)

    # general parameters
    instrument = forms.MultipleChoiceField(
        required=False,
        choices=[(inst, JWST_INSTRUMENT_NAMES_MIXEDCASE[inst]) for inst in JWST_INSTRUMENT_NAMES_MIXEDCASE],
        widget=forms.CheckboxSelectMultiple)

    look_choices = [(query_format(choice), query_format(choice)) for choice in LOOK_OPTIONS]
    look_status = forms.MultipleChoiceField(
        required=False, choices=look_choices, widget=forms.CheckboxSelectMultiple)

    date_range = forms.CharField(required=True)

    cat_choices = [(query_format(choice), query_format(choice)) for choice in PROPOSAL_CATEGORIES]
    proposal_category = forms.MultipleChoiceField(
        required=False, choices=cat_choices, widget=forms.CheckboxSelectMultiple)

    sort_choices = [(choice, choice) for choice in SORT_OPTIONS]
    sort_type = forms.ChoiceField(
        required=True,
        choices=sort_choices, initial=sort_choices[2],
        widget=forms.RadioSelect)

    num_choices = [(50, 50), (100, 100), (200, 200), (500, 500)]
    num_per_page = forms.ChoiceField(
        required=True,
        choices=num_choices, initial=num_choices[3],
        widget=forms.RadioSelect)

    # instrument specific parameters
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

    miri_subarray = forms.MultipleChoiceField(required=False, choices=params['miri']['subarray_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_subarray = forms.MultipleChoiceField(required=False, choices=params['nirspec']['subarray_list'], widget=forms.CheckboxSelectMultiple)
    niriss_subarray = forms.MultipleChoiceField(required=False, choices=params['niriss']['subarray_list'], widget=forms.CheckboxSelectMultiple)
    nircam_subarray = forms.MultipleChoiceField(required=False, choices=params['nircam']['subarray_list'], widget=forms.CheckboxSelectMultiple)
    fgs_subarray = forms.MultipleChoiceField(required=False, choices=params['fgs']['subarray_list'], widget=forms.CheckboxSelectMultiple)

    miri_pupil = forms.MultipleChoiceField(required=False, choices=params['miri']['pupil_list'], widget=forms.CheckboxSelectMultiple)
    nirspec_pupil = forms.MultipleChoiceField(required=False, choices=params['nirspec']['pupil_list'], widget=forms.CheckboxSelectMultiple)
    niriss_pupil = forms.MultipleChoiceField(required=False, choices=params['niriss']['pupil_list'], widget=forms.CheckboxSelectMultiple)
    nircam_pupil = forms.MultipleChoiceField(required=False, choices=params['nircam']['pupil_list'], widget=forms.CheckboxSelectMultiple)
    fgs_pupil = forms.MultipleChoiceField(required=False, choices=params['fgs']['pupil_list'], widget=forms.CheckboxSelectMultiple)

    def clean_inst(self):

        inst = self.cleaned_data['instrument']

        return inst


class InstrumentAnomalySubmitForm(forms.Form):
    """A multiple choice field for specifying flagged anomalies."""

    def __init__(self, *args, **kwargs):
        instrument = kwargs.pop('instrument')
        super(InstrumentAnomalySubmitForm, self).__init__(*args, **kwargs)
        self.fields['anomaly_choices'] = forms.MultipleChoiceField(
            choices=ANOMALY_CHOICES_PER_INSTRUMENT[instrument],
            widget=forms.CheckboxSelectMultiple(), required=False)
        self.instrument = instrument

    def update_anomaly_table(self, rootfileinfo, user, anomaly_choices):
        """Update the ``Anomalies`` model associated with the sent RootFileInfo.
        All 'anomaly_choices' should be marked 'True' and the rest should be 'False'

        Parameters
        ----------
        rootfileinfo : RootFileInfo
            The RootFileInfo model object of the image to update
        user : str
            The user that is flagging the anomaly
        anomaly_choices : list
            A list of anomalies that are to be flagged (e.g.
            ``['snowball', 'crosstalk']``)
        """
        anomaly_choices = list(map(str.lower, anomaly_choices))
        default_dict = {'flag_date': datetime.datetime.now(),
                        'user': user}
        for anomaly in Anomalies.get_all_anomalies():
            default_dict[anomaly] = (anomaly in anomaly_choices)

        try:
            Anomalies.objects.update_or_create(root_file_info=rootfileinfo, defaults=default_dict)
        except Exception as e:
            logging.warning('Unable to update anomaly table for {} due to {}'.format(rootfileinfo.root_name, e))

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
            search_string_public = os.path.join(get_config()['filesystem'], 'public', 'jw{}'.format(proposal_string),
                                                '*', '*{}*.fits'.format(proposal_string))
            search_string_proprietary = os.path.join(get_config()['filesystem'], 'proprietary', 'jw{}'.format(proposal_string),
                                                     '*', '*{}*.fits'.format(proposal_string))
            all_files = glob.glob(search_string_public)
            all_files.extend(glob.glob(search_string_proprietary))

            # Gather all files that do not have the 'IGNORED_SUFFIXES' in them
            all_files = [filename for filename in all_files if not any(name in filename for name in IGNORED_SUFFIXES)]

            if len(all_files) > 0:
                all_instruments = []
                all_observations = defaultdict(list)
                for file in all_files:
                    filename = os.path.basename(file)

                    # We only want to pass in datasets that are science exptypes. JWQL doesn't
                    # handle guider data, this will still allow for science FGS data but filter
                    # guider data.
                    if any(map(filename.__contains__, GUIDER_FILENAME_TYPE)):
                        continue
                    else:
                        fileinfo = filename_parser(file)
                        try:
                            instrument = fileinfo['instrument']
                            observation = fileinfo['observation']
                            all_instruments.append(instrument)
                            all_observations[instrument].append(observation)
                        except KeyError:
                            # If the filename is not recognized by filename_parser(), skip it.
                            continue

                # sort lists so first observation is available when link is clicked.
                for instrument in all_instruments:
                    all_observations[instrument].sort()

                if len(set(all_instruments)) > 1:
                    # Technically all proposal have multiple instruments if you include guider data. Remove Guider Data
                    instrument_routes = [format_html('<a href="/{}/archive/{}/obs{}">{}</a>', instrument, proposal_string[1:],
                                                     all_observations[instrument][0], instrument) for instrument in set(all_instruments)]
                    raise forms.ValidationError(
                        mark_safe(('Proposal contains multiple instruments, please click instrument link to view data: {}.').format(', '.join(instrument_routes))))  # noqa

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
            parsed = filename_parser(search)
            if 'instrument' in parsed:
                self.fileroot_dict = filename_parser(search)
                return True
            else:
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
            all_rootnames = get_rootnames_for_instrument_proposal(self.instrument, proposal_string)
            all_obs = []
            for root in all_rootnames:
                # Wrap in try/except because level 3 rootnames won't have an observation
                # number returned by the filename_parser. That's fine, we're not interested
                # in those files anyway.
                try:
                    all_obs.append(filename_parser(root)['observation'])
                except KeyError:
                    pass

            observation = sorted(list(set(all_obs)))[0]

            return redirect('/{}/archive/{}/obs{}'.format(self.instrument, proposal_string, observation))

        # If they searched for a file root
        elif self.search_type == 'fileroot':
            return redirect('/{}/{}/'.format(self.instrument, search))


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

    production_mode = True

    if production_mode:
        # times for default query (one day one week ago)
        now = Time.now()
        default_start_time = now + TimeDelta(3600., format='sec')
        default_end_time = now
    else:
        # example for testing
        default_start_time = Time('2022-06-20 00:00:00.000', format='iso')
        default_end_time = Time('2022-06-21 00:00:00.000', format='iso')

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
