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

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from jwql.shared_tasks.shared_tasks import run_pipeline
from jwql.utils.utils import copy_files, get_config


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
