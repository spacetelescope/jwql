"""generate_tab_description.py

    Generated the html code for the info section in each tab

Authors
-------
    - [AIRBUS] Daniel Kübacher
    - [AIRBUS] Leo Stumpf

Use
---
    -

Dependencies
------------
    The descriptions text must be defined as an list defined as followed:

    list = [
    [list:{Line=1,column=1}, list:{Line=1,column=2}, list:{Line=1,column=3}],
    [list:{Line=2,column=1}, list:{Line=2,column=2}, list:{Line=2,column=3}],
    [list:{Line=3,column=1}, list:{Line=3,column=2}, list:{Line=3,column=3}]
    ]

    for example:
    description_power = [
    [['POWER ICE'], ['SE_ZIMIRICEA * 30V (static)'], ['Primary power consumption ICE side A - HV on and IDLE']],
    [['POWER FPE'], ['SE_ZIMIRIFPEA * 30V (static)'], ['Primary power consumption FPE side A']],
    [['FPE & ICE Voltages/Currents'], ['SE_ZIMIRFPEA', ' SE_ZIMIRCEA *INPUT VOLTAGE* (missing)'],
     ['Supply voltage and current ICE/FPE']]
    ]

    The description for all tabs are predefined in the utils_f.py file and can be imported from there.

References
----------
    The code was developed in reference to the information provided in:
    ‘MIRI trend requestsDRAFT1900301.docx’

Notes
-----
    For further information please contact Brian O'Sullivan
"""
from bokeh.models.widgets import Div
import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf
import jwql.instrument_monitors.miri_monitors.data_trending.utils_f as utils
from bokeh.models import (BoxSelectTool, Circle, Column, ColumnDataSource,
                          DataTable, Grid, HoverTool, IntEditor, LinearAxis,
                          NumberEditor, NumberFormatter, Plot, SelectEditor,
                          StringEditor, StringFormatter, TableColumn,)
from bokeh.document import Document
from bokeh.util.browser import view
from bokeh.embed import file_html
from bokeh.resources import INLINE
import pandas as pd
from astropy.time import Time
from bokeh.layouts import column

def generate_tab_description(input):
    str_start = """
    <style>
        table, th, td {
          border: 1px solid black;
          background-color: #efefef;
          border-collapse: collapse;
          padding: 5px
        }
        table {
          border-spacing: 15px;
        }
        </style>

    """

    str_end = """

        </table>
        </body>
    """

    str_body = """
        <body>
        <table style="width:100%">
          <tr>
            <th><h6>Plotname</h6></th>
            <th><h6>Mnemonic</h6></th>
            <th><h6>Description</h6></th>
          </tr>
    """

    for line in input:
        str_body += '      <tr>\n'
        for collum in line:
            str_body += '         <td>\n'
            for element in collum:
                str_body += '          '
                str_body += element
                str_body += '<br>\n'
            str_body += '         </td>\n'
        str_body += '      </tr>\n'

    str_out = str_start + str_body + str_end
    descr = Div(text=str_out, width=1100)
    return descr

def anomaly_table(conn, mnemonic):

    get_str = '('
    for element in mnemonic:
        get_str = get_str + "'"+ str(element)+ "',"
    get_str = get_str[:-1] + ')'


    sql_c = "SELECT * FROM miriAnomaly WHERE plot in " + get_str +" ORDER BY start_time"
    anomaly_orange = pd.read_sql_query(sql_c, conn)

    div = Div(text="<font size='5'> Reported anomalys: </font>")

    try:
        # convert mjd to iso time
        anomaly_orange['start_time'] = Time(anomaly_orange['start_time'], format='mjd').iso
        anomaly_orange['end_time'] = Time(anomaly_orange['end_time'], format='mjd').iso

        # neu
        source = ColumnDataSource(anomaly_orange)

        columns = [
            TableColumn(field="id", title="ID", width=20),
            TableColumn(field="plot", title="Mnemonic", width=100),
            TableColumn(field="autor", title="Autor", width=100),
            TableColumn(field="start_time", title="Start Time", width=200),
            TableColumn(field="end_time", title="End Time", width=200),
            TableColumn(field="comment", title="Comment", width=600),
        ]

        data_table = DataTable(source=source, columns=columns, editable=False, width=1120, fit_columns=True,
                               index_position=None, selectable=True)
    except:
        data_table = Div(text='There are currently no anomalies reported')

    return column(div, data_table)
