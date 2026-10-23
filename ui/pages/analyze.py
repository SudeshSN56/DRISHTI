from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import streamlit as st
import torch

from core.config import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_CLASSES,
    IMAGE_SIZE,
    MIN_TRACK_FRAMES,
    MODEL_NAME,
)
from core import detector
from core.video_source import VideoSource, VideoSourceError
from ui.components import notice, panel, swatch


def render_analyze(
    class_names: tuple[str, ...],
    render_results: Callable[[Path], None],
    update_topbar: Callable[[str], None],
) -> None:
    st.title("Analyze")
    st.caption("Configure a recorded video run. Results are indexed from its detections.csv.")
    upload_column, settings_column = st.columns([1.3, 1])

    with upload_column:
        uploaded_video = st.file_uploader(
            "Upload a recorded video",
            type=("mp4", "avi", "mov"),
            help="MP4, AVI, MOV. Videos longer than five minutes can still run.",
            key="video_upload",
        )
        if uploaded_video is not None:
            st.markdown(
                panel(
                    "Selected source",
                    f'<span class="console-value">{uploaded_video.name}</span>',
                ),
                unsafe_allow_html=True,
            )
        defaults = [name for name in DEFAULT_CLASSES if name in class_names]
        selected_classes = st.multiselect(
            "Object classes",
            options=class_names,
            default=defaults,
            help="Curated classes are selected by default. All model classes remain available.",
            key="selected_classes",
        )
        st.markdown(
            "<div style='display:flex;flex-wrap:wrap;gap:6px 14px;margin:4px 0 14px'>"
            + "".join(f"<span>{swatch(name)}</span>" for name in selected_classes)
            + "</div>",
            unsafe_allow_html=True,
        )

    with settings_column:
        parameter_rows = (
            ("CONFIDENCE", f"{CONFIDENCE_THRESHOLD:.2f}"),
            ("IMAGE SIZE", f"{IMAGE_SIZE}px"),
            ("MIN TRACK LENGTH", f"{MIN_TRACK_FRAMES} frames"),
            ("INFERENCE DEVICE", "CUDA" if torch.cuda.is_available() else "CPU"),
        )
        parameter_html = "".join(
            f'<div style="display:flex;justify-content:space-between;gap:12px;'
            f'padding:9px 0;border-bottom:1px solid var(--line)">'
            f'<span style="color:var(--muted);font-size:.72rem">{label}</span>'
            f'<span class="console-value">{value}</span></div>'
            for label, value in parameter_rows
        )
        st.markdown(
            panel("Detection parameters · read-only", parameter_html),
            unsafe_allow_html=True,
        )
        st.caption("Track counters and saved crops include tracks meeting the minimum length.")

    run_clicked = st.button(
        "Run",
        type="primary",
        disabled=uploaded_video is None,
        key="run_detection",
    )
    if run_clicked:
        if uploaded_video is None:
            st.error("Upload a video before starting detection.")
        elif not selected_classes:
            st.error("Select at least one object class before starting detection.")
        else:
            started = time.perf_counter()
            st.session_state["run_status"] = "processing"
            st.session_state["live_preview"] = None
            st.session_state["live_counts"] = {}
            update_topbar("processing")
            progress = st.progress(0, text="Preparing video · 0.0s elapsed")
            live_frame, live_table = st.columns([3, 1])
            frame_slot = live_frame.empty()
            counts_slot = live_table.empty()
            live_frame.caption("LIVE ANNOTATED PREVIEW")
            live_table.caption("LIVE TRACK COUNTS")
            try:
                with tempfile.TemporaryDirectory() as temporary_directory:
                    temporary_path = Path(temporary_directory) / Path(uploaded_video.name).name
                    temporary_path.write_bytes(uploaded_video.getvalue())
                    with VideoSource(temporary_path) as source:
                        if source.metadata.duration_sec > 5 * 60:
                            st.markdown(
                                notice(
                                    "This video is longer than five minutes. Processing will continue.",
                                    "warning",
                                ),
                                unsafe_allow_html=True,
                            )

                    def update_progress(processed: int, total: int) -> None:
                        elapsed = time.perf_counter() - started
                        fraction = min(processed / total, 1.0) if total else 0.0
                        progress.progress(
                            fraction,
                            text=(
                                f"Processing frame {processed:,} of {total:,} "
                                f"· {elapsed:.1f}s elapsed"
                            ),
                        )

                    def update_preview(
                        frame_rgb: np.ndarray,
                        live_counts: dict[str, int],
                    ) -> None:
                        st.session_state["live_preview"] = frame_rgb
                        st.session_state["live_counts"] = dict(live_counts)
                        frame_slot.image(frame_rgb, channels="RGB", width="stretch")
                        counts_slot.dataframe(
                            pd.DataFrame(
                                [
                                    {
                                        "class": class_name,
                                        "tracks": live_counts.get(class_name, 0),
                                    }
                                    for class_name in selected_classes
                                ]
                            ),
                            hide_index=True,
                            width="stretch",
                        )

                    run_dir = detector.run_detection(
                        temporary_path,
                        selected_classes,
                        progress_callback=update_progress,
                        preview_callback=update_preview,
                    )
                st.session_state["selected_run_dir"] = str(run_dir)
                st.session_state["run_status"] = "done"
                progress.progress(
                    1.0,
                    text=f"Processing complete · {time.perf_counter() - started:.1f}s elapsed",
                )
                st.success("Video processing completed.")
                update_topbar("done")
            except (VideoSourceError, ValueError, RuntimeError, OSError) as error:
                st.session_state["run_status"] = "idle"
                progress.empty()
                update_topbar("idle")
                st.error(f"Could not process this video: {error}")

    preview = st.session_state.get("live_preview")
    live_counts = st.session_state.get("live_counts", {})
    if preview is not None:
        preview_column, count_column = st.columns([3, 1])
        with preview_column:
            st.caption("LATEST ANNOTATED FRAME")
            st.image(preview, channels="RGB", width="stretch")
        with count_column:
            st.caption("LIVE TRACK COUNTS · MINIMUM LENGTH APPLIED")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"class": name, "tracks": live_counts.get(name, 0)}
                        for name in (st.session_state.get("selected_classes") or [])
                    ]
                ),
                hide_index=True,
                width="stretch",
            )

    selected_run = st.session_state.get("selected_run_dir")
    if selected_run and (Path(selected_run) / "detections.csv").is_file():
        render_results(Path(selected_run))
