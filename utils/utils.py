"""Various utility functions for the jwql project.

Authors
-------

    Matthew Bourque

Use
---

    This module can be imported as such:

    >>> import utils
    config_yaml, config_json = get_config()
"""

import json
import yaml


def get_config():
    """Return dictionaries that hold the contents of the jwql config
    files.

    Returns
    -------
    config_yaml : dict
        A dictionary that holds the contents of the yaml config file.
    config_json: dict
        A dictionary that holds the contents of the json config file.
    """

    with open('config.yml', 'r') as f:
        config_yaml = yaml.load(f)

    with open('config.json', 'r') as f:
        config_json = json.load(f)

    return config_yaml, config_json
