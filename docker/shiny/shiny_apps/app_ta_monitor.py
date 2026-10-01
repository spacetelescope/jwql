from shiny import App, module, reactive, render, ui
from shiny.types import SilentException

from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)

import matplotlib.pyplot as plt

from asgiref.sync import sync_to_async
from astropy.io import fits
from astroquery.mast import MastMissions
import numpy as np
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from support_ta_monitor_data import TADataSupplier
from support_ta_monitor_logs import get_ictm_event_log
from support_ta_monitor_logs import extract_oss_event_msgs_for_visit
from support_ta_monitor_logs import check_log_and_note_issues
from support_ta_monitor_plots import TAPlot

running_standalone = str(os.environ.get("SHINY_EMBED", 0)) == "0"

logging.info(f"SHINY_EMBED={os.environ.get('SHINY_EMBED')}")
logging.info(f"Running Standalone: {running_standalone}")

plt.rcParams["font.weight"] = "bold"
plt.rcParams["axes.labelweight"] = "bold"  # Optional: also bolds axis title

CANONICAL_NAMES = {
    "miri": "MIRI",
    "nircam": "NIRCam",
    "niriss": "NIRISS",
    "nirspec": "NIRSpec"
}

data_source = reactive.value(None)
figure_source = reactive.value(None)
current_instrument = reactive.value("")
current_mode = reactive.value("")
uncal_image = reactive.value("")
cal_image = reactive.value("")
check_image = reactive.value("")
user_connected = reactive.value(False)

def build_nav_panel(panel_name, panel_ui):
    return ui.nav_panel(panel_name, panel_ui)

def build_menu_ui(name, ui_list):
    nav_panels = [build_nav_panel(n, u) for n, u in ui_list]
    return ui.nav_menu(name, *nav_panels)

def build_navset_ui(menu_list, id="toplevel"):
    return ui.navset_tab(*menu_list, id=id)

def show_loading_dialog(message):
    return ui.modal(
        ui.div(
            # Spinner animation and centered layout
            ui.div(
                class_="spinner-border text-primary m-3", 
                role="status", 
                style="width: 3rem; height: 3rem;"
            ),
            ui.h4(f"{message}", class_="mt-2"),
            class_="d-flex flex-column align-items-center justify-content-center text-center"
        ),
        title=None,          # Removes standard header line
        footer=None,         # Removes footer completely
        easy_close=False,    # Blocks users from clicking out of the modal
        size="s"             # Compact modal size
    )


@module.ui
def miri_tab_ui():
    miri_ui = ui.div(
        ui.input_selectize(
            "exposure_select",
            "Select Exposure",
            choices=[],
            selected=None,
            multiple=False,  # Set to True if you want a multi-tag text input
            width="500px",
            options={
                "placeholder": "Enter FileSetName",
                "create": True,  # Allows typing custom values not in the list
                "persist": False,  # User-created choices don't permanently alter the original list
                "openOnFocus": True,  # Opens dropdown immediately when clicked
                "allowEmptyOption": True,
            },
        ),
        ui.layout_columns(
            ui.card(
                ui.output_ui("miri_uncal"),
                ui.div(
                    ui.input_action_button(
                        "prev_integ",
                        "◀️",
                        style="padding: 0; height: auto; min-width: 0; line-height: normal; border: none; background: transparent;",
                    ),
                    ui.input_slider(
                        "integ_slicer",
                        "Integration:",
                        min=1,
                        max=1,
                        value=1,
                        step=1,
                    ),
                    ui.input_action_button(
                        "next_integ",
                        "▶️",
                        style="padding: 0; height: auto; min-width: 0; line-height: normal; border: none; background: transparent;",
                    ),
                    class_="d-flex justify-content-center align-items-center gap-3 mb-3",
                ),
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.input_checkbox(
                            "uncal_plot",
                            "Show Annotations",
                            True
                        ),
                        ui.input_checkbox(
                            "uncal_flagged",
                            "Show Flagged Pixels",
                            False
                        ),
                        ui.input_checkbox(
                            "uncal_zoom",
                            "Zoom Image",
                            True
                        ),
                        open="closed",
                    ),
                ),
                ui.output_plot("plot_miri_uncal_image"),#, width="100%", height="400px"),
                max_height="500px",
                full_screen=True
            ),
            ui.card(
                ui.output_ui("miri_cal"),
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.input_checkbox(
                            "cal_plot",
                            "Show Annotations",
                            True
                        ),
                        ui.input_checkbox(
                            "cal_zoom",
                            "Zoom Image",
                            True
                        ),
                        open="closed",
                    ),
                ),
                ui.output_plot("plot_miri_cal_image"),#, width="100%", height="400px"),
                max_height="500px",
                full_screen=True
            ),
        ),
        ui.layout_columns(
            ui.card(
                ui.output_ui("miri_check"),
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.input_checkbox(
                            "check_plot",
                            "Show Annotations",
                            True
                        ),
                        ui.input_checkbox(
                            "check_zoom",
                            "Zoom Image",
                            True
                        ),
                        open="closed",
                    ),
                ),
                ui.output_plot("plot_miri_verification_image"),#, width="100%", height="400px"),
                max_height="500px",
                full_screen=True
            ),
            ui.card(
                ui.card_header("OSS Log"),
                ui.output_ui("oss_warnings"),
                ui.div(
                    ui.output_code("text_miri_oss_log"),
                    style="font-size: 12px;"
                ),
                max_height="500px",
                full_screen=True
            ),
        ),
    )
    return miri_ui

