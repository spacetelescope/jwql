from astropy.io import fits
from astropy import table as astropy_table
import logging
import os
from pathlib import Path
import shutil
import tempfile

from jwql.utils.utils import filesystem_path, filename_parser

from support_ta_monitor_plots import TAPlot


EXP_TYPE_MAPPING = {
    "miri": "MIR_",
}

def _obs_list_from_astroquery(instrument, mode=""):
    from astroquery.mast import MastMissions
    logging.info(f"Loading {instrument} {mode} exposures")
    logging.info("Loading mission")
    mission = MastMissions(mission='jwst')
    exp_type = f"{EXP_TYPE_MAPPING[instrument.lower()]}{mode.upper()}*"
    logging.info(f"Looking for exposure type {exp_type}")
    columns = ['fileSetName', 'program', 'observtn', 'visit_id', 'exp_type', 'subarray']
    mode_sci = mission.query_criteria(exp_type=exp_type, select_cols=columns, limit=500000)
    logging.info(f"Found {len(mode_sci)} exposures")
    visits = set(mode_sci['visit_id'])
    logging.info(f"{len(visits)} unique visits")
    exp_type = f"{EXP_TYPE_MAPPING[instrument.lower()]}TACQ"
    logging.info(f"Loading {instrument} TA exposures {exp_type}")
    ta_exposures = mission.query_criteria(exp_type=exp_type, select_cols=columns, limit=500000)
    logging.info(f"Found {len(ta_exposures)} unique exposures")
    logging.info("Combining exposure lists")
    ta_list = ta_exposures[[v in visits for v in ta_exposures['visit_id']]]
    logging.info(f"Found {len(ta_list)} {mode} TA exposures")
    return ta_list

def _obs_list_from_jwql(instrument, mode=""):
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()
    from jwql.website.apps.jwql.models import Observation, RootFileInfo
    exp_type = f"{EXP_TYPE_MAPPING[instrument]}TACQ"
    exptypes = mode.upper()
    results = RootFileInfo.objects.filter(obsnum__exptypes__contains=exptypes).filter(exp_type=exp_type)
    obs_list = [x.root_name for x in results if "seg" not in x.root_name]
    return sorted(obs_list)

def _obs_list_from_filesystem():
    pass


def _download_obs_from_astroquery(obs_list, current_obs, download_dir):
    from astroquery.mast import MastMissions
    mission = MastMissions(mission='jwst')
    obs_row = obs_list[obs_list['fileSetName'] == current_obs]
    data_products = mission.get_unique_product_list(obs_row)
    for row in data_products:
        logging.info(row['uri'])
        if row['uri'][-8:] == "cal.fits":
            result = mission.download_file(row['uri'], local_path=download_dir)
            logging.info(result)


def _uncal_acq_from_astroquery(data_dir, current_obs):
    logging.info(f"Retrieving uncalibrated data with {data_dir} {current_obs}")
    data_path = Path(data_dir)
    data_files = list(data_path.glob(f"{current_obs}*uncal.fits"))
    logging.info(data_files)
    if len(data_files) > 0:
        return data_files[0]
    return None

def _uncal_acq_from_jwql(current_obs):
    if current_obs is None:
        return None
    from jwql.utils.utils import filesystem_path
    logging.info(f"Retrieving uncalibrated data for {current_obs}")
    try:
        return filesystem_path(f"{current_obs}_uncal.fits")
    except FileNotFoundError as e:
        logging.info(f"Exposure {current_obs} not found: {e}")
    return None


def _cal_acq_from_astroquery(data_dir, current_obs):
    logging.info(f"Retrieving calibrated data with {data_dir} {current_obs}")
    data_path = Path(data_dir)
    data_files = list(data_path.glob(f"{current_obs}*_cal.fits"))
    logging.info(data_files)
    if len(data_files) > 0:
        return data_files[0]
    return None

def _cal_acq_from_jwql(current_obs):
    if current_obs is None:
        return None
    from jwql.utils.utils import filesystem_path
    logging.info(f"Retrieving uncalibrated data for {current_obs}")
    try:
        return filesystem_path(f"{current_obs}_cal.fits")
    except FileNotFoundError as e:
        logging.info(f"Exposure {current_obs} not found: {e}")
    try:
        return filesystem_path(f"{current_obs}_rate.fits")
    except FileNotFoundError as e:
        logging.info(f"Exposure {current_obs} not found: {e}")
    return None


