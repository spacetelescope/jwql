"""Contains class objects for building a query form for querying the
database through the webite.
Many of the class objects are subclasses or extensions from components
provided by the ``wtforms`` library. Much of this is based on Meredith 
Durbin's code for WFC3 Quicklook.

Use
---
    This module is inteded to be imported and used by the
    ``ql_site`` module as such:
    ::
        from ql_database_form import QueryForm, AnomalyFlagForm   ########### UPDATE THESE  ##########
        form = QueryForm()
        form = AnomalyFlagForm()
"""

import os

from wtforms import *
from wtforms_alchemy import ModelForm
from wtforms_components.fields import IntegerField, DecimalField

from jwql.utils.constants import ANOMALIES_PER_INSTRUMENT, JWST_INSTRUMENT_NAMES_MIXEDCASE

# values_dict = {}
# with open(os.path.join(os.path.dirname(__file__), 'form_values.txt')) as f1:
#     for line in f1:
#         key, values = line.replace('\n', '').split(':')
#         values = values.split(',')
#         values_dict[key] = values

# values_dict['output'] = list(zip(values_dict['output_cols'], values_dict['output_names']))
# values_dict['anomalies'] = list(zip(values_dict['anomaly_cols'], values_dict['anomaly_names']))


# class AnomalyFlagForm(ModelForm):
#     """Form for flagging anomalies on individual images.
#     Parameters
#     ----------
#     ModelForm : obj
#     The ``ModelForm`` object from ``wtforms``
#     """

#     class Meta:
#         model = ANOMALIES_PER_INSTRUMENT
#         # field_args = {i[0]: {'label': i[1]} for i in values_dict['anomalies']}  ###### update this


class CheckboxField(SelectMultipleField):
    """Like a ``SelectField``, except displays a list of checkbox
    buttons.
    Parameters
    ----------
    SelectMultipleField : obj
        The ``SelectMultipleField`` object from ``wtforms``
    """

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class MultiCheckboxField(SelectMultipleField):
    """A multiple-select, except displays a list of checkboxes.
    Parameters
    ----------
    SelectMultipleField : obj
        The ``SelectMultipleField`` object from ``wtforms``
    """

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


def is_field_value(form, fieldname, value, negate=False):
    """Helper function to check if the given field in the given form is
    of a specified value.
    Parameters
    ----------
    form: obj
        The form to test on
    fieldname : str
        The fieldname to test value against. If not found an Exception
        is raised.
    value : str
        Value to test for.
    negate : boolean
        True/False to invert the result.
    """

    field = form._fields.get(fieldname)
    if field is None:
        raise Exception('Invalid field "%s"' % fieldname)
    test = value == field.data
    test = not test if negate else test

    return test


class RequiredIf(validators.Required):
    """Custom validator to enforce requires only if another field
    matches a specified value. the ``negate`` allows for inverting
    the result.
    Parameters
    ----------
    validators.Required : obj
        The ``validators.Required`` object from ``wtforms``.
    """

    def __init__(self, other_fieldname, value, negate, *args, **kwargs):
        self.other_fieldname = other_fieldname
        self.negate = negate
        self.value = value
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        if is_field_value(form, self.other_fieldname, self.value, self.negate):
            super(RequiredIf, self).__call__(form, field)

operator_form = SelectField('Operator', [validators.Optional()],
                          choices=[('=', '='), ('<', '<'), ('>', '>'), ('between', 'between')],
                          default=('=', '='))


class ExptimeForm(Form):
    """Creates a ``ExptimeForm`` object that allows for ``exptime``
    input in a form field.
    Parameters
    ----------
    Form : obj
        The ``Form`` object from ``wtforms``.
    """
    op = operator_form
    val1 = DecimalField('Exposure Time', [validators.Optional()])
    val2 = DecimalField('exptime2', [validators.Optional()])


class DateForm(Form):
    """Creates a ``DateForm`` object that allows for date input in a
    form field.
    Parameters
    ----------
    Form : obj
        The ``Form`` object from ``wtforms``.
    """

    op = operator_form
    val1 = DateField('Date Observed', [validators.Optional()],
                      description='YYYY-MM-DD', format='%Y-%m-%d')
    val2 = DateField('dateobs2', [validators.Optional()],
                      description='YYYY-MM-DD', format='%Y-%m-%d')