@module.server
def miri_tab_server(input, output, session):
    oss_messages = reactive.value([])
    dq_data = reactive.value(None)
    current_integrations = reactive.value(1)
    current_exposure = reactive.value("")

    @reactive.effect
    async def _():
        """Reactive effect for user selecting an exposure"""
        nonlocal current_exposure
        logging.info("exposure_select")
        new_exposure = input.exposure_select()
        logging.info(f"Selected exposure is {new_exposure}")
        selected_exposure = current_exposure()
        logging.info(f"Existing selection is {selected_exposure}")
        logging.info(f"{new_exposure} == {selected_exposure}: {new_exposure == selected_exposure}")
        if new_exposure != selected_exposure:
            logging.info(f"Changed selected exposure from {selected_exposure}->{new_exposure}")
            await sync_to_async(data_source().select_obs)(new_exposure)
            current_exposure.set(new_exposure)

    @reactive.effect
    @reactive.event(input.prev_integ)
    def _():
        """Reactive effect for user clicking the "previous integration" button"""
        logging.info("previous_integration_button_start")
        if input.integ_slicer() > 1:
            ui.update_slider("integ_slicer", value=(input.integ_slicer() - 1))
        logging.info("previous_integration_button_end")

    @reactive.effect
    @reactive.event(input.next_integ)
    def _():
        """Reactive effect for user clicking the "next integration" button"""
        nonlocal current_integrations
        logging.info("next_integration_button_start")
        if input.integ_slicer() < current_integrations():
            ui.update_slider("integ_slicer", value=(input.integ_slicer() + 1))
        logging.info("next_integration_button_end")

    @render.ui
    async def miri_uncal():
        """Set the card title to the name of the uncalibrated image"""
        logging.info("miri_uncal_name")
        uncal_obs = await sync_to_async(data_source().get_obs_uncal)()
        if uncal_obs is None or uncal_obs == "":
            return ""
        return ui.card_header(f"TA Image (uncalibrated) {Path(uncal_obs).stem}"),

    @render.plot
    async def plot_miri_uncal_image():
        """Plot the MIRI uncalibrated frame"""
        logging.info("plot_miri_uncal_start")
        selected_exposure = current_exposure()
        acq_integ = input.integ_slicer() - 1
        show_plot = input.uncal_plot()
        zoom_plot = input.uncal_zoom()
        dq_frame = dq_data()
        show_flagged = input.uncal_flagged()
        uncal_obs = await sync_to_async(data_source().get_obs_uncal)()
        fig = None
        if uncal_obs is not None:
            with fits.open(uncal_obs) as fits_file:
                n_integrations = fits_file['SCI'].data.shape[1]
                current_integrations.set(n_integrations)
                slider_value = min(input.integ_slicer(), current_integrations())
                ui.update_slider(
                    "integ_slicer",
                    min=1,
                    max=current_integrations(),
                    value=slider_value
                )
            fig = data_source().get_plot_uncal(
                acq_integ,
                show_plot,
                dq_frame,
                show_flagged,
                zoom_plot
            )
        if fig is None:
            fig = plt.figure()
            fig.text(0.5, 0.5, 'No File Available', fontsize=18, ha='center', va='center')
        logging.info("plot_miri_uncal_end")
        return fig
    @render.ui
    def miri_cal():
        logging.info("miri_cal_name")
        return ui.card_header(f"TA Image (calibrated) {cal_image()}"),
    @render.plot
    async def plot_miri_cal_image():
        logging.info("plot_miri_cal_start")
        selected_exposure = current_exposure()
        show_plot = input.cal_plot()
        zoom_plot = input.cal_zoom()
        cal_file = await sync_to_async(data_source().get_obs_cal)()
        if cal_file is not None:
            with fits.open(cal_file) as fits_file:
                dq_data.set(fits_file['DQ'].data)
            fig = data_source().get_plot_cal(show_plot, zoom_plot)
        else:
            fig = plt.figure()
            fig.text(0.5, 0.5, 'No File Available', fontsize=18, ha='center', va='center')
        logging.info("plot_miri_cal_end")
        return fig
    @render.ui
    def miri_check():
        logging.info("miri_check_name")
        return ui.card_header(f"TA Image (check) {check_image()}"),
    @render.plot
    async def plot_miri_verification_image():
        logging.info("plot_miri_check_start")
        selected_exposure = current_exposure()
        show_plot = input.check_plot()
        zoom_plot = input.check_zoom()
        check_file = await sync_to_async(data_source().get_obs_check)()
        if check_file is not None:
            fig = data_source().get_plot_check(show_plot, zoom_plot)
        else:
            fig = plt.figure()
            fig.text(0.5, 0.5, 'No File Available', fontsize=18, ha='center', va='center')
        logging.info("plot_miri_check_end")
        return fig
    @render.text
    def text_miri_oss_log():
        logging.info("miri_oss_log_start")
        nonlocal oss_messages
        selected_exposure = current_exposure()
        uncal_file = data_source().get_obs_uncal()
        if uncal_file is not None:
            oss_messages.set([])
            with fits.open(uncal_file) as fits_file:
                uncal_hdr = fits_file[0].header

            # Take an hour off of time to capture 
            startdate = datetime.fromisoformat(uncal_hdr["DATE-BEG"]) - timedelta(days=1)
            enddate = datetime.fromisoformat(uncal_hdr["DATE-END"])
            visit_id = uncal_hdr["VISIT_ID"]

            eventlog = get_ictm_event_log(
                        mast_api_token=None,
                        verbose=False,
                        startdate=startdate,
                        enddate=enddate,
                    )

            msgs = extract_oss_event_msgs_for_visit(eventlog, visit_id)
            all_warnings = []
            for i, message in enumerate(msgs):
                warning = check_log_and_note_issues(message)
                if warning is not None:
                    logging.info(f"Got OSS warning: {warning}")
                    all_warnings.append(f"Line {i+1}: {warning}")
            if len(all_warnings) > 0:
                oss_messages.set(all_warnings)
            logging.info("miri_oss_log_end")
            return "\n".join(msgs)
        logging.info("miri_oss_log_end")
        return ""
    @render.ui
    def oss_warnings():
        nonlocal oss_messages
        if len(oss_messages()) > 0:
            message_text = []
            for message in oss_messages():
                message_text.append(ui.tags.div(f"Warning: {message}"))
            return ui.tags.div(
                *message_text,
                class_="alert alert-warning",
                role="alert"
            )
        return None