def _check_acq_from_astroquery(instrument, ta_list, data_dir, current_obs):
    from astroquery.mast import MastMissions
    mission = MastMissions(mission='jwst')
    exp_type = f"{EXP_TYPE_MAPPING[instrument.lower()]}TACONFIRM"
    logging.info(f"Looking for exposures of type {exp_type} with name {current_obs}")
    columns = ['fileSetName', 'program', 'observtn', 'visit_id', 'exp_type', 'subarray']
    ta_exposures = mission.query_criteria(exp_type=exp_type, select_cols=columns, limit=500000)
    logging.info(f"Found {len(ta_exposures)} exposures")
    ta_row = ta_list[ta_list['fileSetName'] == current_obs]
    if len(ta_row) == 0:
        logging.info("No exposures populating TA list yet")
        return None
    logging.info(f"Looking for matches to {ta_row[0]['fileSetName']} {ta_row[0]['program']} {ta_row[0]['visit_id']} {ta_row[0]['observtn']}")
    found_rows = ta_exposures[ta_exposures['program'] == ta_row[0]['program']]
    if len(found_rows) == 0:
        logging.info("No Confirmation Exposure Found (by program)")
        logging.info(set([p for p in ta_exposures['program']]))
        return None
    logging.info(f"Found {len(found_rows)} exposures")
    logging.info(set([p for p in found_rows['visit_id']]))
    found_rows = found_rows[found_rows['visit_id'] == ta_row[0]['visit_id']]
    if len(found_rows) == 0:
        logging.info("No Confirmation Exposure Found (by visit)")
        return None
    found_rows = found_rows[found_rows['observtn'] == ta_row[0]['observtn']]
    if len(found_rows) == 0:
        logging.info("No Confirmation Exposure Found (by observation)")
        return None
    logging.info(f"Found {len(found_rows)} exposures")
    file_prefix = found_rows[0]["fileSetName"]
    data_products = mission.get_unique_product_list(found_rows)
    logging.info(data_products)
    for row in data_products:
        logging.info(row['uri'])
        if row['uri'][-8:] == "cal.fits":
            result = mission.download_file(row['uri'], local_path=data_dir)
            logging.info(result)
    data_path = Path(data_dir)
    data_files = list(data_path.glob(f"{file_prefix}*_cal.fits"))
    logging.info(data_files)
    if len(data_files) > 0:
        return data_files[0]
    return None

def _check_acq_from_jwql(instrument, current_obs):
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    django.setup()
    from jwql.website.apps.jwql.models import RootFileInfo
    logging.info(f"Looking for check image with instrument {instrument} for {current_obs}")
    try:
        obs_path = filesystem_path(f"{current_obs}_uncal.fits")
    except FileNotFoundError as e:
        logging.info(f"Check for exposure {current_obs} not found: {e}")
        return None
    logging.info(f"CHECK: Filesystem path is {obs_path}")
    with fits.open(obs_path) as fits_file:
        program = str(int(fits_file[0].header["PROGRAM"].strip()))
        observation = fits_file[0].header["OBSERVTN"].strip()
        visit = fits_file[0].header["VISIT"].strip()
    logging.info(f"CHECK: Got keywords")
    exp_type = f"{EXP_TYPE_MAPPING[instrument]}TACONFIRM"
    logging.info(f"CHECK: program is {program}")
    logging.info(f"CHECK: exp_type is {exp_type}")
    results = RootFileInfo.objects.filter(proposal=program).filter(exp_type=exp_type)
    logging.info(f"CHECK: results are {results}")
    for result in results:
        result_name = result.root_name
        try:
            result_path = filesystem_path(f"{result_name}_cal.fits")
        except FileNotFoundError as e:
            logging.info(f"Check for exposure {current_obs} not found: {e}")
            return None
        with fits.open(result_path) as fits_file:
            check_program = str(int(fits_file[0].header["PROGRAM"].strip()))
            check_observation = fits_file[0].header["OBSERVTN"].strip()
            check_visit = fits_file[0].header["VISIT"].strip()
        logging.info(f"Checking {result_name}")
        logging.info(f"\tProgram {program} vs {check_program}")
        logging.info(f"\tVisit {visit} vs {check_visit}")
        logging.info(f"\tObservation {observation} vs {check_observation}")
        if check_program == program:
            if check_visit == visit:
                if check_observation == observation:
                    return result_path


