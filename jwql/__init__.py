from importlib.metadata import version
from jwql.utils import utils

__version__ = version('jwql')
try:

    config_version = utils.get_config()['jwql_version']
    if __version__ != config_version:
        print(f"Warning: config file JWQL version is {config_version}, "
              f"while JWQL is using {__version__}")

except FileNotFoundError:
    print('Could not determine jwql config version')
