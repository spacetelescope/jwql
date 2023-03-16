#! /usr/bin/env python

"""Script to transfer postgres anomaly data to django models

Authors
-------

    - Bradley Sappington

Use
---

    This module is called as follows:
    ::
        $ python anomaly_db_transfer.py


Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql`` directory.
"""

import logging
import django
import os
import datetime

# These lines are needed in order to use the Django models in a standalone
# script (as opposed to code run as a result of a webpage request). If these
# lines are not run, the script will crash when attempting to import the
# Django models in the line below.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
django.setup()
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import make_aware

from jwql.database import database_interface as di
from jwql.utils.constants import JWST_INSTRUMENT_NAMES_MIXEDCASE
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.monitor_utils import initialize_instrument_monitor
from jwql.utils.utils import filesystem_path, get_config
from jwql.website.apps.jwql.models import RootFileInfo, Anomalies





@log_info
@log_fail
def transfer_anomalies():
    """Update the the Django anomalies model with all information in the existing postgres database.

    """
    instruments = ['nircam', 'miri', 'nirspec', 'niriss', 'fgs']
    for instrument in instruments:
        # Get the anomalies for this instrument
        table = getattr(di, '{}Anomaly'.format(JWST_INSTRUMENT_NAMES_MIXEDCASE[instrument.lower()]))
        query = di.session.query(table)
        logging.info('anomalies for {} are: {}'.format(instrument, table.columns))
        table_keys = ['id', 'root_file_info', 'flag_date', 'user']
        table_keys += table.columns
        table_keys = list(map(lambda x: x.lower(), table_keys))
        updated = 0

        anomaly_dict = {}
        rows = query.statement.execute().fetchall()
        for rowx, row in enumerate(rows):
            anomaly_dict = {}
            for ix, value in enumerate(row):
                if (table_keys[ix] == 'flag_date'):
                    #avoid warning for native DateTime when timezone is active
                    value = make_aware(value)
                anomaly_dict[table_keys[ix]] = value
                
            root_file_info_name = anomaly_dict['root_file_info']
            try:
                root_file_info_instance = RootFileInfo.objects.get(root_name=root_file_info_name)
            except ObjectDoesNotExist:
                logging.info('No root_file_info for {}'.format(root_file_info_name))
                continue

            try:
                del(anomaly_dict['id'])
                del(anomaly_dict['root_file_info'])
                anomalies, anomaly_created = Anomalies.objects.update_or_create(root_file_info=root_file_info_instance,
                                                                                defaults=anomaly_dict)
                if anomaly_created:
                    updated += 1
            except Exception as e:
                logging.warning('Failed to create {} with exception {}'.format(root_file_info_name, e))
        logging.info('Transferred {} anomalies for {}'.format(updated, instrument))

if __name__ == '__main__':
    module = os.path.basename(__file__).strip('.py')
    start_time, log_file = initialize_instrument_monitor(module)
    transfer_anomalies()
