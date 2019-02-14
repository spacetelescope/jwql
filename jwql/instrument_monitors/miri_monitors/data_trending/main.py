import numpy as np
import astropy as ap
import functions as func
import sql_interface as sql
import statistics

from bokeh.plotting import figure, output_file, show


testdata=[
'imir_190130_otis229FOFTLM2019030204146194.CSV',
'imir_190130_otis240FOFTLM2019030210631185.CSV',
'imir_190130_otis230FOFTLM2019030204240886.CSV',  
'imir_190130_otis241FOFTLM2019030210651672.CSV',
'imir_190130_otis231FOFTLM2019030204334644.CSV',  
'imir_190130_otis242FOFTLM2019030210728909.CSV',
'imir_190130_otis232FOFTLM2019030204455835.CSV',  
'imir_190130_otis243FOFTLM2019030210744062.CSV',
'imir_190130_otis233FOFTLM2019030204521412.CSV',  
'imir_190130_otis244FOFTLM2019030210809362.CSV',
'imir_190130_otis234FOFTLM2019030204555665.CSV',  
'imir_190130_otis245FOFTLM2019030210828095.CSV',
'imir_190130_otis235FOFTLM2019030204617145.CSV',  
'imir_190130_otis246FOFTLM2019030210852965.CSV',
'imir_190130_otis236FOFTLM2019030204651604.CSV',  
'imir_190130_otis247FOFTLM2019030210914141.CSV',
'imir_190130_otis237FOFTLM2019030204712019.CSV',  
'imir_190130_otis248FOFTLM2019030210940944.CSV',
'imir_190130_otis238FOFTLM2019030204738855.CSV',  
'imir_190130_otis249FOFTLM2019030211002524.CSV',
'imir_190130_otis239FOFTLM2019030204805611.CSV',  
'imir_190130_otis250FOFTLM2019030211032094.CSV']

#programm start
##################################################
  
#default path adress for trainigData

directory='/home/daniel/STScI/trainigData/'



##################################################

"""
Condition 1 for mnemonics below: 

HV not active.
IMIR_HK_ICE_SEC_VOLT1<1V

Cal sources inactive
IMIR_HK_IMG_CAL_LOOP=OFF
IMIR_HK_IFU_CAL_LOOP=OFF

POM heater inactive
IMIR_HK_POM_LOOP=OFF

######################################
SE_ZIMIRICEA
GP_ZPSVOLT
IMIR_HK_ICE_SEC_VOLT4
IGDP_MIR_ICE_INTER_TEMP
SI_GZMPT1AK
IGDP_MIR_ICE_T1P_CRYO
IGDP_MIR_ICE_T2R_CRYO
IGDP_MIR_ICE_T3LW_CRYO
IGDP_MIR_ICE_T4SW_CRYO
IGDP_MIR_ICE_T5IMG_CRYO
IGDP_MIR_ICE_T6DECKCRYO
IGDP_MIR_ICE_T7IOC_CRYO
IGDP_MIR_ICE_FW_AMB
IGDP_MIR_ICE_CCC_CRYO
IGDP_MIR_ICE_GW14_CRYO
IGDP_MIR_ICE_GW23_CRYO
IGDP_MIR_ICE_POMP_CRYO
IGDP_MIR_ICE_POMR_CRYO
IGDP_MIR_ICE_IFU_CRYO
IGDP_MIR_ICE_IMG_CRYO
######################################
"""


output=[]



path = directory+test_data[1]


i=imported_file=func.mnemonics(path)

#setup condition for data retrieval 
con_set_1 = [                                               \
func.equal(i.mnemonic('IMIR_HK_IMG_CAL_LOOP'),'OFF'),       \
func.equal(i.mnemonic('IMIR_HK_IFU_CAL_LOOP'),'OFF'),       \
func.equal(i.mnemonic('IMIR_HK_POM_LOOP'),'OFF'),           \
func.smaller(i.mnemonic('IMIR_HK_ICE_SEC_VOLT1'),1) ]

condition_1=func.condition(con_set_1)

useful_data=[]

for element in i.mnemonic('IMIR_HK_ICE_SEC_VOLT4'):
    if condition_1.state(element['Primary Time']):
        useful_data.append(float(element['EU Value']))

try:
    average=sum(useful_data)/len(useful_data)
    deviation=statistics.stdev(useful_data)

    output.append((average,deviation))
    print("Average of SE_ZIMIRICEA ({} values) is: {} , Deviation: {}" \
        .format(len(useful_data),average, deviation))

except ZeroDivisionError:
    print('No useful data for SE_ZIMIRICEA')


print(output)




#simple bokeh plot for retrieved and analysed data 
x=np.linspace(0,len(output))
y1=[]

for element in output: 
    y1.append(element[0])


output_file("line.html")

p = figure(plot_width=400, plot_height=400)

# add a line renderer
p.line(x,y1, line_width=2)

show(p)


##################################################
#programm end 
