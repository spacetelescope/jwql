"""utils_f.py

    Contains all utils/variables/definitions/settings for dashboard.py (coherently)
    Contains Elements for the dashbord

Authors
-------

    - [AIRBUS] Leo Stumpf

Use
---
    -

Dependencies
------------

    The file miri_database.db in the directory jwql/jwql/database/ must be populated.

References
----------
    The code was developed in reference to the information provided in:
    ‘MIRI trend requestsDRAFT1900301.docx’

Notes
-----

    For further information please contact Brian O'Sullivan
"""
import datetime
from astropy.time import Time
from bokeh.models import DatetimeTickFormatter
from bokeh.plotting import figure

import jwql.instrument_monitors.miri_monitors.data_trending.plots.plot_functions as pf

# Defines Layout of the Legend of all plots
plot_x_axis_format = DatetimeTickFormatter(
    hours=["%Y-%m-%d ,%H:%M:%S.%f"],
    days=["%Y-%m-%d, %H:%M"],
    months=["%Y-%m-%d"],
    years=["%Y-%m-%d"],
)


# Time Delta function it is used to only display a certain timeframe of e.g. the last 120 days
def time_delta(endtime):
    timeDeltaEnd = endtime.datetime
    timeDelta = [timeDeltaEnd - datetime.timedelta(days=120), timeDeltaEnd]
    return timeDelta


# Tab Description
description_bias = [
    [['VSSOUT'], ['IGDP_MIR_IC_V_VSSOUT', 'IGDP_MIR_SW_V_VSSOUT', 'IGDP_MIR_LW_V_VSSOUT'],
     ['Detector Bias VSSOUT (IC,SW, & LW)']],
    [['VDETCOM'], ['IGDP_MIR_IC_V_VDETCOM', 'IGDP_MIR_SW_V_VDETCOM', 'IGDP_MIR_LW_V_VDETCOM'],
     ['Detector Bias VDETCOM (IC,SW, & LW)']],
    [['VRSTOFF'], ['IGDP_MIR_IC_V_VRSTOFF', 'IGDP_MIR_SW_V_VRSTOFF', 'IGDP_MIR_LW_V_VRSTOFF'],
     ['Detector Bias VRSTOFF (IC,SW, & LW)']],
    [['VP'], ['IGDP_MIR_IC_V_VP', 'IGDP_MIR_SW_V_VP', 'IGDP_MIR_LW_V_VP'], ['Detector Bias VP (IC,SW, & LW)']],
    [['VDDUC'], ['IGDP_MIR_IC_V_VDDUC', 'IGDP_MIR_SW_V_VDDUC', 'IGDP_MIR_LW_V_VDDUC'],
     ['Detector Bias VDDUC (IC,SW, & LW)']]
]

# Tab Description
description_power = [
    [['POWER ICE'], ['SE_ZIMIRICEA * 30V (static)'], ['Primary power consumption ICE side A - HV on and IDLE']],
    [['POWER FPE'], ['SE_ZIMIRIFPEA * 30V (static)'], ['Primary power consumption FPE side A']],
    [['FPE & ICE Voltages/Currents'], ['SE_ZIMIRFPEA', ' SE_ZIMIRCEA *INPUT VOLTAGE* (missing)'],
     ['Supply voltage and current ICE/FPE']]
]

# Tab Description
description_IceVoltage = [
    [['ICE_SEC_VOLT1/3'], ['IMIR_HK_ICE_SEC_VOLT1 ', 'IMIR_HK_ICE_SEC_VOLT3'],
     ['ICE Secondary Voltage (HV) V1 and V3']],
    [['ICE_SEC_VOLT2'], ['IMIR_HK_SEC_VOLT2'], ['ICE secondary voltage (HV) V2']],
    [['ICE_SEC_VOLT4'], ['IMIR_HK_SEC_VOLT2'], ['ICE secondary voltage (HV) V4 - HV on and IDLE']],
    [['Wheel Sensor Supply'],
     ['IMIR_HK_FW_POS_VOLT', 'IMIR_HK_GW14_POS_VOLT', 'IMIR_HK_GW23_POS_VOLT', 'IMIR_HK_CCC_POS_VOLT'],
     ['Wheel Sensor supply voltages ']]
]

