#! /usr/bin/env python

"""
Tests for the redis/celery server infrastructure.

Authors
-------

    - Brian York

Use
---

    In order to run these tests, you need the following:
    
    - A running redis server (separate from the production server on pljwql2)
    - A running celery worker communicating with that redis server
    - A config.json file providing the redis URL, and pointing to the JWQL testing
      files.

    These tests are intended to be run from the command line, because I haven't yet 
    figured out a way to actually set up the entire environment in pytest:
    ::

        python test_redis_celery.py
"""

from astropy.io import ascii, fits
from collections import defaultdict
from collections import OrderedDict
from copy import deepcopy
import datetime
import logging
import numpy as np
import os
from pathlib import Path
from pysiaf import Siaf
import pytest
from tempfile import TemporaryDirectory

from jwql.instrument_monitors import pipeline_tools
from jwql.shared_tasks.shared_tasks import only_one, run_pipeline, run_parallel_pipeline
from jwql.utils import crds_tools, instrument_properties, monitor_utils
from jwql.utils.constants import JWST_INSTRUMENT_NAMES, JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.constants import FLAT_EXP_TYPES, DARK_EXP_TYPES
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.permissions import set_permissions
from jwql.utils.utils import copy_files, ensure_dir_exists, get_config, filesystem_path


def get_instrument(file_name):
    if 'miri' in file_name:
        return 'miri'
    elif 'nircam' in file_name:
        return 'nircam'
    elif 'nrc' in file_name:
        return 'nircam'
    elif 'niriss' in file_name:
        return 'niriss'
    elif 'nis' in file_name:
        return 'niriss'
    elif 'nirspec' in file_name:
        return 'nirspec'
    elif 'nrs' in file_name:
        return 'nirspec'
    elif 'guider' in file_name:
        return 'fgs'
    return 'unknown'


if __name__ == "__main__":
    config = get_config()
    p = Path(config['test_data'])
    
    for file in p.rglob("*uncal.fits"):
        print("Testing cal pipeline")
        with TemporaryDirectory() as working_dir:
            try:
                print("Running in {}".format(working_dir))
                file_name = os.path.basename(file)
                if "gs-" in file_name:
                    print("\tSkipping guide star file {}".format(file_name))
                    continue
                print("\tCopying {}".format(file))
                copy_files([file], working_dir)
                cal_file = os.path.join(working_dir, file_name)
                print("\t\tCalibrating {}".format(cal_file))
                instrument = get_instrument(file_name)
                outputs = run_pipeline(cal_file, "uncal", "all", instrument)
                print("\t\tDone {}".format(file))
            except Exception as e:
                print("ERROR: {}".format(e))

        print("Testing jump pipeline")
        with TemporaryDirectory() as working_dir:
            try:
                print("Running in {}".format(working_dir))
                file_name = os.path.basename(file)
                if "gs-" in file_name:
                    print("\tSkipping guide star file {}".format(file_name))
                    continue
                print("\tCopying {}".format(file))
                copy_files([file], working_dir)
                cal_file = os.path.join(working_dir, file_name)
                print("\t\tCalibrating {}".format(cal_file))
                instrument = get_instrument(file_name)
                outputs = run_pipeline(cal_file, "uncal", "all", instrument, jump_pipe=True)
                print("\t\tDone {}".format(file))
            except Exception as e:
                print("ERROR: {}".format(e))
    
    print("Done test")
