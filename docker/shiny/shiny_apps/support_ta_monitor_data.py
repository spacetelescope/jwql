from astropy.io import fits
import os


EXP_TYPE_MAPPING = {
    "miri": "MIR_TA*",
}

def _obs_list_from_astroquery(instrument):
    from astroquery.mast import MastMissions
    missions = MastMissions(mission="jwst")
    obs_table = missions.query_criteria(
        instrume=instrument.upper(), exp_type=EXP_TYPE_MAPPING[instrument]
    )
    return obs_table

def _obs_list_from_jwql():
    pass

def _obs_list_from_filesystem():
    pass

class TADataSupplier():
    def __init__(self, instrument):
        self.instrument = instrument.lower()
        self.data_source = os.environ.get("SHINY_TA_DATA_SOURCE", "astroquery")
        self.current_obs = None

    @property
    def obs_list(self):
        if hasattr(self, "_data_table"):
            return self._data_table["fileSetName"].tolist()
        if self.data_source == "astroquery":
            self._data_table = _obs_list_from_astroquery(self.instrument)
        return self._data_table["fileSetName"].tolist()
