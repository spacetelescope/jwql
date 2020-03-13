"""mnemonic.py

    The module includes several lists to import to MIRI data trending monitor program.
    The lists are used for data aquisation and to set up the initial database.

Authors
-------

    - [AIRBUS] Daniel Kübacher
    - [AIRBUS] Leo Stumpf

Use
---
    import mnemoncis as mn

Dependencies
------------
    -

References
----------
    The code was developed in reference to the information provided in:
    ‘MIRI trend requestsDRAFT1900301.docx’

Notes
-----

    For further information please contact Brian O'Sullivan
"""

# min job mnemonics
miri_mnemonic_min = [
    'IGDP_MIR_IC_DET_TEMP',
    'IGDP_MIR_IC_V_VDDUC',
    'IGDP_MIR_IC_V_VDETCOM',
    'IGDP_MIR_IC_V_VP',
    'IGDP_MIR_IC_V_VRSTOFF',
    'IGDP_MIR_IC_V_VSSOUT',
    'IGDP_MIR_ICE_CCC_CRYO',
    'IGDP_MIR_ICE_FW_CRYO',
    'IGDP_MIR_ICE_GW14_CRYO',
    'IGDP_MIR_ICE_GW23_CRYO',
    'IGDP_MIR_ICE_IFU_CRYO',
    'IGDP_MIR_ICE_IMG_CRYO',
    'IGDP_MIR_ICE_INTER_TEMP',
    'IGDP_MIR_ICE_POMP_CRYO',
    'IGDP_MIR_ICE_POMR_CRYO',
    'IGDP_MIR_ICE_T1P_CRYO',
    'IGDP_MIR_ICE_T2R_CRYO',
    'IGDP_MIR_ICE_T3LW_CRYO',
    'IGDP_MIR_ICE_T4SW_CRYO',
    'IGDP_MIR_ICE_T5IMG_CRYO',
    'IGDP_MIR_ICE_T6DECKCRYO',
    'IGDP_MIR_ICE_T7IOC_CRYO',
    'IGDP_MIR_LW_DET_TEMP',
    'IGDP_MIR_LW_V_VDDUC',
    'IGDP_MIR_LW_V_VDETCOM',
    'IGDP_MIR_LW_V_VP',
    'IGDP_MIR_LW_V_VRSTOFF',
    'IGDP_MIR_LW_V_VSSOUT',
    'IGDP_MIR_SW_DET_TEMP',
    'IGDP_MIR_SW_V_VDDUC',
    'IGDP_MIR_SW_V_VDETCOM',
    'IGDP_MIR_SW_V_VP',
    'IGDP_MIR_SW_V_VRSTOFF',
    'IGDP_MIR_SW_V_VSSOUT',
    'IMIR_HK_ICE_SEC_VOLT1',
    'IMIR_HK_ICE_SEC_VOLT4',
    'IMIR_HK_IFU_CAL_LOOP',
    'IMIR_HK_IMG_CAL_LOOP',
    'IMIR_HK_POM_LOOP',
    'IMIR_IC_SCE_ANA_TEMP1',
    'IMIR_IC_SCE_DIG_TEMP',
    'IMIR_LW_SCE_ANA_TEMP1',
    'IMIR_LW_SCE_DIG_TEMP',
    'IMIR_PDU_I_ANA_5V',
    'IMIR_PDU_I_ANA_7V',
    'IMIR_PDU_I_ANA_N5V',
    'IMIR_PDU_I_ANA_N7V',
    'IMIR_PDU_I_DIG_5V',
    'IMIR_PDU_TEMP',
    'IMIR_PDU_V_ANA_5V',
    'IMIR_PDU_V_ANA_7V',
    'IMIR_PDU_V_ANA_N5V',
    'IMIR_PDU_V_ANA_N7V',
    'IMIR_PDU_V_DIG_5V',
    'IMIR_PDU_V_REF_2R5V',
    'IMIR_SPW_V_DIG_2R5V',
    'IMIR_SW_SCE_ANA_TEMP1',
    'IMIR_SW_SCE_DIG_TEMP',
    'IGDP_IT_MIR_IC_STATUS',
    'IGDP_IT_MIR_LW_STATUS',
    'IGDP_IT_MIR_SW_STATUS',
    'SE_ZIMIRFPEA',
    'SE_ZIMIRICEA',
    'SE_ZBUSVLT',
    'SI_GZMPT1AK',
    'SI_GZMPT2AK',
    'ST_ZTC1MIRIA',
    'ST_ZTC2MIRIA',
    'ST_ZTC1MIRIB',
]
mnemonic_cond_1 = [
    "SE_ZIMIRICEA",
    "SE_ZBUSVLT",
    "IMIR_HK_ICE_SEC_VOLT4",
    "IGDP_MIR_ICE_INTER_TEMP",

    "ST_ZTC1MIRIA",
    "ST_ZTC1MIRIB",

    "IGDP_MIR_ICE_T1P_CRYO",
    "IGDP_MIR_ICE_T2R_CRYO",
    "IGDP_MIR_ICE_T3LW_CRYO",
    "IGDP_MIR_ICE_T4SW_CRYO",
    "IGDP_MIR_ICE_T5IMG_CRYO",
    "IGDP_MIR_ICE_T6DECKCRYO",
    "IGDP_MIR_ICE_T7IOC_CRYO",
    "IGDP_MIR_ICE_FW_CRYO",
    "IGDP_MIR_ICE_CCC_CRYO",
    "IGDP_MIR_ICE_GW14_CRYO",
    "IGDP_MIR_ICE_GW23_CRYO",
    "IGDP_MIR_ICE_POMP_CRYO",
    "IGDP_MIR_ICE_POMR_CRYO",
    "IGDP_MIR_ICE_IFU_CRYO",
    "IGDP_MIR_ICE_IMG_CRYO"]
