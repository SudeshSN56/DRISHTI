import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from ultralytics import YOLO

from core.analysis import AnalysisResult, analyze_csv
from core.config import DEFAULT_CLASSES, MODEL_NAME, OUTPUTS_DIR
from core.detector import run_detection
from core.report import build_brief
from core.video_source import VideoSource, VideoSourceError


@st.cache_data
def get_class_names(model_name: str) -> tuple[str, ...]:
    model = YOLO(model_name)
    names = model.names
    return tuple(sorted(names.values()))


def _available_runs() -> list[Path]:
    return sorted(
        (
            run_dir
            for run_dir in OUTPUTS_DIR.glob("run_*")
            if (run_dir / "detections.csv").is_file()
        ),
        key=lambda run_dir: run_dir.name,
        reverse=True,
    )


def _render_results(run_dir: Path) -> None:
    csv_path = run_dir / "detections.csv"
    try:
        analysis: AnalysisResult = analyze_csv(csv_path)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Could not read the results CSV: {error}")
        return

    st.header(f"Results: {analysis.video_name}")
    st.caption(
        f"Duration: {analysis.video_duration_sec:.1f} seconds · "
        f"Processed: {analysis.processed_at}"
    )
    st.info(analysis.summary)

    if analysis.counts.empty:
        st.success("No selected objects were detected in this video.")
    else:
        st.subheader("Unique tracked objects by class")
        st.dataframe(analysis.counts, hide_index=True, width="stretch")
        st.bar_chart(analysis.counts.set_index("class"))

        st.subheader("First-seen timeline")
        timeline_chart = analysis.timeline.pivot(
            index="bucket_start_sec",
            columns="class",
            values="count",
        )
        timeline_chart.index = [
            f"{int(start // 60)}:{int(start % 60):02d}"
            for start in timeline_chart.index
        ]
        st.line_chart(timeline_chart)
        st.dataframe(analysis.timeline, hide_index=True, width="stretch")

    st.download_button(
        "Download CSV",
        data=csv_path.read_bytes(),
        file_name=csv_path.name,
        mime="text/csv",
        key=f"download_csv_{run_dir.name}",
    )
    if st.button("Print Brief", key=f"print_brief_{run_dir.name}"):
        try:
            brief_path = build_brief(csv_path)
            st.session_state["brief_for_run"] = str(brief_path)
            st.success("PDF brief created from this run's CSV.")
        except (OSError, ValueError, pd.errors.ParserError) as error:
            st.error(f"Could not create the PDF brief: {error}")

    brief_path = run_dir / "brief.pdf"
    if (
        st.session_state.get("brief_for_run") == str(brief_path)
        and brief_path.is_file()
    ):
        st.download_button(
            "Download Brief PDF",
            data=brief_path.read_bytes(),
            file_name=brief_path.name,
            mime="application/pdf",
            key=f"download_brief_{run_dir.name}",
        )

    annotated_video = run_dir / "annotated.mp4"
    if annotated_video.is_file():
        st.subheader("Annotated video")
        st.video(str(annotated_video), format="video/mp4")
    else:
        st.warning("The annotated video is not available in this run folder.")

    snapshots_dir = run_dir / "snapshots"
    snapshots = sorted(snapshots_dir.glob("*.jpg")) if snapshots_dir.is_dir() else []
    if snapshots:
        st.subheader("Object snapshots")
        snapshot_columns = st.columns(4)
        for index, snapshot_path in enumerate(snapshots):
            snapshot_columns[index % len(snapshot_columns)].image(
                str(snapshot_path),
                caption=snapshot_path.stem.replace("_", " "),
                width="stretch",
            )


def main() -> None:
    st.set_page_config(page_title="Drone Surveillance Report", layout="wide")
    st.title("Drone Surveillance Report System")
    st.write(
        "Upload a recorded drone video to detect and track selected object classes. "
        "Analysis and reports are based on the generated CSV."
    )

    try:
        class_names = get_class_names(MODEL_NAME)
    except (OSError, RuntimeError, ValueError) as error:
        st.error(f"Could not load the YOLO model class list: {error}")
        return

    defaults = [name for name in DEFAULT_CLASSES if name in class_names]
    uploaded_video = st.file_uploader(
        "Upload a recorded video",
        type=("mp4", "avi", "mov"),
        help="Supported formats: MP4, AVI, and MOV. Videos longer than five minutes can still run.",
    )
    selected_classes = st.multiselect(
        "Object classes to detect",
        options=class_names,
        default=defaults,
        help="The curated classes are selected by default; add or remove any model class.",
    )
    run_clicked = st.button(
        "Run",
        type="primary",
        disabled=uploaded_video is None,
    )

    if run_clicked:
        if uploaded_video is None:
            st.error("Upload a video before starting detection.")
        elif not selected_classes:
            st.error("Select at least one object class before starting detection.")
        else:
            progress_bar = st.progress(0, text="Preparing video...")
            status = st.empty()
            preview_column, counts_column = st.columns([3, 1])
            preview_placeholder = preview_column.empty()
            counts_placeholder = counts_column.empty()
            preview_column.caption("Live annotated preview")
            counts_column.caption("Live tracks (minimum length applied)")

            try:
                with tempfile.TemporaryDirectory() as temporary_directory:
                    temporary_path = (
                        Path(temporary_directory) / Path(uploaded_video.name).name
                    )
                    temporary_path.write_bytes(uploaded_video.getvalue())
                    with VideoSource(temporary_path) as source:
                        if source.metadata.duration_sec > 5 * 60:
                            st.warning(
                                "This video is longer than five minutes. Processing will continue."
                            )

                    def update_progress(processed: int, total: int) -> None:
                        progress_bar.progress(
                            min(processed / total, 1.0),
                            text=f"Processing frame {processed:,} of {total:,}",
                        )

                    def update_preview(
                        frame_rgb: np.ndarray,
                        live_counts: dict[str, int],
                    ) -> None:
                        preview_placeholder.image(frame_rgb, channels="RGB")
                        counts_placeholder.dataframe(
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

                    run_dir = run_detection(
                        temporary_path,
                        selected_classes,
                        progress_callback=update_progress,
                        preview_callback=update_preview,
                    )

                st.session_state["selected_run_dir"] = str(run_dir)
                progress_bar.progress(1.0, text="Processing complete.")
                status.success("Video processing completed.")
            except (VideoSourceError, ValueError, RuntimeError, OSError) as error:
                progress_bar.empty()
                status.error(f"Could not process this video: {error}")

    available_runs = _available_runs()
    selected_run = st.session_state.get("selected_run_dir")
    if selected_run and Path(selected_run) not in available_runs:
        st.session_state.pop("selected_run_dir")
        selected_run = None

    if available_runs:
        run_options = {run_dir.name: run_dir for run_dir in available_runs}
        selected_label = next(
            (
                label for label, run_dir in run_options.items()
                if str(run_dir) == selected_run
            ),
            next(iter(run_options)),
        )
        selected_label = st.selectbox(
            "View a previous run",
            options=list(run_options),
            index=list(run_options).index(selected_label),
        )
        _render_results(run_options[selected_label])


if __name__ == "__main__":
    main()
