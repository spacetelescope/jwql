#!/usr/bin/env python3

"""
This module is meant to monitor target acquisition offsets and failures,
as described here: 
    
    https://innerspace.stsci.edu/pages/viewpage.action?pageId=132279653

Authors
-------

    - Gray Kanarek
    - Charles Profitt

Use
---

    This module can be executed from the command line:

    ::

        python monitor_ta.py

    Alternatively, it can be called from scripts with the following
    import statements:

    ::
        from monitor_filesystem import MonitorTA


    Required arguments (in a ``config.json`` file):
    ``outputs`` - The path to the output files needs to be in a
    ``config.json`` file in the ``utils`` directory.


Dependencies
------------

    The user must have a configuration file named ``config.json``
    placed in the ``utils`` directory.

Notes
-----

    TBD
    
"""

import numpy as np

from bokeh_templating import BokehTemplate




class MonitorTA(BokehTemplate):
    
    def pre_init(self):
        pass
    
    def post_init(self):
        pass