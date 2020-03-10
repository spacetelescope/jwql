
from bokeh.models.widgets import Div, MultiSelect
from bokeh.layouts import column, gridplot
from bokeh.models.widgets import TextInput
from bokeh.models.widgets.inputs import DatePicker, TextAreaInput
#from bokeh.models.widgets.buttons import Button, CustomJS
from bokeh.models.widgets.buttons import Button
from bokeh.events import ButtonClick
from bokeh.io import curdoc
from bokeh.client import push_session

import numpy as np
from bokeh.io import show, output_file
from bokeh.plotting import figure
from bokeh import events
from bokeh.models import CustomJS, Div, Button
from bokeh.layouts import column, row



def display_event(div, attributes=[], style = 'float:left;clear:left;font_size=10pt'):
    "Build a suitable CustomJS to display the current event in the div model."
    return CustomJS(args=dict(div=div), code="""
        var attrs = %s; var args = [];
        for (var i = 0; i<attrs.length; i++) {
            args.push(attrs[i] + '=' + Number(cb_obj[attrs[i]]).toFixed(2));
        }
        var line = "<span style=%r><b>" + cb_obj.event_name + "</b>(" + args.join(", ") + ")</span>\\n";
        var text = div.text.concat(line);
        var lines = text.split("\\n")
        if (lines.length > 35)
            lines.shift();
        div.text = lines.join("\\n");
        div.text = "hi";
    """ % (attributes, style))

def callback(div):
    div.text(' neu')




def display_report(options_imput):
    title_dataReport = Div(text='<h2><u>Report-Tool</u></h2>', width=200, height=100)
    Name_field = TextInput(title="Name", value = "John Doe", width = 300)
    start_date = DatePicker(title="Start Date", width = 300)
    end_date = DatePicker(title="End Date", width = 300)
    textareal = TextAreaInput(rows=10)
    dropDown = MultiSelect(width = 300, options = options_imput)
    button = Button(label="Button", button_type="success")



    div = Div(text="""Your <a href="https://en.wikipedia.org/wiki/HTML">HTML</a>-supported text is initialized with the <b>text</b> argument.  The
    remaining div arguments are <b>width</b> and <b>height</b>. For this example, those values
    are <i>200</i> and <i>100</i> respectively.""")

    #div.text('test')



    button.js_on_event(events.ButtonClick, display_event(div)) # Button click

    #button.on_event(events.ButtonClick, callback(div))


    l = gridplot([[Name_field, start_date, end_date, dropDown]], merge_tools=False)
    l = column(title_dataReport,l, textareal, button, div)

    return l
