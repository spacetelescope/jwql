import os

import numpy as np

from jwql.bokeh_templating import BokehTemplate
from jwql.utils.utils import get_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class DarkMonitor(BokehTemplate):

    def pre_init(self):

        self._embed = True

        #app design
        self.format_string = None
        self.interface_file = os.path.join(SCRIPT_DIR, "dark_monitor_interface.yml")

        self.settings = get_config()
        self.output_dir = self.settings['outputs']

        self.load_data()
        self.timestamps = np.arange(10) / 10.
        self.dark_current = np.arange(10)


    def post_init(self):

        self.refs['dark_current_yrange'].start = min(self.dark_current)
        self.refs['dark_current_yrange'].end = max(self.dark_current)


    def load_data(self):
        #actually load data:
        new_data = np.arange(10) / 20

        #update columndatasource
        self.dark_current = new_data

DarkMonitor()
