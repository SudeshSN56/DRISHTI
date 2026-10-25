# DRISHTI — Project Report

## Current status

Report updated: 2026-10-23.

DRISHTI analyzes recorded drone footage locally. Its Python detection pipeline uses Ultralytics YOLO and ByteTrack, stores run evidence in CSV, and provides results, object tracking summaries, annotated video, snapshots, and PDF briefs. The repository now contains both the earlier Streamlit application and a newer FastAPI + React application. The React application talks to the FastAPI backend; the Streamlit source remains in the repository.

The current checkout is on `quality-improvements` at commit `b3a3fe7` (`new system done removed streamlit`). The worktree also contains uncommitted additions for a batch-processing script and a VisDrone run manifest. This report describes the current checkout and local run evidence rather than treating the project as archived.

## Scope and outcome

DRISHTI is designed for local Windows 11 + Python 3.12 work on recorded drone clips. The backend is Python, FastAPI, OpenCV, pandas, and Ultralytics YOLO with ByteTrack. The current web client is React, TypeScript, and Vite; the older Streamlit UI is also still present. The detector reads video from disk, tracks selected classes, and saves per-run outputs.

Key outcomes:
- Streamlit console UI with graphite styling and dark/light themes
- CSV-first Results, Run Explorer, and Object Dossier pages
- Provenance-aware detections CSV for run parameters and legacy compatibility
- Evaluation tool for manual-count comparisons
- Configurable default-preserving detection filters and speed controls
- PDF brief enhancements and improved snapshot handling
- FastAPI endpoints for health, model metadata, detection streaming, files, runs, and PDF briefs
- React console pages for Analyze, Results, Run Explorer, and Object Dossier
- Batch processing of local MP4 clips and recorded VisDrone sequence outcomes

## Repository and branch state

Current branch:
- quality-improvements

Related branch retained:
- ui-redesign

The historical project log lives at:
- docs/archive/gptluna.md

Current local worktree changes:
- `tools/batch_process.py` is added and processes `*.mp4` files from `test_videos/` with the configured default classes. It prints per-clip outcomes and creates a PDF brief after each successful run.
- Run it from the repository root with `python -m tools.batch_process` (or the selected virtual-environment Python executable).
- `outputs/visdrone_batch_manifest_20261023_194944.csv` is an untracked run manifest for 52 VisDrone sequences. It records 51 completed sequences and one interrupted sequence. The completed entries account for 21,748 frames; the manifest assumes 30 FPS.
- The batch script and manifest are separate: the script does not currently write that VisDrone manifest.

## Architecture summary

Top-level structure:
- app.py and ui/ — legacy Streamlit entry point, theme, components, and pages
- api/ — FastAPI application, schemas, and endpoints
- web/ — React + TypeScript frontend and Vite build configuration
- core/ — video source, detector, analysis, report, and config logic
- tools/ — batch processing, evaluation, and frame-to-video utilities
- tests/ — automated verification for app, pipeline, UI, and evaluation tools
- outputs/ — run folders generated locally
- test_videos/ — sample clips used for validation
- datasets/ — local datasets kept out of source control

## Data flow

1. A video is uploaded through the web interface or selected from a local sample.
2. The API validates the request and starts detection; progress and annotated previews are streamed to the web client.
3. The detector runs YOLO + ByteTrack on selected classes.
4. Track state and provenance are written to `detections.csv` as the primary evidence record.
5. Results, run explorer, and object dossier data are derived from saved run CSVs through the API.
6. A PDF brief is generated on request.
7. The Streamlit interface remains as an alternate, legacy entry point in the source tree.

## Output artifacts

Each successful run writes a timestamped folder under outputs/. In the final version, each run may contain:
- detections.csv
- annotated.mp4
- snapshots/
- brief.pdf (generated on request in the UI; the batch script generates it automatically after successful processing)

The CSV is the single source of truth for all numbers, charts, reports, and summaries shown in the app.

## User interfaces

The console interfaces use a graphite aesthetic:
- grayscale chrome
- data-only color highlights for object classes and statuses
- analysis, results, run exploration, and object dossier pages
- compact KPI cards, charts, tables, snapshots, and annotated-video review
- responsive layouts and interactive navigation

The Streamlit application retains its dark/light theme toggle and sidebar navigation. The React application is a separate TypeScript frontend built with Vite and communicates with the FastAPI endpoints.

## API and web application

The FastAPI application is defined in `api/main.py`. Its routes provide:
- health status and model metadata/class/sample-video information
- video detection with server-sent progress and preview events
- run listing, run details, and run deletion
- access to run artifacts and on-demand PDF generation
- serving the built React application from `web/dist/` when that directory exists