class AnomalyForm(Form):
    """Creates a ``AnomalyForm`` object that allows for anomaly input
    in a form field.
    Parameters
    ----------
    Form : obj
        The ``Form`` object from ``wtforms``.
    """

    query = MultiCheckboxField('Anomalies', [validators.Optional()],
                               choices=ANOMALIES_PER_INSTRUMENT.keys())   ###UPDATE DEPENDING ON WHICH INSTRUMENTS ARE SELECTED
    logic = RadioField('Logic', choices=[('OR', 'OR'), ('AND', 'AND')], default='OR', description='span3')


class QueryForm(Form):
    """Form for querying the database.
    Parameters
    ----------
    Form : obj
        The ``Form`` object from ``wtforms``.
    """

    rootname = TextField('Rootname', [validators.Optional()],
                        description='Single rootname or comma-separated list span6')
    instrument = CheckboxField('Instrument', [validators.Optional()], description='span5',
                        choices=[(inst.lower(), inst) for inst in JWST_INSTRUMENT_NAMES_MIXEDCASE])
    # proposal_type = CheckboxField('Proposal Type', [validators.Optional()], description='span2',
    #                     choices=[('cal', 'CAL'),
    #                              ('go', 'GO')])
    # obstype = CheckboxField('Observation Type', [validators.Optional()], description='span2',
    #                     choices=[('IMAGING', 'Imaging'),
    #                              ('SPECTROSCOPIC', 'Spectroscopic')])
    # dir = TextField('Directory', [validators.Optional()], description=
    #     'ex. /grp/hst/wfc3a/Quicklook/11422/Visit01; single or comma-separated span5')
    # link = TextField('Link', [validators.Optional()], description=
    #     'ex. /grp/hst/wfc3a/Cal_Links/12334; single or comma-separated span5')
    # proposid = IntegerField('Proposal ID', [validators.Optional(),
    # validators.NumberRange(min=11099, max=19999, message='Please enter a valid proposal ID')], description='span2')
    # filter = MultiCheckboxField('Filter', [validators.Optional()],
    #                     choices=[(filt, filt) for filt in values_dict['filter']])
    # date_obs = FormField(DateForm, 'Date Observed', description='span3')
    # exptime = FormField(ExptimeForm, 'Exposure Time', description='span3')
    # aperture = SelectMultipleField('Aperture', [validators.Optional()],
    #                     choices=[(ap, ap) for ap in values_dict['aperture']],
    #                     description='span3')
    # imagetyp = SelectMultipleField('Image Type', [validators.Optional()],
    #                     choices=[(imtype, imtype) for imtype in values_dict['imagetyp']],
    #                     description='span3')
    # samp_seq = SelectMultipleField('Sample Sequence (IR only)', [validators.Optional()],
    #                     choices=[(seq, seq) for seq in values_dict['samp_seq']],
    #                     description='span3')
    # nsamp = FormField(NsampForm, 'Number of Samples (IR only)', description='span3')
    # flashcur = SelectMultipleField('Flash current (UVIS Only)', [validators.Optional()],
    #                     choices=[(flash, flash) for flash in values_dict['flashcur']],
    #                     description='span3')
    # flashlvl = FormField(FlashlvlForm, 'Flash Level (UVIS Only)', description='span3')
    # targname = TextField('Target Name', [validators.Optional()], description=
    #     'ex. OMEGACEN, NGC-3603, IRAS05129+5128; single or comma-separated span6')
    # pr_inv_l = TextField('PI Last Name', [validators.Optional()],
    #                     description='Single or comma-separated span3')
    # pr_inv_f = TextField('PI First Name', [validators.Optional()],
    #                     description='Single or comma-separated span3')
    anomaly = FormField(AnomalyForm, 'Anomalies', description='span12')
    # output_columns = MultiCheckboxField('Output Columns', [RequiredIf('output_format', 'thumbnails', True,
    #                     message='Please select at least one output column.')],
    #                     choices=values_dict['output'])
    # output_format = RadioField('Output Format', [validators.Required(message=
    #     'Please select an output format.')],
    #                     choices=[('table', 'HTML table'),
    #                              ('csv', 'CSV'),
    #                              ('thumbnails', 'Thumbnails')],
    #                     default = 'thumbnails', description='span3')