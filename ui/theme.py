from __future__ import annotations

import streamlit as st


DARK_TOKENS = {
    "bg": "#111214",
    "bg-2": "#0c0d0f",
    "panel": "#17181b",
    "panel-2": "#1e2023",
    "panel-3": "#26282c",
    "line": "#26282c",
    "line-2": "#34363b",
    "line-3": "#45484e",
    "text": "#ececee",
    "text-2": "#b5b7bd",
    "muted": "#8b8e96",
    "accent": "#ececee",
    "accent-ink": "#111214",
    "ok": "#3fb26b",
    "warn": "#d9a23a",
    "crit": "#e05252",
    "inc": "#6b9bea",
    "dec": "#e06c6c",
}

LIGHT_TOKENS = {
    **DARK_TOKENS,
    "bg": "#f5f5f6",
    "bg-2": "#ffffff",
    "panel": "#ffffff",
    "panel-2": "#f1f1f2",
    "panel-3": "#e6e6e8",
    "line": "#e2e2e5",
    "line-2": "#cdced2",
    "line-3": "#b4b6bb",
    "text": "#17181a",
    "text-2": "#40424a",
    "muted": "#686b73",
    "accent": "#17181a",
    "accent-ink": "#ffffff",
    "inc": "#2f66c8",
    "dec": "#c0392f",
}


def _variables(tokens: dict[str, str]) -> str:
    return "\n".join(f"  --{name}:{value};" for name, value in tokens.items())


def inject_theme(theme: str) -> None:
    tokens = LIGHT_TOKENS if theme == "light" else DARK_TOKENS
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root {{
{_variables(DARK_TOKENS)}
  color-scheme: dark;
}}
:root[data-theme="light"] {{
{_variables(LIGHT_TOKENS)}
  color-scheme: light;
}}
:root {{
{_variables(tokens)}
  color-scheme: {"light" if theme == "light" else "dark"};
  font-synthesis: none;
}}
html, body, [data-testid="stAppViewContainer"] {{
  background:var(--bg) !important;
  color:var(--text);
  font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
}}
[data-testid="stHeader"], footer {{ visibility:hidden; height:0; }}
[data-testid="stSidebar"] {{
  background:var(--bg-2);
  border-right:1px solid var(--line);
}}
[data-testid="stSidebar"] > div:first-child {{ padding-top:1rem; }}
.block-container {{ padding-top:1.1rem; max-width:1600px; }}
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] {{
  color:var(--text-2);
}}
h1, h2, h3, h4 {{ color:var(--text) !important; letter-spacing:-.025em; }}
p, label, [data-testid="stWidgetLabel"] {{ color:var(--text-2) !important; }}
code, pre, [data-testid="stMetricValue"], .mono {{
  font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Consolas,monospace !important;
  font-variant-numeric:tabular-nums;
}}
[data-testid="stMetric"] {{
  background:var(--panel); border:1px solid var(--line); padding:14px 16px;
}}
[data-testid="stAlert"] {{
  background:var(--panel) !important; border:1px solid var(--line-2) !important;
  color:var(--text-2) !important;
}}
[data-testid="stMetricLabel"] {{ color:var(--muted) !important; font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }}
[data-testid="stMetricValue"] {{ color:var(--text) !important; font-size:1.35rem; }}
div.stButton > button, [data-testid="stDownloadButton"] button {{
  color:var(--text); background:var(--panel-2); border:1px solid var(--line-2);
  border-radius:3px; transition:transform 150ms ease,background 150ms ease;
}}
div.stButton > button:hover, [data-testid="stDownloadButton"] button:hover {{
  color:var(--text); border-color:var(--line-3); background:var(--panel-3);
}}
div.stButton > button:active, [data-testid="stDownloadButton"] button:active {{
  transform:translateY(1px);
}}
div.stButton > button:focus-visible, button:focus-visible, input:focus-visible,
[data-baseweb="select"]:focus-within {{
  outline:2px solid var(--accent) !important; outline-offset:2px;
}}
[data-baseweb="input"], [data-baseweb="select"] > div, [data-testid="stDateInput"] input {{
  background:var(--panel-2); border-color:var(--line-2); color:var(--text);
}}
[data-testid="stFileUploader"] section {{
  background:var(--panel); border:1px dashed var(--line-3); border-radius:3px;
}}
[data-testid="stFileUploader"] button {{ border-radius:3px; }}
[data-testid="stProgressBar"] > div > div {{ background:var(--text-2); }}
[data-testid="stTabs"] button {{ color:var(--text-2); }}
[data-testid="stTabs"] button[aria-selected="true"] {{
  color:var(--text); border-bottom-color:var(--accent);
}}
[data-testid="stExpander"] {{
  border:1px solid var(--line); background:var(--panel); border-radius:3px;
}}
[role="radiogroup"] label {{ color:var(--text-2) !important; }}
input[type="radio"], input[type="checkbox"] {{ accent-color:var(--accent); }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  border:1px solid var(--line); background:var(--panel);
}}
.console-topbar {{
  display:flex; align-items:center; gap:18px; flex-wrap:wrap;
  padding:12px 16px; margin-bottom:18px; background:var(--panel);
  border:1px solid var(--line); border-radius:3px;
}}
.console-brand {{ color:var(--text); font-weight:700; letter-spacing:.08em; }}
.console-subtitle {{ color:var(--muted); font-size:.76rem; }}
.console-item {{ display:flex; align-items:center; gap:7px; color:var(--text-2); font-size:.76rem; }}
.console-value {{ color:var(--text); font-family:"IBM Plex Mono",monospace; font-size:.74rem; }}
.status-dot {{ width:7px; height:7px; border-radius:50%; display:inline-block; background:var(--muted); }}
.status-dot.processing {{ background:var(--warn); }}
.status-dot.done {{ background:var(--ok); }}
.console-panel {{
  padding:16px; background:var(--panel); border:1px solid var(--line);
  border-radius:3px; margin:0 0 14px;
}}
.console-panel-title {{ color:var(--muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.1em; margin-bottom:9px; }}
.class-swatch {{ display:inline-block; width:8px; height:8px; margin-right:7px; vertical-align:middle; border-radius:1px; }}
.class-label {{ color:var(--text-2); font-size:.8rem; }}
.console-badge {{
  display:inline-block; padding:3px 7px; border:1px solid var(--line-2);
  border-radius:2px; color:var(--text-2); font:500 .68rem "IBM Plex Mono",monospace;
}}
.console-notice {{ padding:11px 14px; margin:10px 0; border:1px solid var(--line-2); border-left:3px solid var(--muted); background:var(--panel); color:var(--text-2); }}
.console-notice.warn {{ border-left-color:var(--warn); }}
.console-notice.error {{ border-left-color:var(--crit); }}
.console-notice.ok {{ border-left-color:var(--ok); }}
.object-card {{ padding:10px; border:1px solid var(--line); background:var(--panel); border-radius:3px; }}
.object-card:hover {{ border-color:var(--line-3); }}
.object-meta {{ color:var(--muted); font: .72rem "IBM Plex Mono",monospace; line-height:1.8; }}
@media print {{
  [data-testid="stSidebar"], [data-testid="stHeader"], footer,
  .console-topbar, .no-print, button, [data-testid="stDownloadButton"] {{ display:none !important; }}
  html, body, [data-testid="stAppViewContainer"] {{ background:#fff !important; color:#111 !important; }}
  .block-container {{ max-width:none !important; padding:0 !important; }}
  .console-panel {{ break-inside:avoid; border-color:#bbb !important; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration:.01ms !important; transition-duration:.01ms !important; scroll-behavior:auto !important; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )
