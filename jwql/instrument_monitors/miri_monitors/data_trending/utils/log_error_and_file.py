"""log_error_and_file.py

    This module can be used to produce logfiles as well as an commandline output.

    The aim of this class is to provide an easy to use possibility to generate
    a continues log of the software both in the cmd as well as in a log file.
    The log file has to be defined only once.

Authors
-------

    - [AIRBUS] Daniel Kübacher
    - [AIRBUS] Leo Stumpf

Use
---
        To include the module use:
    ::
        import jwql.instrument_monitors.miri_monitors.data_trending.utils.log_error_and_file as log_error_and_file

    Define once per project the used log file name with
    ::
        log_error_and_file.define_log_file('FILE_NAME.log')

    Define in each function in which you want to log data
    ::
        log = log_error_and_file.Log('NMAE_FUNCTION')

    Now to log strings use the log.log or log.info function

Dependencies
------------

    The file miri_database.db in the directory jwql/jwql/database/ must exist.

References
----------
    The code was developed in reference to the information provided in:
    ‘MIRI trend requestsDRAFT1900301.docx’

Notes
-----

    For further information please contact Brian O'Sullivan
"""
from datetime import datetime
import os

class Log:

    def __init__(self, function_name):
        function_name = function_name.upper()
        self.function_name = function_name

        f = open('log_control.txt', 'r')
        self.log_file = f.read()
        f.close()

    def test(self):
        f = open('log_control.txt', 'r')
        self.log_file = f.read()
        f.close()

    def log(self, input, type='INFO'):
        type = type.upper()

        str_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        str_type = '[' + type + ']'
        str_func = '[' + self.function_name + ']'
        str_print = str_type + '\t' + str_time + ' ' + str_func + ' ' + input

        color_red = '\33[31m'
        color_black = '\033[0m'

        # write to file
        f = open(self.log_file, 'a')
        f.write(str_print + '\n')
        f.close()

        if type == 'ERROR' or type == 'ERR':
            str_print = color_red + str_print + color_black

        # write to cmd
        print(str_print)

    def info(self, input):

        if type(input) == type('str'):
            zw = input
            input = []
            input.append(zw)

        # make useful frame
        input.insert(0, "*******************************")
        input.append("*******************************")

        # output
        f = open(self.log_file, 'a')
        for str in input:
            f.write('* ' + str + '\n')
            print('* ' + str)
        f.close()

def define_log_file(log_file_name):
    # save name
    f = open('log_control.txt', 'w')
    f.write(log_file_name)
    f.close()

    # clear log file and create
    f = open(log_file_name, 'w')
    f.close()

def delete_log_file():
    os.remove('log_control.txt')