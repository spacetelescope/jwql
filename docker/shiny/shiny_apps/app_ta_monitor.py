from shiny import App, reactive, render, ui

import logging

logging.basicConfig(level=logging.INFO)

import matplotlib.pyplot as plt

from astropy.io import fits
from astroquery.mast import MastMissions
import numpy as np
import os
from urllib.parse import parse_qs, urlparse

from support_ta_monitor_data import TADataSupplier

running_standalone = str(os.environ.get("SHINY_EMBED", 0)) == "0"

logging.info(f"SHINY_EMBED={os.environ.get('SHINY_EMBED')}")
logging.info(f"Running Standalone: {running_standalone}")

plt.rcParams["font.weight"] = "bold"
plt.rcParams["axes.labelweight"] = "bold"  # Optional: also bolds axis title

data_source = reactive.value(None)

def build_nav_panel(panel_name, panel_ui):
    return ui.nav_panel(panel_name, panel_ui)

def build_menu_ui(name, ui_list):
    nav_panels = [build_nav_panel(n, u) for n, u in ui_list]
    return ui.nav_menu(name, *nav_panels)

def build_navset_ui(menu_list):
    return ui.navset_tab(*menu_list)


miri_lrs_ui = ui.div(
    ui.h4("MIRI LRS"),
    ui.input_selectize(
        "miri_exposure_select",
        "Select MIRI LRS TA Exposure",
        choices=[],
        selected=None,
        multiple=False,  # Set to True if you want a multi-tag text input
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
            ui.card_header("TA Image (uncalibrated)"),
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_slider(
                        "group_slicer",
                        "Uncal Groups:",
                        min=1,
                        max=1,
                        value=1,
                        step=1,
                    ),
                    ui.input_slider(
                        "integ_slicer",
                        "Uncal Integrations:",
                        min=1,
                        max=1,
                        value=1,
                        step=1,
                    ),
                    open="closed",
                ),
            ),
            ui.output_plot("plot_lrs_uncal_image"),#, width="100%", height="400px"),
            max_height="500px"
        ),
        ui.card(
            ui.card_header("TA Image (calibrated)"),
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_checkbox(
                        "check_lrs_show_calibrated_crosses",
                        "Show TA checks",
                        True
                    ),
                    open="closed",
                ),
            ),
            ui.output_plot("plot_lrs_cal_image"),#, width="100%", height="400px"),
            max_height="500px"
        ),
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("TA Verification Image"),
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_checkbox(
                        "check_lrs_show_verification_crosses",
                        "Show TA checks",
                        True
                    ),
                    open="closed",
                ),
            ),
            ui.output_plot("plot_lrs_verification_image"),#, width="100%", height="400px"),
            max_height="500px"
        ),
        ui.card(
            ui.card_header("OSS Log"),
            ui.output_text("text_lrs_oss_log"),
            max_height="500px",
        ),
    ),
)

miri_mrs_ui = ui.card(
    ui.card_header("MIRI MRS Card")
)

nircam_ui = ui.card(
    ui.card_header("NIRCam Card")
)

niriss_ui = ui.card(
    ui.card_header("NIRISS Card")
)

nirspec_ui = ui.card(
    ui.card_header("NIRSpec Card")
)

instrument_ui = {
    "miri": build_menu_ui("MIRI", [("MIRI LRS", miri_lrs_ui), ("MIRI MRS", miri_mrs_ui)]),
    "nircam": build_menu_ui("NIRCam", [("NIRCam TA Monitor", nircam_ui)]),
    "niriss": build_menu_ui("NIRISS", [("NIRISS TA Monitor", niriss_ui)]),
    "nirspec": build_menu_ui("NIRISS", [("NIRSpec TA Monitor", nirspec_ui)]),
}

app_ui = ui.page_fillable(
    ui.output_ui("dynamic_layout")
)

def server(input, output, session):
    @render.ui
    def dynamic_layout():
        # Note that at some point we will need to update the data supplier based on the
        # currently selected tab
        data_source.set(TADataSupplier("MIRI"))
        ui.update_selectize(
            "miri_exposure_select",
            choices = data_source().obs_list
        )
        if running_standalone:
            return build_navset_ui([instrument_ui[x] for x in sorted(instrument_ui.keys())])
        query_string = session.clientdata.url_search()
        parsed_params = parse_qs(urlparse(query_string).query)
        instrument = parsed_params.get("inst", ["unspecified"])[0]
        if instrument.lower() in instrument_ui.keys():
            return build_navset_ui([instrument_ui[instrument.lower()]])
        else:
            return build_navset_ui([instrument_ui[x] for x in sorted(instrument_ui.keys())])
    @render.plot
    def plot_lrs_uncal_image():
        selected_exposure = input.miri_exposure_select()
        data_source().select_obs(selected_exposure)
        uncal_file = data_source().get_obs_uncal()
        if uncal_file is not None:
            with fits.open(uncal_file) as fits_file:
                uncal_data = fits_file['SCI'].data
            print(uncal_data.shape)
            ui.update_slider("group_slicer", min=1, max=uncal_data.shape[0])
            ui.update_slider("integ_slicer", min=1, max=uncal_data.shape[1])
            selected_data = uncal_data[
                input.group_slicer() - 1, input.integ_slicer() - 1, :, :
            ]
            fig = plt.imshow(selected_data, aspect='auto')
            plt.xlabel("x (pixels)", fontsize=11, fontweight="bold")
            plt.ylabel("y (pixels)", fontsize=11, fontweight="bold")
            cbar = plt.colorbar(fig, orientation="vertical", fraction=0.046, pad=0.04)
            cbar.set_label("Counts", fontsize=11, fontweight="bold")
            return fig
    @render.plot
    def plot_lrs_cal_image():
        selected_exposure = input.miri_exposure_select()
        data_source().select_obs(selected_exposure)
        cal_file = data_source().get_obs_cal()
        if cal_file is not None:
            with fits.open(cal_file) as fits_file:
                cal_data = fits_file['SCI'].data
            fig = plt.imshow(cal_data, aspect='auto')
            plt.xlabel("x (pixels)", fontsize=11, fontweight="bold")
            plt.ylabel("y (pixels)", fontsize=11, fontweight="bold")
            cbar = plt.colorbar(fig, orientation="vertical", fraction=0.046, pad=0.04)
            cbar.set_label("Counts", fontsize=11, fontweight="bold")
            return fig
    @render.plot
    def plot_lrs_verification_image():
        selected_exposure = input.miri_exposure_select()
        data_source().select_obs(selected_exposure)
        cal_file = data_source().get_obs_cal()
        if cal_file is not None:
            with fits.open(cal_file) as fits_file:
                cal_data = fits_file['SCI'].data
            fig = plt.imshow(cal_data, aspect='auto')
            plt.xlabel("x (pixels)", fontsize=11, fontweight="bold")
            plt.ylabel("y (pixels)", fontsize=11, fontweight="bold")
            cbar = plt.colorbar(fig, orientation="vertical", fraction=0.046, pad=0.04)
            cbar.set_label("Counts", fontsize=11, fontweight="bold")
            return fig
    @render.text
    def text_lrs_oss_log():
        query_string = session.clientdata.url_search()
        parsed_params = parse_qs(urlparse(query_string).query)
        instrument = parsed_params.get("inst", ["unspecified"])[0]
        exposure = input.miri_exposure_select()
        scroll_text = f"Getting data for instrument {instrument}.\n"
        scroll_text += f"Selected exposure is {exposure}.\n"
        return scroll_text

app = App(app_ui, server, debug=False)
