from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.analysis import analyze_csv
from ui.components import badge
from ui.data import ObjectInfo, read_objects


def render_dossier(selected_run: Path | None) -> None:
    st.title("Object Dossier")
    run_value = st.session_state.get("dossier_run_dir")
    run_dir = Path(run_value) if run_value else selected_run
    if run_dir is None or not (run_dir / "detections.csv").is_file():
        st.info("Open an object snapshot from Results to inspect its dossier.")
        return
    csv_path = run_dir / "detections.csv"
    try:
        objects = read_objects(csv_path)
        analysis = analyze_csv(csv_path)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Could not read the object dossier CSV: {error}")
        return
    if not objects:
        st.info("This run contains no tracked objects.")
        return

    requested = st.session_state.get("dossier_object_key")
    order = st.session_state.get("dossier_objects")
    if not order:
        order = [(item.class_name, item.track_id) for item in objects]
    objects_by_key = {
        (item.class_name, item.track_id): item
        for item in objects
    }
    ordered_objects = [
        objects_by_key[key]
        for key in order
        if key in objects_by_key
    ]
    seen = {(item.class_name, item.track_id) for item in ordered_objects}
    ordered_objects.extend(
        item
        for item in objects
        if (item.class_name, item.track_id) not in seen
    )
    indexed = {
        (item.class_name, item.track_id): index
        for index, item in enumerate(ordered_objects)
    }
    if requested not in indexed:
        requested = (
            (ordered_objects[0].class_name, ordered_objects[0].track_id)
            if ordered_objects
            else next(iter(indexed))
        )
    object_index = indexed[requested]
    current = ordered_objects[object_index]

    controls = st.columns([1, 5, 1])
    with controls[0]:
        st.button(
            "Prev",
            disabled=object_index == 0,
            key="dossier_prev",
            on_click=_select_object,
            args=(ordered_objects[max(0, object_index - 1)], run_dir, order),
        )
    with controls[1]:
        st.caption(
            f"OBJECT {object_index + 1} / {len(ordered_objects)} · "
            f"RUN {run_dir.name}"
        )
    with controls[2]:
        st.button(
            "Next",
            disabled=object_index == len(ordered_objects) - 1,
            key="dossier_next",
            on_click=_select_object,
            args=(
                ordered_objects[min(len(ordered_objects) - 1, object_index + 1)],
                run_dir,
                order,
            ),
        )

    image_column, detail_column = st.columns([1.25, 1])
    with image_column:
        if current.snapshot_path:
            st.image(str(current.snapshot_path), width="stretch")
        else:
            st.markdown(
                '<div class="console-panel" style="height:280px;display:grid;place-items:center">'
                "Snapshot unavailable</div>",
                unsafe_allow_html=True,
            )
    with detail_column:
        st.markdown(
            f'<h2>{badge(current.class_name, current.class_name)}</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="console-value" style="font-size:1.4rem">TRACK ID {current.track_id}</div>',
            unsafe_allow_html=True,
        )
        total = int(analysis.counts["count"].sum()) if not analysis.counts.empty else 0
        share = 100 / total if total else 0
        confidence = (
            f"{current.avg_confidence:.3f}"
            if current.avg_confidence is not None
            else "Not recorded"
        )
        details = (
            ("FIRST SEEN", _time_label(current.first_seen_sec)),
            ("LAST SEEN", _time_label(current.last_seen_sec)),
            ("DURATION VISIBLE", f"{current.last_seen_sec - current.first_seen_sec:.2f}s"),
            ("AVERAGE CONFIDENCE", confidence),
            ("SHARE OF RUN", f"{share:.1f}%"),
        )
        st.dataframe(
            pd.DataFrame(details, columns=("Measure", "Value")),
            hide_index=True,
            width="stretch",
        )

    same_class = [
        item for item in objects
        if item.class_name == current.class_name and item.track_id != current.track_id
    ]
    st.subheader(f"Other {current.class_name} objects")
    if not same_class:
        st.caption("No other tracked objects of this class.")
    else:
        columns = st.columns(min(5, len(same_class)))
        for index, item in enumerate(same_class[:10]):
            with columns[index % len(columns)]:
                if item.snapshot_path:
                    st.image(str(item.snapshot_path), width="stretch")
                else:
                    st.markdown(
                        '<div class="console-panel" style="height:100px;display:grid;'
                        'place-items:center;color:var(--muted)">Snapshot unavailable</div>',
                        unsafe_allow_html=True,
                    )
                st.caption(f"{current.class_name} · ID {item.track_id} · {_time_label(item.first_seen_sec)}")
                st.button(
                    "Open",
                    key=f"same_class_{item.class_name}_{item.track_id}",
                    on_click=_select_object,
                    args=(item, run_dir, order),
                )


def _select_object(
    item: ObjectInfo,
    run_dir: Path,
    order: list[tuple[str, str]],
) -> None:
    st.session_state["dossier_run_dir"] = str(run_dir)
    st.session_state["dossier_object_key"] = (item.class_name, item.track_id)
    st.session_state["dossier_objects"] = order


def _time_label(seconds: float) -> str:
    minutes = int(seconds) // 60
    remaining = seconds - minutes * 60
    return f"{minutes:02d}:{remaining:04.1f}"
