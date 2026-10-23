from __future__ import annotations

import hashlib
import html
from datetime import datetime, timezone
from typing import Iterable

import streamlit as st


CLASS_COLORS = {
    "person": "#fab219",
    "car": "#6b9bea",
    "truck": "#ec835a",
    "bus": "#d03b3b",
    "bicycle": "#3fb26b",
    "motorcycle": "#b07be0",
    "boat": "#4cc3d9",
    "bird": "#c8d96b",
    "dog": "#e08fb4",
    "cat": "#e0b48f",
    "horse": "#8f9be0",
    "cow": "#9bc48f",
    "sheep": "#c4c4c4",
}


def class_color(class_name: str) -> str:
    known = CLASS_COLORS.get(class_name.casefold())
    if known:
        return known
    digest = hashlib.sha256(class_name.casefold().encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    return f"hsl({hue} 58% 62%)"


def swatch(class_name: str, *, compact: bool = False) -> str:
    safe_name = html.escape(class_name)
    color = class_color(class_name)
    width = "8px" if compact else "9px"
    return (
        f'<span class="class-swatch" style="background:{color};width:{width}" '
        f'aria-hidden="true"></span><span class="class-label">{safe_name}</span>'
    )


def badge(label: str, class_name: str | None = None) -> str:
    safe = html.escape(label)
    prefix = swatch(class_name, compact=True) if class_name else ""
    text = (
        ""
        if class_name and class_name.casefold() == label.casefold()
        else safe
    )
    return f'<span class="console-badge">{prefix}{text}</span>'


def panel(title: str, content: str) -> str:
    return (
        '<section class="console-panel">'
        f'<div class="console-panel-title">{html.escape(title)}</div>{content}</section>'
    )


def stat(label: str, value: str, detail: str = "") -> str:
    return (
        '<div class="console-panel">'
        f'<div class="console-panel-title">{html.escape(label)}</div>'
        f'<div class="console-value" style="font-size:1.12rem">{html.escape(value)}</div>'
        f'<div style="color:var(--muted);font-size:.72rem">{html.escape(detail)}</div>'
        "</div>"
    )


def notice(message: str, severity: str = "info") -> str:
    category = "warn" if severity in {"warning", "warn"} else severity
    return f'<div class="console-notice {html.escape(category)}">{html.escape(message)}</div>'


def object_card(
    class_name: str,
    track_id: str,
    first_seen: str,
    confidence: str,
    snapshot_html: str = "",
) -> str:
    safe_track = html.escape(track_id)
    return (
        f'<div class="object-card" style="border-left:2px solid {class_color(class_name)}">'
        f'{snapshot_html}<div>{swatch(class_name)} <span class="console-badge">ID {safe_track}</span></div>'
        f'<div class="object-meta">FIRST SEEN {html.escape(first_seen)}<br>'
        f'AVG CONFIDENCE {html.escape(confidence)}</div></div>'
    )


def render_topbar(
    run_status: str,
    device_label: str,
    model_ready: bool,
    run_count: int,
) -> str:
    status = run_status if run_status in {"idle", "processing", "done"} else "idle"
    status_text = {"idle": "IDLE", "processing": "PROCESSING", "done": "DONE"}[status]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    topbar = (
        '<div class="console-topbar">'
        '<div><div class="console-brand">DRISHTI</div>'
        '<div class="console-subtitle">COMMAND &amp; INTELLIGENCE CONSOLE</div></div>'
        f'<div class="console-item"><span class="status-dot {status}"></span>RUN '
        f'<span class="console-value">{status_text}</span></div>'
        f'<div class="console-item">DEVICE <span class="console-value">{html.escape(device_label)}</span></div>'
        f'<div class="console-item">MODEL <span class="console-value">{"READY" if model_ready else "MISSING"}</span></div>'
        f'<div class="console-item">INDEXED <span class="console-value">{run_count}</span></div>'
        f'<div class="console-item"><span class="console-value">{timestamp}</span> UTC</div>'
        "</div>"
    )
    return topbar


def render_sidebar(
    class_names: Iterable[str],
    page_options: tuple[str, ...],
) -> str:
    st.sidebar.markdown(
        '<div class="console-brand" style="font-size:1.05rem">DRISHTI</div>'
        '<div class="console-subtitle">AERIAL VIDEO INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )
    page = st.sidebar.radio(
        "Navigation",
        page_options,
        key="active_page",
        label_visibility="collapsed",
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<div class="console-panel-title">CLASS LEGEND</div>',
        unsafe_allow_html=True,
    )
    legend = sorted(set(class_names), key=str.casefold)
    st.sidebar.markdown(
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:7px 10px'>"
        + "".join(f"<div>{swatch(name)}</div>" for name in legend)
        + "</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Annotated video boxes are labelled with class and track ID.")
    return page
