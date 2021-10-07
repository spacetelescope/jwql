import os
import pkg_resources
from jwql.utils import utils

module_path = pkg_resources.resource_filename('jwql', '')
setup_path = os.path.normpath(os.path.join(module_path, '../setup.py'))

try:
    with open(setup_path) as f:
        data = f.readlines()

    for line in data:
        if 'VERSION =' in line:
            __version__ = line.split(' ')[-1].replace("'", "").strip()

    config_version = utils.get_config()['jwql_version']
    if __version__ != config_version:
        print("Warning: config file JWQL version is {}, while JWQL is using {}".format(config_version, __version__))

except FileNotFoundError:
    print('Could not determine jwql version')
    __version__ = '0.0.0'
