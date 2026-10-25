from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from core.config import DATASETS_DIR, TEST_VIDEOS_DIR
from ui.data import run_info


@st.cache_data(ttl=60)
def scan_source_files(
    datasets_dir: Path = DATASETS_DIR,
    test_videos_dir: Path = TEST_VIDEOS_DIR,
) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for collection, root in (
        ("VisDrone datasets", datasets_dir),
        ("Test videos", test_videos_dir),
    ):
        if not root.is_dir():
            continue
        for current_dir, _, file_names in os.walk(root):
            current_path = Path(current_dir)
            for file_name in file_names:
                file_path = current_path / file_name
                stat = file_path.stat()
                files.append(
                    {
                        "collection": collection,
                        "file": file_name,
                        "type": file_path.suffix.lower() or "no extension",
                        "size_mb": round(stat.st_size / (1024 * 1024), 3),
                        "modified": pd.Timestamp(stat.st_mtime, unit="s").strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                        "path": str(file_path.relative_to(root)),
                    }
                )
    return sorted(
        files,
        key=lambda item: (
            str(item["collection"]).casefold(),
            str(item["path"]).casefold(),
        ),
    )


def render_library(run_dirs: list[Path]) -> None:
    st.title("Files & Runs")
    st.caption(
        "Browse source videos, every file in the local VisDrone datasets, "
        "and the artifacts saved for each processed run."
    )
    files_tab, runs_tab = st.tabs(["Source files", "Processed runs"])
    with files_tab:
        _render_files()
    with runs_tab:
        _render_runs(run_dirs)


def _render_files() -> None:
    try:
        files = scan_source_files()
    except OSError as error:
        st.error(f"Could not scan source files: {error}")
        return
    if not files:
        st.info(
            "No files found under datasets or test_videos. Add local source data "
            "to those folders to browse it here."
        )
        return

    frame = pd.DataFrame(files)
    st.caption(
        f"{len(frame):,} files indexed · source file inventory refreshes every 60 seconds"
    )
    search_col, collection_col, type_col = st.columns([2, 1, 1])
    with search_col:
        query = st.text_input(
            "Search files",
            placeholder="Filename or relative path",
            key="library_file_query",
        ).strip().casefold()
    with collection_col:
        collection = st.selectbox(
            "Collection",
            ["All collections", *sorted(frame["collection"].unique())],
            key="library_collection",
        )
    with type_col:
        file_type = st.selectbox(
            "File type",
            ["All types", *sorted(frame["type"].unique())],
            key="library_file_type",
        )

    if collection != "All collections":
        frame = frame.loc[frame["collection"] == collection]
    if file_type != "All types":
        frame = frame.loc[frame["type"] == file_type]
    if query:
        searchable = frame["file"].str.casefold() + " " + frame["path"].str.casefold()
        frame = frame.loc[searchable.str.contains(query, regex=False)]

    st.caption(f"{len(frame):,} matching file(s)")
    page_size = 100
    page_count = max(1, (len(frame) + page_size - 1) // page_size)
    page_state_key = "library_files_page"
    st.session_state.setdefault(page_state_key, 1)
    st.session_state[page_state_key] = min(
        max(1, st.session_state[page_state_key]),
        page_count,
    )
    selected_page = st.number_input(
        "Page",
        min_value=1,
        max_value=page_count,
        step=1,
        key=page_state_key,
    )
    start = (int(selected_page) - 1) * page_size
    st.dataframe(
        frame.iloc[start : start + page_size],
        hide_index=True,
        width="stretch",
    )
    st.caption(f"Page {int(selected_page)} of {page_count} · {page_size} files per page")


def _render_runs(run_dirs: list[Path]) -> None:
    st.caption(f"{len(run_dirs):,} processed run(s) with detections.csv")
    if not run_dirs:
        st.info("No processed runs are indexed yet.")
        return

    for run_dir in run_dirs:
        try:
            info = run_info(run_dir)
            artifacts = sorted(
                path.relative_to(run_dir).as_posix()
                for path in run_dir.rglob("*")
                if path.is_file()
            )
        except (OSError, ValueError, pd.errors.ParserError) as error:
            st.error(f"Could not read run {run_dir.name}: {error}")
            continue

        with st.expander(
            f"{info.video_name} · {run_dir.name} · {info.total_objects} objects"
        ):
            st.write(
                f"Source: `{info.video_name}` · Processed: `{info.processed_at}` · "
                f"Duration: {info.duration_sec:.1f}s"
            )
            st.caption(f"{len(artifacts)} saved artifact(s)")
            if artifacts:
                st.dataframe(
                    pd.DataFrame({"Run file": artifacts}),
                    hide_index=True,
                    width="stretch",
                )
            st.button(
                "Open results",
                key=f"library_open_{run_dir.name}",
                on_click=_select_run,
                args=(run_dir,),
            )


def _select_run(run_path: Path) -> None:
    st.session_state["selected_run_dir"] = str(run_path)
    st.session_state["active_page"] = "Results"
