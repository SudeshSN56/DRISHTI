from __future__ import annotations

from datetime import date
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from ui.components import badge, panel
from ui.data import DatasetVideo, RunInfo, available_dataset_videos, filter_runs, run_info


def render_explorer(run_dirs: list[Path]) -> None:
    st.title("Run Explorer")
    st.caption(
        "Browse processed runs and source sequences. VisDrone source folders contain "
        "numbered image frames, not pre-built video files."
    )
    query_column, collection_column, class_column, count_column = st.columns([2, 1, 1, 1])
    with query_column:
        query = st.text_input(
            "City / video / sequence",
            placeholder="Search demo city or source name",
        )
    all_dataset_videos = available_dataset_videos()
    dataset_names = sorted(
        {video.dataset_name for video in all_dataset_videos},
        key=str.casefold,
    )
    with collection_column:
        selected_dataset = st.selectbox("Dataset", ["All datasets", *dataset_names])
    all_runs: list[RunInfo] = []
    for run_dir in run_dirs:
        try:
            all_runs.append(run_info(run_dir))
        except (OSError, ValueError, pd.errors.ParserError) as error:
            st.error(f"Could not index {run_dir.name}: {error}")
    all_classes = sorted(
        {name for run in all_runs for name in run.class_names},
        key=str.casefold,
    )
    with class_column:
        selected_class = st.selectbox("Class", ["All classes", *all_classes])
    with count_column:
        min_objects = st.number_input("Minimum objects", min_value=0, value=0, step=1)

    date_column, sort_column = st.columns([2, 1])
    with date_column:
        after_text, before_text = st.columns(2)
        with after_text:
            after_value = st.text_input("From date · YYYY-MM-DD", placeholder="Any date")
        with before_text:
            before_value = st.text_input("To date · YYYY-MM-DD", placeholder="Any date")
    with sort_column:
        sort_by = st.selectbox("Sort by", ["newest", "most objects", "longest video"])

    query_value = query.strip().casefold()
    filtered_dataset_videos = [
        video
        for video in all_dataset_videos
        if (selected_dataset == "All datasets" or video.dataset_name == selected_dataset)
        and (
            not query_value
            or query_value in video.name.casefold()
            or query_value in video.dataset_name.casefold()
            or query_value in video.demo_city.casefold()
        )
    ]
    st.subheader(f"VisDrone source sequences · {len(filtered_dataset_videos)} matching")
    st.caption(
        "All source sequences are listed here. They contain numbered JPG frames, "
        "not processed detection runs. City names are dummy demo labels, not "
        "geographic metadata."
    )
    for video in filtered_dataset_videos:
        _render_dataset_video_card(video)

    try:
        after = date.fromisoformat(after_value.strip()) if after_value.strip() else None
        before = date.fromisoformat(before_value.strip()) if before_value.strip() else None
    except ValueError:
        st.error("Dates must use YYYY-MM-DD.")
        return
    if after and before and after > before:
        st.error("From date must be on or before To date.")
        return
    filtered = filter_runs(
        all_runs,
        video_query=query,
        class_name="" if selected_class == "All classes" else selected_class,
        min_objects=int(min_objects),
        after=after,
        before=before,
        sort_by=sort_by,
    )
    st.subheader(f"Processed runs · {len(filtered)} matching")
    limit_key = "explorer_limit"
    if limit_key not in st.session_state:
        st.session_state[limit_key] = 24
    for run in filtered[: st.session_state[limit_key]]:
        _render_run_card(run)
    if len(filtered) > st.session_state[limit_key]:
        if st.button("Load more", key="load_more_runs"):
            st.session_state[limit_key] += 24
            st.rerun()

    if not run_dirs and not all_dataset_videos:
        st.info("No indexed runs or VisDrone source sequences found.")


def _render_run_card(run: RunInfo) -> None:
    class_chips = " ".join(badge(name, name) for name in run.class_names)
    city_label = f"<span class='badge'>{run.location or 'Demo city'}</span>" if run.location else ""
    st.markdown(
        panel(
            run.video_name,
            f'<div class="object-meta">{city_label} RUN {run.path.name} · {run.processed_at} · '
            f'{run.duration_sec:.1f}s · {run.total_objects} OBJECTS</div>'
            f'<div style="margin-top:8px">{class_chips or "No detections"}</div>',
        ),
        unsafe_allow_html=True,
    )
    st.button(
        "Open results",
        key=f"open_run_{run.path.name}",
        on_click=_select_run,
        args=(run.path,),
    )


def _render_dataset_video_card(video: DatasetVideo) -> None:
    title = f"{video.demo_city} · {video.name}"
    content = (
        f'<div class="object-meta">{html.escape(video.dataset_name)} · '
        f'{video.frame_count:,} JPG FRAMES · SOURCE SEQUENCE</div>'
        '<div class="object-meta">Demo location · not recorded dataset metadata</div>'
    )
    st.markdown(panel(title, content), unsafe_allow_html=True)


def _select_run(run_path: Path) -> None:
    st.session_state["selected_run_dir"] = str(run_path)
    st.session_state["active_page"] = "Results"
    st.session_state["explorer_limit"] = 24