The React application currently includes Analyze, Results, Run Explorer, and Object Dossier pages. The web package provides Vite development, production build, preview, and Oxlint commands. For local development, run the API with Uvicorn and run the Vite development server separately. The repository's setup documents should be kept aligned with this newer application path.

## Core capabilities delivered

### Detection and processing
- Upload workflow with validation and corrupt-file handling
- Class selection and default-curated classes
- Progress display, elapsed timer, and warning banner for long videos
- Zero-detection handling
- Annotated preview during processing
- CSV provenance recording for model, confidence, size, track length, device, and processing time
- Compatibility for old CSVs without provenance columns

### Results experience
- KPI strip with counts and timing information
- Summary text from CSV-derived values
- Three SVG charts: class totals, time histogram, stacked class mix
- Additional active-objects timeline chart
- Snapshot gallery with sorting and paging
- Download CSV and print PDF actions

### Run exploration and object review
- Filtering by search, class, object count, date, and sort mode
- Previous-run browsing
- Object dossier with prev/next object selection
- Per-class context in related object cards

### Reporting and quality
- PDF brief with page numbers, legend, and run settings
- Print CSS for browser-side print cleanup
- Snapshot quality controls with padding and minimum size rules
- Configurable defaults that preserve existing behavior unless changed by the user
- Evaluation CLI for comparing app counts to manual counts

## Quality improvements included

The project includes a quality and handover pass that improved the trustworthiness and usability of the app:
- CSV provenance and backward compatibility for legacy folders
- Not-recorded handling for old runs
- explicit run settings in the CSV and results page
- evaluation tool for manual count error measurement
- configurable minimum box filter and per-class confidence overrides
- tracker and inference-width controls with default-safe behavior
- visible-large-video notice and elapsed/processing FPS display
- honest chart labels and better active-object charting
- better snapshot quality, gallery pagination, and placeholder handling
- PDF improvements and print styling
- README quick-start, limitation notes, and dependency pinning
- repository scan for secret and personal-path leakage
- FastAPI routes and request/response schemas for the web application
- React/TypeScript console with API-backed analysis and results pages
- API tests for health, model metadata, sample videos, and run responses
- A local batch-processing script for MP4 clips in `test_videos/`

## Recent VisDrone batch run

The local manifest `outputs/visdrone_batch_manifest_20261023_194944.csv` records 52 input sequences from `VisDrone2019-VID-test-dev` and `VisDrone2019-VID-train`:
- 51 sequences completed, with run folders recorded in `outputs/`
- 1 sequence (`uav0000281_00460_v`) was interrupted and has no run directory in the manifest
- 21,748 frames are recorded for completed sequences
- The conversion/processing manifest uses a 30 FPS assumption; it does not establish the dataset's native frame rate

The manifest is local run evidence, not a ground-truth evaluation. Detection and tracking counts are not formal accuracy measurements.

## Validation summary

Checks performed while updating this report:

| Check | Result |
|---|---|
| FastAPI tests (`python -m unittest tests.test_api -v`) | Passed: 6 tests |
| React production build (`npm run build`) | Passed: TypeScript build and Vite bundle |
| React lint (`npm run lint`) | Completed with 5 warnings in `Dossier.tsx` and `Results.tsx` (hook dependencies, effect state update, and callback initialization) |

Key environment versions at close:
- Streamlit 1.66.0
- Ultralytics 8.4.183
- PyTorch 2.11.0+cu128
- torchvision 0.26.0+cu128
- OpenCV 5.0.0.93
- pandas 3.0.6
- fpdf2 2.8.9
- PyYAML 6.0.3
- Pillow 12.3.0
- Matplotlib 3.11.2

These versions were recorded in the earlier handoff; they were not all re-probed during this report update. The complete Python test suite and live web/API startup were not rerun as part of this update.

## Dependencies and notes

Direct dependencies were pinned in requirements.txt for reproducibility and handover quality. The PyTorch CUDA install instruction remains documented in the README and must be kept for this project.

The repository also retains the Ultralytics AGPL-3.0 and VisDrone usage/terms guidance to keep the project compliant and transparent.

## Known limitations

The project still intentionally reflects these boundaries:
- small or distant objects may be missed
- counts are approximate and should not be presented as accuracy measurements
- tracking can split or merge IDs across frames
- CUDA is required for the current detector flow
- source video retention is not implemented
- no login, maps, DB, or PowerPoint workflows are included

## Final closure note

DRISHTI currently contains a working local detection pipeline, an existing Streamlit UI, and a newer FastAPI + React application. The React production build and focused API tests pass; lint reports five warnings that remain to be addressed. The worktree also includes local batch-processing changes and a manifest showing one interrupted sequence that can be rerun. Project counts remain approximate and should not be presented as accuracy measurements.

This report summarizes the committed project and the local batch-run state as of the update date above.
