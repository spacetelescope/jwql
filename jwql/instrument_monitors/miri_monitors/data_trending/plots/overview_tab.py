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



def overview_settings(conn):

    now = datetime.datetime.now()
    default_start = now - datetime.timedelta(120)
    slider_min= datetime.date(2017, 2, 11)
    time_range= ({'start': default_start, 'end': now })

    ds_astropy = Time(default_start)
    now_astropy = Time(now)

    source = ColumnDataSource(data=dict(start=[ds_astropy.mjd,], end=[now_astropy.mjd,]))

    slider1 = DateRangeSlider(value = (time_range['start'], time_range['end']), start=slider_min, end=now, title= "Time range")

    button = Button(label = "UPDATE PLOTS", button_type="success")



    callback = CustomJS(args = dict(source=source), code =
    """

        var data = source.get('data')
        var start = cb_obj.value
        data['start'] = range[0]
        data['end'] = range[1]
        source.change.emit();

        var data = source.get('data');
        var start = range.get('start');
        var end = range.get('end');
        data['%s'] = [start + (end - start) / 2];
        data['%s'] = [end - start];
        source.trigger('change');

    """)

    slider1.js_on_change('value', callback)

    slider = WidgetBox(slider1, width=800)

    layout = row(slider, button)

    tab = Panel(child = layout, title = "OVERVIEW/SETTINGS")

    return tab
