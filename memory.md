# Shared Multi-Agent Memory (`memory.md`)

> **Protocol for AI Agents (GPT Luna, Cline, Antigravity):**
> 1. **At Session Start / Chat Reset:** Always read this file (`memory.md`) first to restore context.
> 2. **During Tasks:** Keep track of in-progress operations, decisions, and file edits.
> 3. **At Turn/Task Completion:** Update the "Agent Activity Log" and "Current Focus & Next Steps" sections below so the other agents know what was done, what is in progress, and what remains.

---

## 1. Project Overview & Architecture

- **Project Name:** DRISHTI — Drone Surveillance Report System
- **Target OS & Environment:** Windows 11, Python 3.12 (in `.\venv`)
- **Compute Platform:** NVIDIA GeForce RTX 4060 Laptop GPU (CUDA 12.8, PyTorch CUDA build verified)
- **Primary AI/ML Pipeline:**
  - **Detection & Tracking:** Ultralytics YOLO11s (`yolo11s.pt`) + ByteTrack (`lap`) via `core/detector.py`
  - **Class Filter:** Curated COCO classes (`person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck`, `boat`) or user-selected classes
  - **Analysis Engine:** CSV-first architecture (`core/analysis.py`), deriving track counts, first-seen/visible-object 5-second timelines, and text summary from `detections.csv`
  - **Frontend UI:** Streamlit app (`app.py`), featuring file upload, live annotated frame preview, live track counts, results visualization, annotated video player, snapshot gallery, and run history navigation
  - **Reporting:** fpdf2 PDF brief generation (`core/report.py`), created on demand via the "Print Brief" button
  - **Utilities:** Frame stitcher `tools/frames_to_video.py` converts sequential dataset JPGs into H.264 MP4 clips

---

## 2. Workspace File Map & Roles

| Path | Purpose / Description |
|---|---|
| `app.py` | Streamlit web frontend; handles file uploads, live inference preview callback, charts, run history, and PDF download |
| `core/detector.py` | Core video processing pipeline using CUDA YOLO + ByteTrack, snapshots generation, and CSV logging |
| `core/analysis.py` | Independent CSV analyzer; generates unique counts, timelines, and template summary without needing video files |
| `core/report.py` | PDF brief compiler using fpdf2; triggered only on user action ("Print Brief") |
| `core/video_source.py` | OpenCV video reader/context manager with metadata validation and error handling |
| `core/config.py` | Central configuration (confidence thresholds, image dimensions, track lengths, output directories) |
| `tools/frames_to_video.py` | CLI tool to stitch sequence frame folders (e.g., VisDrone) into H.264 MP4 videos |
| `tests/` | Automated test suite (currently 31 app, pipeline, evaluation, and UI tests) |
| `test_videos/` | Local test clips (git-ignored, contains stitched VisDrone clips: `uav0000137_00458_v.mp4`, `uav0000305_00000_v.mp4`, `uav0000339_00001_v.mp4`) |
| `datasets/` | Ignored dataset storage (`VisDrone2019-VID-val`) |
| `outputs/` | Timestamped run directories (`run_*`), each containing `detections.csv`, `annotated.mp4`, `snapshots/`, and optional `brief.pdf` |
| `PLAN.md` | Product scope and phase-by-phase implementation specifications (Phases 0–6) |
| `docs/archive/gptluna.md` | Historical progress and validation log from earlier GPT Luna sessions |
| `memory.md` | **Active shared multi-agent memory file (this file)** |

---

## 3. Project Status & Completed Milestones

- [x] **Phase 0 — Setup:** Python 3.12 venv, CUDA 12.8 PyTorch, requirements installed, RTX 4060 GPU verified.
- [x] **Phase 0.5 — Demo Data:** VisDrone-VID validation archive acquired, frames converter built, 3 H.264 MP4 clips generated in `test_videos/`.
- [x] **Phase 1 — Video Detection:** YOLO11s + ByteTrack inference pipeline operational with live frame preview callback and confidence snapshot exports.
- [x] **Phase 2 — CSV Analysis:** `analyze_csv` fully functional, handles normal and `__none__` zero-detection outputs.
- [x] **Phase 3 — UI:** Streamlit frontend built and tested; features live preview, counts, plots, downloads, and historical run browsing.
- [x] **Phase 4 — Print Brief:** PDF brief generator built; compiles statistics, summary, and detection crops into a single document.
- [x] **Phase 5 — Automated Tests:** 31 automated tests passing (`tests/test_*.py`).
- [x] **Phase 6 — Demo & Clean-start verification:** Full rehearsal verified; server run and stop tested.