mnemonic_cond_2 = [
    "SE_ZIMIRFPEA",

    "IMIR_PDU_V_DIG_5V",
    "IMIR_PDU_I_DIG_5V",
    "IMIR_PDU_V_ANA_5V",
    "IMIR_PDU_I_ANA_5V",

    "IMIR_PDU_V_ANA_N5V",
    "IMIR_PDU_I_ANA_N5V",

    "IMIR_PDU_V_ANA_7V",
    "IMIR_PDU_I_ANA_7V",

    "IMIR_PDU_V_ANA_N7V",
    "IMIR_PDU_I_ANA_N7V",

    "IMIR_SPW_V_DIG_2R5V",
    "IMIR_PDU_V_REF_2R5V",

    "IGDP_MIR_IC_V_VDETCOM",
    "IGDP_MIR_SW_V_VDETCOM",
    "IGDP_MIR_LW_V_VDETCOM",

    "IGDP_MIR_IC_V_VSSOUT",
    "IGDP_MIR_SW_V_VSSOUT",
    "IGDP_MIR_LW_V_VSSOUT",
    "IGDP_MIR_IC_V_VRSTOFF",

    "IGDP_MIR_SW_V_VRSTOFF",
    "IGDP_MIR_LW_V_VRSTOFF",

    "IGDP_MIR_IC_V_VP",
    "IGDP_MIR_SW_V_VP",
    "IGDP_MIR_LW_V_VP",

    "IGDP_MIR_IC_V_VDDUC",
    "IGDP_MIR_SW_V_VDDUC",
    "IGDP_MIR_LW_V_VDDUC",

    # "IMIR_PDU_TEMP",

    # "ST_ZTC2MIRIA",
    # "ST_ZTC2MIRIB",

    "IMIR_IC_SCE_ANA_TEMP1",
    "IMIR_SW_SCE_ANA_TEMP1",
    "IMIR_LW_SCE_ANA_TEMP1",

    "IMIR_IC_SCE_DIG_TEMP",
    "IMIR_SW_SCE_DIG_TEMP",
    "IMIR_LW_SCE_DIG_TEMP",

    "IGDP_MIR_IC_DET_TEMP",
    "IGDP_MIR_LW_DET_TEMP",
    "IGDP_MIR_SW_DET_TEMP"]

# day job mnemonics
mnemonic_cond_3 = [
    "IMIR_HK_ICE_SEC_VOLT1",
    "IMIR_HK_ICE_SEC_VOLT2",
    "IMIR_HK_ICE_SEC_VOLT3",
    "IMIR_HK_ICE_SEC_VOLT4",
    "SE_ZIMIRICEA"]
