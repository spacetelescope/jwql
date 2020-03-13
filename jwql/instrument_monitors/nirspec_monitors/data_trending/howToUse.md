

# How to use the data trending tool

The data trending tool is used to display instrument mnemonics over a great time range to quickly identify anomalyes.
The tool consists of a `dasboard.py`  and a `dt_corn_job.py`  part.

##dt_corn_job.py
Run this file is you want to populate the sql database with mnemonics for a certain time frame.
Bevor running the `corn_job` pleas make shoure that the following conditions are met:

1. A valid MAST authentication token is present. You can get a token here: https://github.com/spacetelescope/jwst-dms-edb#example-usage
2. Bevor running the `corn_job` for the first time (this must only be done once) pleas run first the `utils/sql_interface.py`. This will generate a valide database in the directory `jwql/jwql/database`. 

Plese Note: Not all mnemonics are currently implemented in the mast database. For the dashboard to worke one needs at least one databoint for each mnmonic table. 
For this reason please copy a populated database in the directory `jwql/jwql/database` (and skip step 2 in the list above). This is a temporary workaround until all mnmemonics are includet in the mast database.
Please kontakt [Brian O'Sullivan (INS)](bosullivan@sciops.esa.int) for a valide database.

The `corn_job` always downloades the data for a given date. To download a specific date call `main_oneDay()`:
 ```python
def main_oneDay():
    day = '2019-07-17'
    get_data_day(day)
```
This will instruct the software to automatically download data for a specific date.
The `corn_job` also contains a sample function on how to download data from multiple dates `main_multipleDays()`
as well as a function to always download the data for a date relative to today `main_daily()`.

##dashboard.py
The dashbord function creates all visual bokeh elements to display the data trending monitor.
It must be included in the `jwql/jwql/website/apps/jwql/view.py` file, and forwarded to the corresponding data trending .html file.
 
 