---

## 4. Agent Collaboration & Activity Log

### Agent: GPT Luna
- **Completed:**
  - Initial scaffolding, core architecture (`detector`, `analysis`, `report`, `video_source`).
  - Added `tools/frames_to_video.py` and stitched 3 VisDrone sequences into `test_videos/`.
  - Added live preview callback to `core/detector.py` and connected it to `app.py`.
  - Authored `PLAN.md` and the now-archived `docs/archive/gptluna.md`.
- **Status:** Handed off.

### Agent: Antigravity (Google DeepMind)
- **Completed:**
  - Verified environment, CUDA PyTorch configuration, and model assets on the RTX 4060 Laptop GPU.
  - Successfully migrated frontend from Streamlit to modern **FastAPI REST Backend + Vite + React 19 + TypeScript**:
    - Created `api/` package with `main.py`, `schemas.py`, routes for `meta`, `runs`, `files`, `report`, and streaming `detect` (SSE with real-time base64 preview frames and progress).
    - Scaffolded and built modern military-grade web console in `web/` with React Router 7, Lucide icons, responsive layout, dark graphite theme, SVG metrics & histograms, annotated video player, and object dossiers.
    - Verified production build (`npm run build` completed in 786ms to `web/dist/`).
    - Added automated API test suite `tests/test_api.py` (all 6 tests pass).
    - Core pipeline tests pass (all 20 unit tests pass).
    - FastAPI mounts and serves `web/dist/` statically on port 8000 for zero-config single-port hosting.
  - **Storage Optimization & Dataset Curation:**
    - Evaluated and ranked all 80 VisDrone sequences across train, val, and test-dev based on target density, track counts, class diversity, and length.
    - Curated and stitched the **top 25 best surveillance videos** into compact H.264 MP4 clips in `test_videos/` (total 346 MB).
    - Removed non-top videos and deleted the 223 MB root demo recording (`Recording 2026-10-23 183709.mp4`).
    - Deleted the entire raw uncompressed `datasets/` folder (~11.24 GB) while retaining `.gitkeep`, freeing massive disk space.
    - Restarted FastAPI + React web console and verified that all 25 curated videos appear in the Analyze dropdown.
- **Status:** Active / Top 25 Curated Videos Stitched in test_videos; Raw Datasets Cleaned Up; Server Live on Port 8000.

### Agent: Cline
- **Completed:**
  - Resumed session from shared memory (`memory.md` / `memmory.md`).
  - Verified project state via file inspection: phases 0–6 complete, 9 tests defined in `tests/test_pipeline.py`, Streamlit app (`app.py`), detector/analysis/report modules intact.
  - Reviewed core modules (`core/detector.py`, `core/analysis.py`, `core/report.py`, `core/config.py`) and test suite to restore full context.
- **In Progress / Blockers:**
  - Terminal/shell integration is unresponsive in this session (commands hang, including `pytest` and `git`), so live test execution and GitHub CLI publishing could not be run from Cline.
  - GitHub remote publishing (`gh auth login` → create private repo → `git push main`) remains pending and requires a working terminal or an authenticated GitHub connection.
- **Status:** Active / Awaiting terminal recovery or user direction.


---

## 5. Current Focus & Immediate Next Steps

- Current work branch: `quality-improvements`; `ui-redesign` remains the stable
  UI checkpoint.
- Provenance, configurable filter defaults, manual-count evaluation, opt-in
  inference resizing/FP16, CSV-derived visible-object charts, snapshot options,
  and PDF settings/legend/page numbering have been implemented and committed
  in small steps. The 2688 × 1512 single-run comparison is recorded in
  `PLAN.md` and `README.md`; inference resizing stays disabled because counts
  differed.
- Latest full test run: 31 passing. PDF text/layout was inspected for one
  class, twelve classes, and zero detections.
- Streamlit health endpoint returned HTTP 200, and AppTest rendered the real
  Results run with 252 unique tracks and 9.20 FPS.
- A fresh real-clip CSV and four-page PDF were written under ignored `outputs/`;
  PDF text confirmed model, settings, legend, and page number.
- Handover check is complete; leave the branch local unless the user requests
  a push.
