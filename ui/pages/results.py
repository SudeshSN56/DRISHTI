from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.analysis import analyze_csv
from core.config import CONFIDENCE_THRESHOLD, IMAGE_SIZE, MIN_TRACK_FRAMES
from core.report import build_brief
from ui.charts import bar_list, histogram, stacked_bar
from ui.components import notice, object_card
from ui.data import ObjectInfo, read_objects


def _time_label(seconds: float) -> str:
    minutes = int(seconds) // 60
    remaining = seconds - minutes * 60
    return f"{minutes:02d}:{remaining:04.1f}"


def render_results(run_dir: Path) -> None:
    csv_path = run_dir / "detections.csv"
    try:
        analysis = analyze_csv(csv_path)
        objects = read_objects(csv_path)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Could not read the results CSV: {error}")
        return

    counts = [
        (str(row["class"]), int(row["count"]))
        for row in analysis.counts.to_dict("records")
    ]
    total_objects = sum(value for _, value in counts)
    common_class = counts[0][0] if counts else "—"
    busiest_label = "—"
    if not analysis.timeline.empty:
        windows = analysis.timeline.groupby(
            ["bucket_start_sec", "bucket_end_sec"],
            as_index=False,
        )["count"].sum()
        if not windows.empty:
            busiest = windows.loc[windows["count"].idxmax()]
            busiest_label = (
                f"{_time_label(float(busiest['bucket_start_sec']))}–"
                f"{_time_label(float(busiest['bucket_end_sec']))}"
            )

    st.header(f"Results: {analysis.video_name}")
    st.caption(f"Run {run_dir.name} · Processed {analysis.processed_at}")
    kpis = st.columns(6)
    metrics = (
        ("UNIQUE OBJECTS", str(total_objects)),
        ("CLASSES", str(len(counts))),
        ("MOST COMMON", common_class),
        ("BUSIEST WINDOW", busiest_label),
        ("VIDEO DURATION", f"{analysis.video_duration_sec:.1f}s"),
        ("PROCESSING SPEED", "Not recorded"),
    )
    for column, (label, value) in zip(kpis, metrics):
        with column:
            st.metric(label, value)

    st.markdown(
        '<div class="console-panel"><div class="console-panel-title">'
        "RUN SUMMARY · COUNTS ARE APPROXIMATE</div></div>",
        unsafe_allow_html=True,
    )
    st.info(analysis.summary)

    if not counts:
        st.markdown(
            notice("No selected objects were detected in this video.", "ok"),
            unsafe_allow_html=True,
        )

    chart_left, chart_right = st.columns([1, 1])
    with chart_left:
        st.markdown('<div class="console-panel-title">OBJECTS BY CLASS</div>', unsafe_allow_html=True)
        st.markdown(bar_list(counts), unsafe_allow_html=True)
    with chart_right:
        st.markdown('<div class="console-panel-title">FIRST-SEEN TIMELINE · 5-SECOND BUCKETS</div>', unsafe_allow_html=True)
        timeline_total = (
            analysis.timeline.groupby(
                ["bucket_start_sec", "bucket_end_sec"],
                as_index=False,
            )["count"].sum()
            if not analysis.timeline.empty
            else pd.DataFrame(columns=["bucket_start_sec", "bucket_end_sec", "count"])
        )
        timeline_buckets = [
            (
                f"{_time_label(float(row['bucket_start_sec']))}–"
                f"{_time_label(float(row['bucket_end_sec']))}",
                int(row["count"]),
            )
            for row in timeline_total.to_dict("records")
        ]
        st.markdown(histogram(timeline_buckets), unsafe_allow_html=True)
    st.markdown('<div class="console-panel-title">CLASS MIX · 100% OF UNIQUE OBJECTS</div>', unsafe_allow_html=True)
    st.markdown(stacked_bar(counts), unsafe_allow_html=True)

    with st.expander("Detection parameters and provenance"):
        provenance = (
            ("Source of truth", "detections.csv"),
            ("Confidence threshold", f"{CONFIDENCE_THRESHOLD:.2f}"),
            ("Image size", f"{IMAGE_SIZE}px"),
            ("Minimum track length", f"{MIN_TRACK_FRAMES} frames"),
            ("Processing speed", "Not recorded in CSV"),
        )
        st.dataframe(
            pd.DataFrame(provenance, columns=("Parameter", "Value")),
            hide_index=True,
            width="stretch",
        )

    annotated_video = run_dir / "annotated.mp4"
    if annotated_video.is_file():
        st.subheader("Annotated video replay")
        st.video(str(annotated_video), format="video/mp4")
    else:
        st.warning("The annotated video is not available in this run folder.")

    st.subheader("Object snapshots")
    if not objects:
        st.caption("No saved objects or snapshots are available for this run.")
    else:
        cards = st.columns(4)
        for index, item in enumerate(objects):
            with cards[index % len(cards)]:
                snapshot_html = ""
                if item.snapshot_path:
                    st.image(str(item.snapshot_path), width="stretch")
                    snapshot_html = ""
                confidence = (
                    f"{item.avg_confidence:.3f}"
                    if item.avg_confidence is not None
                    else "—"
                )
                st.markdown(
                    object_card(
                        item.class_name,
                        item.track_id,
                        _time_label(item.first_seen_sec),
                        confidence,
                        snapshot_html,
                    ),
                    unsafe_allow_html=True,
                )
                st.button(
                    "Open dossier",
                    key=f"dossier_{run_dir.name}_{item.class_name}_{item.track_id}",
                    use_container_width=True,
                    on_click=_open_dossier,
                    args=(item, objects, run_dir),
                )

    actions = st.columns(3)
    with actions[0]:
        st.download_button(
            "Download CSV",
            data=csv_path.read_bytes(),
            file_name=csv_path.name,
            mime="text/csv",
            key=f"download_csv_{run_dir.name}",
            use_container_width=True,
        )
    with actions[1]:
        if st.button("Print Brief", key=f"print_brief_{run_dir.name}", use_container_width=True):
            try:
                brief_path = build_brief(csv_path)
                st.session_state["brief_for_run"] = str(brief_path)
                st.success("PDF brief created from this run's CSV.")
            except (OSError, ValueError, pd.errors.ParserError) as error:
                st.error(f"Could not create the PDF brief: {error}")
    with actions[2]:
        brief_path = run_dir / "brief.pdf"
        if brief_path.is_file() and st.session_state.get("brief_for_run") == str(brief_path):
            st.download_button(
                "Download Brief PDF",
                data=brief_path.read_bytes(),
                file_name=brief_path.name,
                mime="application/pdf",
                key=f"download_brief_{run_dir.name}",
                use_container_width=True,
            )


def _open_dossier(item: ObjectInfo, objects: list[ObjectInfo], run_dir: Path) -> None:
    st.session_state["dossier_run_dir"] = str(run_dir)
    st.session_state["dossier_objects"] = [
        (value.class_name, value.track_id) for value in objects
    ]
    st.session_state["dossier_object_key"] = (item.class_name, item.track_id)
    st.session_state["active_page"] = "Object Dossier"
