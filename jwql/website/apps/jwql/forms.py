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
    placed in the ``jwql/utils/`` directory.
"""

import datetime
import glob
import os

from astropy.time import Time, TimeDelta
from django import forms
from django.shortcuts import redirect
from jwedb.edb_interface import is_valid_mnemonic

# from data_containers import get_thumbnails_all_instruments
from jwql.database import database_interface as di
from jwql.utils.constants import ANOMALY_CHOICES
from jwql.utils.constants import FILTERS_PER_INSTRUMENT
from jwql.utils.constants import FULL_FRAME_APERTURES
from jwql.utils.constants import GENERIC_SUFFIX_TYPES
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_SHORTHAND
from jwql.utils.constants import OBSERVING_MODE_PER_INSTRUMENT
from jwql.utils.utils import get_config, filename_parser
# from jwql.website.apps.jwql.views import current_anomalies  ### global variable defined once query_anomaly page has forms filled

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')

# from jwql.utils import anomaly_query_config
# from jwql.website.apps.jwql import views # update anomaly_query_config


class AnomalyForm(forms.Form):
    """Creates a ``AnomalyForm`` object that allows for anomaly input
    in a form field."""
    query = forms.MultipleChoiceField(choices=ANOMALY_CHOICES, widget=forms.CheckboxSelectMultiple())  # Update depending on chosen instruments

    def clean_anomalies(self):

        anomalies = self.cleaned_data['query']

        return anomalies


class AnomalySubmitForm(forms.Form):
    """A multiple choice field for specifying flagged anomalies."""

    # Define anomaly choice field
    anomaly_choices = forms.MultipleChoiceField(choices=ANOMALY_CHOICES, widget=forms.CheckboxSelectMultiple())

    def update_anomaly_table(self, rootname, user, anomaly_choices):
        """Updated the ``anomaly`` table of the database with flagged
        anomaly information

        Parameters
        ----------
        rootname : str
            The rootname of the image to flag (e.g.
            ``jw86600008001_02101_00001_guider2``)
        user : str
            The ``ezid`` of the authenticated user that is flagging the
            anomaly
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
        di.engine.execute(di.Anomaly.__table__.insert(), data_dict)

    def clean_anomalies(self):

        anomalies = self.cleaned_data['anomaly_choices']

        return anomalies


class ApertureForm(forms.Form):
    """Creates an ``ApertureForm`` object that allows for ``aperture``
    input in a form field."""

    aperture_list = []
    for instrument in FULL_FRAME_APERTURES.keys():
        for aperture in FULL_FRAME_APERTURES[instrument]:
            item = [aperture, aperture]
            aperture_list.append(item)
    aperture = forms.MultipleChoiceField(required=False, choices=aperture_list, widget=forms.CheckboxSelectMultiple)

    def clean_apertures(self):

        apertures = self.cleaned_data['aperture']

        return apertures


class EarlyDateForm(forms.Form):
    """Creates a ``EarlyDateForm`` object that allows for ``early_date``
    input in a form field."""

    early_date = forms.DateField(required=False, initial="eg, 2021-10-02 12:04:39 or 2021-10-02")

    # still working out whether we can have initial pre-fill without setting values in request
    def clean_early_date(self):
        early_date = self.cleaned_data['early_date']

        return early_date


class ExptimeMaxForm(forms.Form):
    """Creates a ``ExptimeMaxForm`` object that allows for
    ``exp_time_max`` input in a form field."""

    exp_time_max = forms.DecimalField(initial="57404.70")

    def clean_exptime_max(self):
        exptime_max = self.cleaned_data['exp_time_max']

        return exptime_max


class ExptimeMinForm(forms.Form):
    """Creates a ``ExptimeMinForm`` object that allows for
    ``exp_time_min`` input in a form field."""

    exp_time_min = forms.DecimalField(initial="57404.04")

    def clean_exptime_min(self):
        """Validate the "exp_time_min" field.

        Check that the input is greater than or equal to zero.

        Returns
        -------
        exptime_min : int
            The cleaned data input into the "exp_time_min" field

        """
        exptime_min = self.cleaned_data['exp_time_min']
        if int(exptime_min) < 0:
            raise forms.ValidationError("""Invalid minimum exposure time {}.
                                           Please provide positive value""".format(exptime_min))

        return exptime_min