# Tab Description
description_FpeVC = [
    [['2.5V Ref and FPE Digg'], ['IMIR_SPW_V_DIG_2R5V', 'IMIR_PDU_V_REF_2R5V'],
     ['FPE 2.5V Digital and FPE 2.5V PDU Reference Voltage']],
    [['FPE Dig. 5V'], ['IMIR_PDU_V_DIG_5V', 'IMIR_PDU_I_DIG_5V'], ['FPE 5V Digital Voltage and Current']],
    [['FPE Ana. 5V'], ['IMIR_PDU_V_ANA_5V', 'IMIR_PDU_I_ANA_5V'], ['FPE +5V Analog Voltage and Current']],
    [['FPE Ana. N5V'], ['IMIR_PDU_V_ANA_N5V', 'IMIR_PDU_I_ANA_N5V'], ['FPE -5V Analog Voltage and Current']],
    [['FPE Ana. 7V'], ['IMIR_PDU_V_ANA_7V', 'IMIR_PDU_I_ANA_7V'], ['FPE +7V Analog Voltage and Current']],
    [['FPE Ana. N7V'], ['IMIR_PDU_V_ANA_N7V', 'IMIR_PDU_I_ANA_N7V'], ['FPE -7V Analog Voltage and Current']]
]

# Tab Description
description_Temperature = [
    # line 1 collum 1
    [['CRYO Temperatures'],
     # line 1 collum 2
     ['IGDP_MIR_ICE_T1P_CRYO', 'IGDP_MIR_ICE_T2R_CRYO', 'IGDP_MIR_ICE_T3LW_CRYO',
      'IGDP_MIR_ICE_T4SW_CRYO', 'IGDP_MIR_ICE_T5IMG_CRYO', 'IGDP_MIR_ICE_T6DECKCRYO',
      'IGDP_MIR_ICE_T7IOC_CRYO', 'IGDP_MIR_ICE_FW_CRYO', 'IGDP_MIR_ICE_CCC_CRYO',
      'IGDP_MIR_ICE_GW14_CRYO', 'IGDP_MIR_ICE_GW23_CRYO', 'IGDP_MIR_ICE_POMP_CRYO',
      'IGDP_MIR_ICE_POMR_CRYO', 'IGDP_MIR_ICE_IFU_CRYO', 'IGDP_MIR_ICE_IMG_CRYO'],
     # line 1 collum 3
     ['Deck Nominal Temperature (T1)', ' Deck Redundant Temperature (T2)', ' LW FPM I/F Temperature (T3)',
      ' SW FPM I/F Temperature (T4)', ' IM FPM I/F Temperature (T5)', ' A-B Strut Apex Temperature (T6)',
      ' IOC Temperature (T7)', ' FWA Temperature', ' CCC Temperature',
      ' DGA-A (GW14) Temperature', ' DGA-B (GW23) Temperature', ' POMH Nominal Temperature',
      ' POMH Redundant Temperature', ' MRS (CF) Cal. Source Temperature', ' Imager (CI) Cal. Source Temperature']],

    # line 2 collum 1
    [['IEC Temperatures'],
     # line 2 collum 2
     ['ST_ZTC1MIRIA', 'ST_ZTC2MIRIA', 'ST_ZTC1MIRIB',
      'ST_ZTC2MIRIB', 'IGDP_MIR_ICE_INTER_TEMP', 'IMIR_PDU_TEMP',
      'IMIR_IC_SCE_ANA_TEMP1', 'IMIR_SW_SCE_ANA_TEMP1', 'IMIR_LW_SCE_ANA_TEMP1',
      'IMIR_IC_SCE_DIG_TEMP', 'IMIR_SW_SCE_DIG_TEMP', 'IMIR_LW_SCE_DIG_TEMP'],
     # line 2 collum 3
     ['ICE IEC Panel Temp A', ' FPE IEC Panel Temp A', ' ICE IEC Panel Temp B',
      ' FPE IEC Panel Temp B', ' ICE internal Temperature', ' FPE PDU Temperature',
      ' FPE SCE Analogue board Temperature IC', ' FPE SCE Analogue board Temperature SW',
      ' FPE SCE Analogue board Temperature LW',
      ' FPE SCE Digital board Temperature IC', ' FPE SCE Digital board Temperature SW',
      ' FPE SCE Digital board Temperature LW']],

    # line 3
    [['Detector Temperatures'], ['IGDP_MIR_IC_DET_TEMP', 'IGDP_MIR_lW_DET_TEMP', 'IGDP_MIR_SW_DET_TEMP'],
     ['Detector Temperature (IC,SW&LW)']]
]

