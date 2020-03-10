"""report_tool.py

    First try at creating a tool for bug report

Authors
-------
    - [AIRBUS] Leo Stumpf

Use
---

Dependencies
------------
?

References
----------


Notes
-----
    For further information please contact Brian O'Sullivan
"""
import os

from bokeh import events
from bokeh.layouts import column
from bokeh.layouts import gridplot
from bokeh.models import CustomJS, Div
from bokeh.models.widgets import Button
from bokeh.models.widgets import MultiSelect
from bokeh.models.widgets import TextInput
from bokeh.models.widgets.inputs import DatePicker, TextAreaInput

def display_event(div, attributes=[], style='float:left;clear:left;font_size=10pt'):
    fils_js = os.path.join(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))), 'test123.js')
    file_js = open(fils_js, 'r')
    code_str = file_js.read()
    file_js.close()
    "Build a suitable CustomJS to display the current event in the div model."
    return CustomJS(args=dict(div=div), code=code_str % (attributes, style))

def display_report(options_imput):
    title_dataReport = Div(text='<h2><u>Report-Tool</u></h2>', width=200, height=100)
    Name_field = TextInput(title="Name", value="John Doe", width=300)
    start_date = DatePicker(title="Start Date", width=300)
    end_date = DatePicker(title="End Date", width=300)
    textareal = TextAreaInput(rows=10)
    dropDown = MultiSelect(width=300, options=options_imput)
    button = Button(label="Button", button_type="success")

    div = Div(text="""Your <a href="https://en.wikipedia.org/wiki/HTML">HTML</a>-supported text is initialized with the <b>text</b> argument.  The
    remaining div arguments are <b>width</b> and <b>height</b>. For this example, those values
    are <i>200</i> and <i>100</i> respectively.""")

    div.text = "test2"

    button.js_on_event(events.ButtonClick, display_event(div))  # Button click

    # button.on_event(events.ButtonClick, partial(callback, foo=div))
    # button.on_event(events.ButtonClick, callback)
    # button.on_click(button_callback)

    l = gridplot([[Name_field, start_date, end_date, dropDown]], merge_tools=False)
    l = column(title_dataReport, l, textareal, button, div)

    return l