class FileSearchForm(forms.Form):
    """Single-field form to search for a proposal or fileroot."""

    # Define search field
    search = forms.CharField(label='', max_length=500, required=True,
                             empty_value='Search')

    # Initialize attributes
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
            search_string = os.path.join(FILESYSTEM_DIR, 'jw{}'.format(proposal_string),
                                         '*{}*.fits'.format(proposal_string))
            all_files = glob.glob(search_string)
            if len(all_files) > 0:
                all_instruments = []
                for file in all_files:
                    instrument = filename_parser(file)['instrument']
                    all_instruments.append(instrument)
                if len(set(all_instruments)) > 1:
                    raise forms.ValidationError('Cannot return result for proposal with multiple '
                                                'instruments ({}).'
                                                .format(', '.join(set(all_instruments))))

                self.instrument = all_instruments[0]
            else:
                raise forms.ValidationError('Proposal {} not in the filesystem.'.format(search))

        # If they searched for a fileroot...
        elif self.search_type == 'fileroot':
            # See if there are any matching fileroots and, if so, what
            # instrument they are for
            search_string = os.path.join(FILESYSTEM_DIR, search[:7], '{}*.fits'.format(search))
            all_files = glob.glob(search_string)

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
        proposal_string = '{:05d}'.format(int(search))

        # If they searched for a proposal
        if self.search_type == 'proposal':
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

# from jwql.website.apps.jwql import views # update anomaly_query_config
class FilterForm(forms.Form):
    """Creates a ``FilterForm`` object that allows for ``filter``
    input in a form field."""

    filter_list = []
    for instrument in FILTERS_PER_INSTRUMENT.keys():
        # if instrument in anomaly_query_config.INSTRUMENTS_CHOSEN:   # eg ['nirspec']: selects relevant filters, but not specific to chosen instruments
        filters_per_inst = FILTERS_PER_INSTRUMENT[instrument]
        for filter in filters_per_inst:
            filter_list.append([filter, filter]) if [filter, filter] not in filter_list else filter_list
    filter = forms.MultipleChoiceField(required=False, choices=filter_list, widget=forms.CheckboxSelectMultiple)

    def clean_filters(self):

        filters = self.cleaned_data['filter']

        return filters


class InstrumentForm(forms.Form):
    """Creates a ``InstrumentForm`` object that allows for ``query``
    input in a form field."""

    query = forms.MultipleChoiceField(required=False,
                                      choices=[(inst, JWST_INSTRUMENT_NAMES_MIXEDCASE[inst]) for inst in JWST_INSTRUMENT_NAMES_MIXEDCASE],
                                      widget=forms.CheckboxSelectMultiple())

    def clean_instruments(self):

        instruments_chosen = self.cleaned_data['query']

        return instruments_chosen

    def redirect_to_files(self):
        """Determine where to redirect the web app based on user input.

        Returns
        -------
        HttpResponseRedirect object
            Outgoing redirect response sent to the webpage

        """
        # Process the data in form.clean_instruments as required
        instruments = self.cleaned_data['query']

        # get_thumbnails_all_instruments(instruments)
        return instruments


class LateDateForm(forms.Form):
    """Creates a ``LateDateForm`` object that allows for ``late_date``
    input in a form field."""

    late_date = forms.DateField(required=False, initial="eg, 2021-11-25 14:30:59 or 2021-11-25")

    def clean_late_date(self):
        latedate = self.cleaned_data['late_date']

        return latedate


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
        default_start_time = Time('2019-01-16 00:00:00.000', format='iso')
        default_end_time = Time('2019-01-16 00:01:00.000', format='iso')

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


class ObservingModeForm(forms.Form):  # Add instruments chosen parameter
    """Creates a ``ObservingModeForm`` object that allows for ``mode``
    input in a form field."""

    mode_list = []
    for instrument in OBSERVING_MODE_PER_INSTRUMENT.keys():  # Add AND in instruments chosen
        modes_per_inst = OBSERVING_MODE_PER_INSTRUMENT[instrument]
        for mode in modes_per_inst:
            mode_list.append([mode, mode]) if [mode, mode] not in mode_list else mode_list
    mode = forms.MultipleChoiceField(required=False, choices=mode_list, widget=forms.CheckboxSelectMultiple)

    def clean_modes(self):

        modes = self.cleaned_data['mode']

        return modes