whould_day_nm = [
    "IMIR_HK_ICE_SEC_VOLT1",
    "mak_err",
    "IMIR_HK_ICE_SEC_VOLT2",
    "IMIR_HK_ICE_SEC_VOLT3",
    "IMIR_HK_ICE_SEC_VOLT4",
    "SE_ZIMIRICEA",
    "IMIR_HK_FW_POS_VOLT",
    "IMIR_HK_FW_POS_RATIO",
    "IMIR_HK_FW_CUR_POS",
    "IMIR_HK_GW14_POS_VOLT",
    "IMIR_HK_GW14_POS_RATIO",
    "IMIR_HK_GW14_CUR_POS",
    "IMIR_HK_GW23_POS_VOLT",
    "IMIR_HK_GW23_POS_RATIO",
    "IMIR_HK_GW23_CUR_POS",
    "IMIR_HK_CCC_POS_VOLT",
    "IMIR_HK_CCC_POS_RATIO",
    "IMIR_HK_CCC_CUR_POS",
    "IMIR_HK_CCC_ACTUATOR",
]
whould_day = mnemonic_cond_3 + whould_day_nm

# database mnemonics
mnemonic_wheelpositions = [
    "IMIR_HK_FW_POS_RATIO_FND",
    "IMIR_HK_FW_POS_RATIO_OPAQUE",
    "IMIR_HK_FW_POS_RATIO_F1000W",
    "IMIR_HK_FW_POS_RATIO_F1130W",
    "IMIR_HK_FW_POS_RATIO_F1280W",
    "IMIR_HK_FW_POS_RATIO_P750L",
    "IMIR_HK_FW_POS_RATIO_F1500W",
    "IMIR_HK_FW_POS_RATIO_F1800W",
    "IMIR_HK_FW_POS_RATIO_F2100W",
    "IMIR_HK_FW_POS_RATIO_F560W",
    "IMIR_HK_FW_POS_RATIO_FLENS",
    "IMIR_HK_FW_POS_RATIO_F2300C",
    "IMIR_HK_FW_POS_RATIO_F770W",
    "IMIR_HK_FW_POS_RATIO_F1550C",
    "IMIR_HK_FW_POS_RATIO_F2550W",
    "IMIR_HK_FW_POS_RATIO_F1140C",
    "IMIR_HK_FW_POS_RATIO_F2550WR",
    "IMIR_HK_FW_POS_RATIO_F1065C",

    "IMIR_HK_GW14_POS_RATIO_SHORT",
    "IMIR_HK_GW14_POS_RATIO_MEDIUM",
    "IMIR_HK_GW14_POS_RATIO_LONG",

    "IMIR_HK_GW23_POS_RATIO_SHORT",
    "IMIR_HK_GW23_POS_RATIO_MEDIUM",
    "IMIR_HK_GW23_POS_RATIO_LONG",

    "IMIR_HK_CCC_POS_RATIO_LOCKED",
    "IMIR_HK_CCC_POS_RATIO_OPEN",
    "IMIR_HK_CCC_POS_RATIO_CLOSED"]