class TADataSupplier():
    def __init__(self, instrument, mode=""):
        logging.info(f"Instrument is {instrument}, mode is {mode}")
        self.instrument = instrument.lower()
        self.mode = mode.lower()
        self.data_source = os.environ.get("SHINY_TA_DATA_SOURCE", "astroquery")
        self.current_obs = None
        self.current_visit = None
        self.data_dir = tempfile.mkdtemp()
        self.uncal_path = None
        self.cal_path = None
        self.check_path = None

    def __del__(self):
        if Path(self.data_dir).is_dir():
            shutil.rmtree(self.data_dir)

    def get_obs_list(self):
        if hasattr(self, "_obs_list"):
            return self._obs_list
        if self.data_source == "astroquery":
            self._data_table = _obs_list_from_astroquery(self.instrument, self.mode)
            self._obs_list = self._data_table["fileSetName"].tolist()
        elif self.data_source == "jwql":
            self._obs_list = _obs_list_from_jwql(self.instrument, self.mode)
        return self._obs_list

    def select_obs(self, obs_name):
        if obs_name in self.get_obs_list() and self.current_obs != obs_name:
            self.current_obs = obs_name
            self._uncal_plot = None
            self._cal_plot = None
            self._check_plot = None
            if self.data_source == "astroquery":
                _download_obs_from_astroquery(self._data_table, self.current_obs, self.data_dir)

    def get_obs_uncal(self):
        if self.data_source == "astroquery":
            self.uncal_path = _uncal_acq_from_astroquery(self.data_dir, self.current_obs)
        elif self.data_source == "jwql":
            self.uncal_path = _uncal_acq_from_jwql(self.current_obs)
        return self.uncal_path

    def get_plot_uncal(self, integration, annotate_plot, dq_data, flagged, zoom):
        if self.uncal_path is not None:
            if hasattr(self, "_uncal_plot") and self._uncal_plot is not None:
                return self._uncal_plot.get_plot(
                    integration=integration,
                    plot=annotate_plot,
                    dq_data=dq_data,
                    flagged=flagged,
                    zoom=zoom
                )
            else:
                file_info = filename_parser(self.uncal_path)
                logging.info(file_info)
                visit_id = file_info["program_id"] + file_info["observation"] + file_info["visit"]
                self._uncal_plot = TAPlot(
                    visit_id,
                    self.uncal_path,
                    inst=self.instrument,
                )
                logging.info(f"Created plot {self._uncal_plot}")
                return self._uncal_plot.get_plot(
                    integration=integration,
                    plot=annotate_plot,
                    dq_data=dq_data,
                    flagged=flagged,
                    zoom=zoom
                )
        return None

    def get_obs_cal(self, annotate_plot=True, annotate_text=True):
        if self.data_source == "astroquery":
            self.cal_path = _cal_acq_from_astroquery(self.data_dir, self.current_obs)
        elif self.data_source == "jwql":
            self.cal_path = _cal_acq_from_jwql(self.current_obs)
        return self.cal_path

    def get_plot_cal(self, annotate_plot, zoom):
        if self.cal_path is not None:
            if hasattr(self, "_cal_plot") and self._cal_plot is not None:
                return self._cal_plot.get_plot(
                    plot=annotate_plot,
                    zoom=zoom
                )
            else:
                file_info = filename_parser(self.cal_path)
                logging.info(file_info)
                visit_id = file_info["program_id"] + file_info["observation"] + file_info["visit"]
                self._cal_plot = TAPlot(
                    visit_id,
                    self.cal_path,
                    inst=self.instrument,
                )
                logging.info(f"Created plot {self._cal_plot}")
                return self._cal_plot.get_plot(
                    plot=annotate_plot,
                    zoom=zoom
                )
        return None

    def get_obs_check(self, annotate_plot=True, annotate_text=True):
        if self.data_source == "astroquery":
            self.check_path = _check_acq_from_astroquery(self.instrument, self._data_table, self.data_dir, self.current_obs)
        elif self.data_source == "jwql":
            self.check_path = _check_acq_from_jwql(self.instrument, self.current_obs)
        return self.check_path

    def get_plot_check(self, annotate_plot, zoom):
        if self.check_path is not None:
            if hasattr(self, "_check_plot") and self._check_plot is not None:
                return self._check_plot.get_plot(
                    plot=annotate_plot,
                    zoom=zoom
                )
            else:
                file_info = filename_parser(self.check_path)
                logging.info(file_info)
                visit_id = file_info["program_id"] + file_info["observation"] + file_info["visit"]
                self._check_plot = TAPlot(
                    visit_id,
                    self.check_path,
                    inst=self.instrument,
                    check_image=True
                )
                logging.info(f"Created plot {self._check_plot}")
                return self._check_plot.get_plot(
                    plot=annotate_plot,
                    zoom=zoom
                )
        return None

