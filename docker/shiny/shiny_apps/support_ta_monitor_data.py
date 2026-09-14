from astropy.io import fits
import os
from pathlib import Path
import shutil
import tempfile


EXP_TYPE_MAPPING = {
    "miri": "MIR_",
}

def _obs_list_from_astroquery(instrument, mode=""):
    from astroquery.mast import MastMissions
    mission = MastMissions(mission='jwst')
    exp_type = f"{EXP_TYPE_MAPPING[instrument.lower()]}{mode.upper()}*"
    columns = ['fileSetName', 'program', 'observtn', 'visit_id', 'exp_type', 'subarray']
    mode_sci = mission.query_criteria(exp_type=exp_type, select_cols=columns)
    visits = set(mode_sci['visit_id'])
    ta_exposures = mission.query_criteria(exp_type='MIR_TACQ', select_cols=columns)
    ta_list = ta_exposures[[v in visits for v in ta_exposures['visit_id']]]
    return ta_list

def _download_obs_from_astroquery(obs_list, current_obs, download_dir):
    from astroquery.mast import MastMissions
    mission = MastMissions(mission='jwst')
    obs_row = obs_list[obs_list['fileSetName'] == current_obs]
    data_products = mission.get_unique_product_list(obs_row)
    manifest = mission.download_products(
        data_products, extension="fits", flat=True, download_dir=download_dir
    )

def _uncal_acq_from_astroquery(data_dir, current_obs):
    pass

def _obs_list_from_jwql():
    pass

def _obs_list_from_filesystem():
    pass

class TADataSupplier():
    def __init__(self, instrument, mode=""):
        self.instrument = instrument.lower()
        self.mode = mode.lower()
        self.data_source = os.environ.get("SHINY_TA_DATA_SOURCE", "astroquery")
        self.current_obs = None
        self.data_dir = tempfile.mkdtemp()

    def __del__(self):
        if Path(self.data_dir).is_dir():
            shutil.rmtree(self.data_dir)

    @property
    def obs_list(self):
        if hasattr(self, "_data_table"):
            return self._data_table["obs_id"].tolist()
        if self.data_source == "astroquery":
            self._data_table = _obs_list_from_astroquery(self.instrument, self.mode)
        return self._data_table["fileSetName"].tolist()

    def select_obs(self, obs_name):
        if obs_name in self.obs_list:
            self.current_obs = obs_name
            if self.data_source == "astroquery":
                _download_obs_from_astroquery(self._data_table, self.current_obs, self.data_dir)

    def get_obs_uncal(self):
        pass

    def get_obs_cal(self):
        pass

    def get_obs_verification(self):
        pass
