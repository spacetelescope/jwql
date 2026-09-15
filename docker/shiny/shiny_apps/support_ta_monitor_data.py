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

def _obs_list_from_jwql():
    pass

def _obs_list_from_filesystem():
    pass


def _download_obs_from_astroquery(obs_list, current_obs, download_dir):
    from astroquery.mast import MastMissions
    mission = MastMissions(mission='jwst')
    obs_row = obs_list[obs_list['fileSetName'] == current_obs]
    data_products = mission.get_unique_product_list(obs_row)
    for row in data_products:
        print(row['uri'])
        if row['uri'][-8:] == "cal.fits":
            result = mission.download_file(row['uri'], local_path=download_dir)
            print(result)


def _uncal_acq_from_astroquery(data_dir, current_obs):
    print(f"Retrieving uncalibrated data with {data_dir} {current_obs}")
    data_path = Path(data_dir)
    data_files = list(data_path.glob(f"{current_obs}*uncal.fits"))
    print(data_files)
    if len(data_files) > 0:
        return data_files[0]
    return None


def _cal_acq_from_astroquery(data_dir, current_obs):
    print(f"Retrieving calibrated data with {data_dir} {current_obs}")
    data_path = Path(data_dir)
    data_files = list(data_path.glob(f"{current_obs}*_cal.fits"))
    print(data_files)
    if len(data_files) > 0:
        return data_files[0]
    return None


def _check_acq_from_astroquery(data_dir, current_obs):
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
            return self._data_table["fileSetName"].tolist()
        if self.data_source == "astroquery":
            self._data_table = _obs_list_from_astroquery(self.instrument, self.mode)
        return self._data_table["fileSetName"].tolist()

    def select_obs(self, obs_name):
        if obs_name in self.obs_list and self.current_obs != obs_name:
            self.current_obs = obs_name
            if self.data_source == "astroquery":
                _download_obs_from_astroquery(self._data_table, self.current_obs, self.data_dir)

    def get_obs_uncal(self):
        if self.data_source == "astroquery":
            return _uncal_acq_from_astroquery(self.data_dir, self.current_obs)

    def get_obs_cal(self):
        if self.data_source == "astroquery":
            return _cal_acq_from_astroquery(self.data_dir, self.current_obs)

    def get_obs_verification(self):
        pass
