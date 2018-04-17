"""Various utility functions for the jwql project.

Authors
-------

    Matthew Bourque

Use
---

    This module can be imported as such:

    >>> import utils
    settings = get_config()
"""

import json
import os

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def get_config():
    """Return a dictionary that holds the contents of the jwql config
    file.

    Returns
    -------
    settings : dict
        A dictionary that holds the contents of the config file.
    """

    with open(os.path.join(__location__, 'config.json'), 'r') as config_file:
        settings = json.load(config_file)

    return settings
