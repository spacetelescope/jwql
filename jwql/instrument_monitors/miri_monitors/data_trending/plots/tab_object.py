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

    str_body = """"
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