# Tab Description
description_weehl = [
    [['Filterwheel Ratio'], ['IMIR_HK_FW_POS_RATIO', 'IMIR_HK_FW_CUR_POS'],
     ['FW position sensor ratio (normalised) and commanded position']],
    [['DGA-A Ratio'], ['IMIR_HK_GW14_POS_RATIO', 'IMIR_HK_GW14_CUR_POS'],
     ['DGA-A position sensor ratio (normalised) and commanded position']],
    [['DGA-B Ratio'], ['IMIR_HK_GW23_POS_RATIO', 'IMIR_HK_GW23_CUR_POS'],
     ['DGA-B position sensor ratio (normalised) and commanded position']],
    [['CCC Ratio'], ['IMIR_HK_CCC_POS_RATIO', 'IMIR_HK_CCC_CUR_POS'],
     ['Contamination Control Cover position sensor ratio (normalised) and commanded position']]
]

# List of anomalys to be displayed on a certain page
list_mn_power = [
    'SE_ZIMIRICEA_IDLE',
    'SE_ZIMIRICEA_HV_ON',
    'SE_ZIMIRFPEA',
    'SE_ZIMIRCEA'
]

# List of anomalys to be displayed on a certain page
list_mn_temperature = [
    'IGDP_MIR_ICE_T1P_CRYO',
    'IGDP_MIR_ICE_T2R_CRYO',
    'IGDP_MIR_ICE_T3LW_CRYO',
    'IGDP_MIR_ICE_T4SW_CRYO',
    'IGDP_MIR_ICE_T5IMG_CRYO',
    'IGDP_MIR_ICE_T6DECKCRYO',
    'IGDP_MIR_ICE_T7IOC_CRYO',
    'IGDP_MIR_ICE_FW_CRYO',
    'IGDP_MIR_ICE_CCC_CRYO',
    'IGDP_MIR_ICE_GW14_CRYO',
    'IGDP_MIR_ICE_GW23_CRYO',
    'IGDP_MIR_ICE_POMP_CRYO',
    'IGDP_MIR_ICE_POMR_CRYO',
    'IGDP_MIR_ICE_IFU_CRYO',
    'IGDP_MIR_ICE_IMG_CRYO',
    'ST_ZTC1MIRIA',
    'ST_ZTC2MIRIA',
    'IMIR_PDU_TEMP',
    'IMIR_IC_SCE_ANA_TEMP1',
    'IMIR_SW_SCE_ANA_TEMP1',
    'IMIR_LW_SCE_ANA_TEMP1',
    'IMIR_IC_SCE_DIG_TEMP',
    'IMIR_SW_SCE_DIG_TEMP',
    'IMIR_LW_SCE_DIG_TEMP',
    'IGDP_MIR_IC_DET_TEMP',
    'IGDP_MIR_LW_DET_TEMP',
    'IGDP_MIR_SW_DET_TEMP',
]