mnemonic_set_database = [
    'IGDP_MIR_ICE_CCC_CRYO',
    'IGDP_MIR_ICE_FW_CRYO',
    'IGDP_MIR_ICE_GW14_CRYO',
    'IGDP_MIR_ICE_GW23_CRYO',
    'IGDP_MIR_ICE_IFU_CRYO',
    'IGDP_MIR_ICE_IMG_CRYO',
    'IGDP_MIR_ICE_INTER_TEMP',
    'IGDP_MIR_ICE_POMP_CRYO',
    'IGDP_MIR_ICE_POMR_CRYO',
    'IGDP_MIR_ICE_T1P_CRYO',
    'IGDP_MIR_ICE_T2R_CRYO',
    'IGDP_MIR_ICE_T3LW_CRYO',
    'IGDP_MIR_ICE_T4SW_CRYO',
    'IGDP_MIR_ICE_T5IMG_CRYO',
    'IGDP_MIR_ICE_T6DECKCRYO',
    'IGDP_MIR_ICE_T7IOC_CRYO',
    'IGDP_MIR_IC_DET_TEMP',
    'IGDP_MIR_IC_V_VDDUC',
    'IGDP_MIR_IC_V_VDETCOM',
    'IGDP_MIR_IC_V_VP',
    'IGDP_MIR_IC_V_VRSTOFF',
    'IGDP_MIR_IC_V_VSSOUT',
    'IGDP_MIR_LW_DET_TEMP',
    'IGDP_MIR_LW_V_VDDUC',
    'IGDP_MIR_LW_V_VDETCOM',
    'IGDP_MIR_LW_V_VP',
    'IGDP_MIR_LW_V_VRSTOFF',
    'IGDP_MIR_LW_V_VSSOUT',
    'IGDP_MIR_SW_DET_TEMP',
    'IGDP_MIR_SW_V_VDDUC',
    'IGDP_MIR_SW_V_VDETCOM',
    'IGDP_MIR_SW_V_VP',
    'IGDP_MIR_SW_V_VRSTOFF',
    'IGDP_MIR_SW_V_VSSOUT',
    'IMIR_HK_CCC_POS_VOLT',
    'IMIR_HK_FW_POS_VOLT',
    'IMIR_HK_GW14_POS_VOLT',
    'IMIR_HK_GW23_POS_VOLT',
    'IMIR_HK_ICE_SEC_VOLT1',
    'IMIR_HK_ICE_SEC_VOLT2',
    'IMIR_HK_ICE_SEC_VOLT3',
    'IMIR_HK_ICE_SEC_VOLT4_HV_ON',
    'IMIR_HK_ICE_SEC_VOLT4_IDLE',
    'IMIR_IC_SCE_ANA_TEMP1',
    'IMIR_IC_SCE_DIG_TEMP',
    'IMIR_LW_SCE_ANA_TEMP1',
    'IMIR_LW_SCE_DIG_TEMP',
    'IMIR_PDU_I_ANA_5V',
    'IMIR_PDU_I_ANA_7V',
    'IMIR_PDU_I_ANA_N5V',
    'IMIR_PDU_I_ANA_N7V',
    'IMIR_PDU_I_DIG_5V',
    'IMIR_PDU_TEMP',
    'IMIR_PDU_V_ANA_5V',
    'IMIR_PDU_V_ANA_7V',
    'IMIR_PDU_V_ANA_N5V',
    'IMIR_PDU_V_ANA_N7V',
    'IMIR_PDU_V_DIG_5V',
    'IMIR_PDU_V_REF_2R5V',
    'IMIR_SPW_V_DIG_2R5V',
    'IMIR_SW_SCE_ANA_TEMP1',
    'IMIR_SW_SCE_DIG_TEMP',
    'SE_ZBUSVLT',
    'SE_ZIMIRFPEA',
    'SE_ZIMIRICEA_HV_ON',
    'SE_ZIMIRICEA_IDLE',
    'ST_ZTC1MIRIA',
    'ST_ZTC1MIRIB',
    'ST_ZTC2MIRIA',
    'ST_ZTC2MIRIB'
]

# Weel positions and values
fw_positions = [
    "FND",
    "OPAQUE",
    "F1000W",
    "F1130W",
    "F1280W",
    "P750L",
    "F1500W",
    "F1800W",
    "F2100W",
    "F560W",
    "FLENS",
    "F2300C",
    "F770W",
    "F1550C",
    "F2550W",
    "F1140C",
    "F2550WR",
    "F1065C"]
gw_positions = [
    "SHORT",
    "MEDIUM",
    "LONG"]
ccc_positions = [
    "LOCKED",
    "OPEN",
    "CLOSED"]
fw_nominals = {
    "FND": -164.46,
    "OPAQUE": 380.42,
    "F1000W": -23.88,
    "F1130W": 138.04,
    "F1280W": -298.14,
    "P750L": 12.79,
    "F1500W": -377.32,
    "F1800W": 435.61,
    "F2100W": -126.04,
    "F560W": 218.13,
    "FLENS": -212.44,
    "F2300C": 306.03,
    "F770W": -61.90,
    "F1550C": 188.88,
    "F2550W": -323.65,
    "F1140C": 83.08,
    "F2550WR": -255.18,
    "F1065C": 261.62}
gw23_nominals = {
    "SHORT": 619.81,
    "MEDIUM": 373.31,
    "LONG": 441.4}
gw14_nominals = {
    "SHORT": 627.49,
    "MEDIUM": 342.71,
    "LONG": 408.75}
ccc_nominals = {
    "LOCKED": 577.23,
    "OPEN": 507.86,
    "CLOSED": 399.90}

