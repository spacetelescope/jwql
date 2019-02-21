import jwql.instrument_monitors.miri_monitors.data_trending.utils.sql_interface as sql
from bokeh.plotting import figure
from bokeh.models import BoxAnnotation, LinearAxis, Range1d
from bokeh.embed import components
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource, CustomJS, DateRangeSlider, Slider,  Button
from bokeh.layouts import WidgetBox, gridplot, layout, column, row
from bokeh import events

import pandas as pd
import numpy as np
import datetime
import sqlite3

from astropy.time import Time

from datetime import date
from random import randint


def button_handler(new):
    print (new)





def overview_settings(conn):

    now = datetime.datetime.now()
    default_start = now - datetime.timedelta(120)
    slider_min= datetime.date(2017, 2, 11)
    time_range= ({'start': default_start, 'end': now })

    tr = pd.DataFrame.from_dict(time_range, orient='index')

    slider1 = DateRangeSlider(value = (time_range['start'], time_range['end']), start=slider_min, end=now, title= "Time range")
    button = Button(label = "UPDATE PLOTS", button_type="success")

    button.js_on_event(events.ButtonClick, button_handler(time_range))

    date_slider_callback = CustomJS(args = dict(source=tr), code =
    """
        var data = source.time_range
        var start = cb_obj.start
        var end = cb_obj.end

        data['start'] = start
        data['end'] = end

        data.change.emit();
    """)

    slider1.js_on_change('value', date_slider_callback)

    slider = WidgetBox(slider1, width=800)

    layout = row(slider, button)

    tab = Panel(child = layout, title = "OVERVIEW/SETTINGS")

    return tab
