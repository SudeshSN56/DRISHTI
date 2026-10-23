from __future__ import annotations

from pathlib import Path

import streamlit as st
import torch
from ultralytics import YOLO

from core.config import DEFAULT_CLASSES, MODEL_NAME, OUTPUTS_DIR, PROJECT_ROOT
from ui.components import render_sidebar, render_topbar
from ui.data import available_runs
from ui.pages.analyze import render_analyze
from ui.pages.dossier import render_dossier
from ui.pages.explorer import render_explorer
from ui.pages.results import render_results
from ui.theme import inject_theme


@st.cache_data
def get_class_names(model_name: str) -> tuple[str, ...]:
    model = YOLO(model_name)
    return tuple(sorted(model.names.values()))


def _device_label() -> str:
    if torch.cuda.is_available():
        return f"CUDA / {torch.cuda.get_device_name(0)}"
    return "CPU"


def main() -> None:
    st.set_page_config(
        page_title="DRISHTI · Command & Intelligence Console",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    light_theme = st.session_state.get("light_theme", False)
    inject_theme("light" if light_theme else "dark")

    run_dirs = available_runs(OUTPUTS_DIR)
    try:
        class_names = get_class_names(MODEL_NAME)
        model_error = None
    except (OSError, RuntimeError, ValueError) as error:
        class_names = tuple(DEFAULT_CLASSES)
        model_error = error

    active_page = render_sidebar(
        class_names,
        ("Analyze", "Results", "Run Explorer", "Object Dossier"),
    )
    topbar_column, theme_column = st.columns([8, 1])
    topbar_placeholder = topbar_column.empty()
    device_label = _device_label()
    model_ready = (PROJECT_ROOT / MODEL_NAME).is_file()

    def update_topbar(status: str | None = None) -> None:
        current_status = status or st.session_state.get("run_status", "idle")
        topbar_placeholder.markdown(
            render_topbar(
                current_status,
                device_label,
                model_ready,
                len(available_runs(OUTPUTS_DIR)),
            ),
            unsafe_allow_html=True,
        )

    update_topbar()
    with theme_column:
        st.toggle("Light theme", key="light_theme", help="Switch between graphite dark and light chrome.")

    if model_error is not None:
        st.error(f"Could not load the YOLO model class list: {model_error}")

    selected_run_value = st.session_state.get("selected_run_dir")
    if selected_run_value and not Path(selected_run_value).is_dir():
        st.session_state.pop("selected_run_dir")
        selected_run_value = None
    selected_run = Path(selected_run_value) if selected_run_value else None

    if active_page == "Analyze":
        if model_error is None:
            render_analyze(class_names, render_results, update_topbar)
    elif active_page == "Results":
        if not run_dirs:
            st.info("No indexed runs yet. Analyze a video to create a results CSV.")
        else:
            labels = [run_dir.name for run_dir in run_dirs]
            initial = (
                selected_run.name
                if selected_run in run_dirs
                else labels[0]
            )
            selected_label = st.selectbox(
                "Selected run",
                labels,
                index=labels.index(initial),
                key="results_run_picker",
            )
            selected_run = next(run for run in run_dirs if run.name == selected_label)
            st.session_state["selected_run_dir"] = str(selected_run)
            render_results(selected_run)
    elif active_page == "Run Explorer":
        render_explorer(run_dirs)
    else:
        render_dossier(selected_run)


if __name__ == "__main__":
    main()