# List of anomalys to be displayed on a certain page
list_mn_weelRatio = [
    'IMIR_HK_FW_POS_RATIO_FND',
    'IMIR_HK_FW_POS_RATIO_OPAQUE',
    'IMIR_HK_FW_POS_RATIO_F1000W',
    'IMIR_HK_FW_POS_RATIO_F1130W',
    'IMIR_HK_FW_POS_RATIO_F1280W',
    'IMIR_HK_FW_POS_RATIO_P750L',
    'IMIR_HK_FW_POS_RATIO_F1500W',
    'IMIR_HK_FW_POS_RATIO_F1800W',
    'IMIR_HK_FW_POS_RATIO_F2100W',
    'IMIR_HK_FW_POS_RATIO_F560W',
    'IMIR_HK_FW_POS_RATIO_FLENS',
    'IMIR_HK_FW_POS_RATIO_F2300C',
    'IMIR_HK_FW_POS_RATIO_F770W',
    'IMIR_HK_FW_POS_RATIO_F1550C',
    'IMIR_HK_FW_POS_RATIO_F2550W',
    'IMIR_HK_FW_POS_RATIO_F1140C',
    'IMIR_HK_FW_POS_RATIO_F2550WR',
    'IMIR_HK_FW_POS_RATIO_F1065C',
    'IMIR_HK_GW14_POS_RATIO_SHORT',
    'IMIR_HK_GW14_POS_RATIO_MEDIUM',
    'IMIR_HK_GW14_POS_RATIO_LONG',
    'IMIR_HK_GW23_POS_RATIO_SHORT',
    'IMIR_HK_GW23_POS_RATIO_MEDIUM',
    'IMIR_HK_GW23_POS_RATIO_LONG',
    'IMIR_HK_CCC_POS_RATIO_LOCKED',
    'IMIR_HK_CCC_POS_RATIO_OPEN',
    'IMIR_HK_CCC_POS_RATIO_CLOSED',
]

# List of anomalys to be displayed on a certain page
list_ms_bias = [
    'IGDP_MIR_IC_V_VDETCOM',
    'IGDP_MIR_SW_V_VDETCOM',
    'IGDP_MIR_LW_V_VDETCOM',
    'IGDP_MIR_IC_V_VSSOUT',
    'IGDP_MIR_SW_V_VSSOUT',
    'IGDP_MIR_LW_V_VSSOUT',
    'IGDP_MIR_IC_V_VRSTOFF',
    'IGDP_MIR_SW_V_VRSTOFF',
    'IGDP_MIR_LW_V_VRSTOFF',
    'IGDP_MIR_IC_V_VP',
    'IGDP_MIR_SW_V_VP',
    'IGDP_MIR_LW_V_VP',
    'IGDP_MIR_IC_V_VDDUC',
    'IGDP_MIR_SW_V_VDDUC',
    'IGDP_MIR_LW_V_VDDUC',
]

# List of anomalys to be displayed on a certain page
list_mn_fpeV = [
    'SE_ZIMIRICEA',
    'SE_ZIMIRIFPEA',
    'SE_ZIMIRFPEA',
    'SE_ZIMIRCEA',
]

# List of anomalys to be displayed on a certain page
list_mn_iceV = [
    'IMIR_HK_ICE_SEC_VOLT1',
    'IMIR_HK_ICE_SEC_VOLT3',
    'IMIR_HK_ICE_SEC_VOLT2',
    'IMIR_HK_ICE_SEC_VOLT4_IDLE',
    'IMIR_HK_ICE_SEC_VOLT4_HV_ON',
    'IMIR_HK_FW_POS_VOLT',
    'IMIR_HK_GW14_POS_VOLT',
    'IMIR_HK_GW23_POS_VOLT',
    'IMIR_HK_CCC_POS_VOLT',
]


# Unified Figure to standardise all plots
def get_figure(end, title, y_ax_label, width, hight, y_ax_range):
    p = figure(tools="pan,wheel_zoom,box_zoom,reset,save",
               toolbar_location="above",
               plot_width=width,
               plot_height=hight,
               x_range=time_delta(Time(end)),
               y_range=y_ax_range,
               x_axis_type='datetime',
               output_backend="webgl",
               x_axis_label='Date',
               y_axis_label=y_ax_label)

    p.xaxis.formatter = DatetimeTickFormatter(
        hours=["%Y-%m-%d ,%H:%M:%S.%f"],
        days=["%Y-%m-%d, %H:%M"],
        months=["%Y-%m-%d"],
        years=["%Y-%m-%d"],
    )

    p.grid.visible = True
    p.title.text = title
    pf.add_basic_layout(p)

    return p