miri_ui = {
    "initial": "lrs",
    "panels": [
        build_nav_panel("LRS", miri_tab_ui("miri_lrs")),
        build_nav_panel("MRS", miri_tab_ui("miri_mrs"))
    ]
}

nircam_tab_ui = ui.card(
    ui.card_header("NIRCam Card")
)

nircam_ui = {
    "initial": "nircam",
    "panels": [
        build_nav_panel("NIRCam", nircam_tab_ui)
    ]
}

niriss_tab_ui = ui.card(
    ui.card_header("NIRISS Card")
)

niriss_ui = {
    "initial": "niriss",
    "panels": [
        build_nav_panel("NIRISS", niriss_tab_ui)
    ]
}

nirspec_tab_ui = ui.card(
    ui.card_header("NIRSpec Card")
)

nirspec_ui = {
    "initial": "nirspec",
    "panels": [
        build_nav_panel("NIRSpec", nirspec_tab_ui)
    ]
}


instrument_ui = {
    "miri": miri_ui,
    "nircam": nircam_ui,
    "niriss": niriss_ui,
    "nirspec": nirspec_ui,
}

app_ui = ui.page_navbar(
    title=ui.output_ui("dynamic_title"),
    id="nav_toplevel",
    fillable=True
)

def server(input, output, session):
    tab_setup = False

    miri_tab_server("miri_lrs")

    miri_tab_server("miri_mrs")

    @render.ui
    def dynamic_title():
        logging.info("dynamic_title_start")
        selected_instrument = current_instrument()
        if selected_instrument in CANONICAL_NAMES:
            display_name = CANONICAL_NAMES[selected_instrument]
            logging.info(f"Updating navbar title to {display_name}")
            return ui.span(display_name, class_="navbar-brand")
        logging.info("dynamic_title_end")
        return ui.span("", class_="navbar-brand")

    def set_exposure_options(instrument, mode, options):
        logging.info("Setting exposure option list")
        selectize_id = f"{instrument}_{mode}-exposure_select"
        ui.update_selectize(
            selectize_id,
            choices=options,
            selected=options[0],
        )
        logging.info("set_exposure_options_end")

    @reactive.effect
    @reactive.event(input.nav_toplevel)
    async def _():
        logging.info("nav_toplevel_start")
        mode = input.nav_toplevel()
        instrument = current_instrument()
        if instrument is not None and mode is not None:
            ui.modal_show(show_loading_dialog(f"Loading {mode} Exposure List"))
            mode = mode.lower()
            logging.info(f"nav_toplevel: Instrument and mode are {instrument}, {mode}")
            if data_source() is None or data_source().instrument != instrument or data_source().mode != mode:
                logging.info(f"nav_toplevel: Creating data source for {instrument} {mode}")
                data_source.set(TADataSupplier(instrument, mode))
            obs_data = data_source()
            obs_list = await sync_to_async(data_source().get_obs_list)()
            obs_list = [""] + obs_list
            set_exposure_options(instrument, mode, obs_list)
            ui.modal_remove()
        logging.info("nav_toplevel_end")

    @reactive.effect
    def _():
        nonlocal tab_setup
        logging.info("tab_setup_start")
        if not tab_setup:
            query_string = session.clientdata.url_search()
            parsed_params = parse_qs(urlparse(query_string).query)
            if "inst" in parsed_params:
                instrument = parsed_params["inst"][0].lower()
                logging.info(f"Got instrument {instrument}")
                if instrument in CANONICAL_NAMES:
                    for panel in instrument_ui[instrument]["panels"]:
                        ui.insert_nav_panel(
                            id="nav_toplevel",
                            nav_panel=panel,
                            select=False
                        )
                    ui.update_navset("nav_toplevel", selected=instrument_ui[instrument]["initial"])
                    current_instrument.set(instrument)
                    tab_setup = True
                    return
            # Currently, just make MIRI either way.
            instrument = "miri"
            ui.update_page_title(f"{CANONICAL_NAMES[instrument]}")
            current_instrument.set(instrument)
            for panel in instrument_ui[instrument]["panels"]:
                ui.insert_nav_panel(
                    id="nav_toplevel",
                    nav_panel=panel,
                    select=False
                )
            ui.update_navset("nav_toplevel", selected=instrument_ui[instrument]["initial"])
            logging.info("tab_setup_end")
            tab_setup = True

app = App(app_ui, server, debug=False)
