# DRISHTI — Drone Surveillance Report System

## 1. Executive summary

DRISHTI is a local video-analysis application for recorded aerial footage. It
uses an Ultralytics YOLO model with ByteTrack to detect and track selected
objects, then writes a CSV, an annotated video, and best-confidence object
snapshots for each run. A Streamlit interface provides live processing
feedback, CSV-derived analysis, run browsing, object dossiers, downloads, and
an on-demand PDF brief.

The project is designed for local use on Windows 11 with Python 3.12 and a
CUDA-capable NVIDIA GPU. The detection pipeline currently requires CUDA; CPU
inference is not supported by `core.detector.run_detection`.

## 2. Project goals and boundaries

### Included

- Upload and analyze recorded MP4, AVI, or MOV video.
- Select model classes; start with a curated COCO-oriented class selection.
- Track detections over time and discard tracks shorter than the configured
  minimum.
- Provide progress, an annotated live preview, and qualified live track counts.
- Save per-run CSV output, annotated H.264 video, and object snapshots.
- Derive counts, five-second timeline data, summaries, charts, and run filters
  from each run's `detections.csv`.
- Browse and filter past runs and inspect a tracked object in a dossier.
- Build a PDF report only after the user clicks **Print Brief**.
- Support dark and light graphite UI themes.

### Explicitly out of scope

Login, roles, user management, databases, maps/GPS, live drone input, cloud
processing, model training, thermal/night processing, PowerPoint, batch
queues, source-video retention, and natural-language queries are not part of
the current implementation.

## 3. Technology and configuration

| Area | Implementation |
|---|---|
| Language/runtime | Python 3.12; project targets Windows 11 |
| Web UI | Streamlit (installed environment was checked at version 1.66.0) |
| Detection | Ultralytics YOLO, default model file `yolo11s.pt` |
| Tracking | ByteTrack |
| Video input/output | OpenCV for reading; imageio-ffmpeg/FFmpeg for H.264 output |
| Data processing | pandas, Python CSV |
| PDF | fpdf2 and Matplotlib (Matplotlib is used for PDF charts, not UI charts) |
| UI charts | Hand-written responsive SVG strings; no UI chart dependency |
| Tests | `unittest`, Streamlit `AppTest`, synthetic OpenCV video |

Runtime dependencies are listed in [requirements.txt](requirements.txt):
`ultralytics`, `lap`, `opencv-python`, `numpy`, `pandas`, `matplotlib`,
`streamlit`, `fpdf2`, and `imageio-ffmpeg`. PyTorch must be installed
separately with a CUDA-compatible build; the README setup example uses the
CUDA 12.8 wheel index. The redesign added no runtime dependencies.

Central detection settings in [core/config.py](core/config.py):

| Setting | Value |
|---|---:|
| Model | `yolo11s.pt` |
| Confidence threshold | `0.35` |
| Image size | `960` |
| Minimum track length | `5` frames |
| Analysis timeline buckets | `5` seconds |
| Curated default classes | person, bicycle, car, motorcycle, bus, truck, boat, bird, dog, cat, horse, cow, sheep |

The detector selects the CUDA device explicitly (`device=0`) and raises a
clear runtime error when CUDA is unavailable.

## 4. Architecture and repository map

```text
app.py
├── ui/theme.py              CSS variables, dark/light theme and print rules
├── ui/components.py         Sidebar, class colors, reusable HTML components
├── ui/charts.py             Pure SVG chart builders
├── ui/data.py               CSV-backed run/object records and run filtering
└── ui/pages/
    ├── analyze.py           Upload, classes, parameters, progress and preview
    ├── results.py           CSV analysis, SVGs, replay, snapshots and actions
    ├── explorer.py          Search/filter/sort of indexed runs
    └── dossier.py           Per-track view and Prev/Next navigation

core/
├── config.py                Project paths and detector settings
├── video_source.py          OpenCV video validation and frame reading
├── detector.py              YOLO/ByteTrack pipeline and output generation
├── analysis.py              CSV validation, unique counts, timeline, summary
└── report.py                On-demand PDF brief generation

tools/frames_to_video.py     JPG-sequence to H.264 video utility
tests/                       App, pipeline and UI helper tests
outputs/                     Local run folders (generated; ignored by Git)
test_videos/                 Local sample clips (ignored by Git)
datasets/                    Local datasets (ignored by Git)
```

Other project documentation includes [README.md](README.md),
[PLAN.md](PLAN.md), and the historical [gptluna.md](gptluna.md).

## 5. Processing and data flow

1. Streamlit loads the model's available class names and presents the Analyze
   page. A user uploads a recorded clip, chooses classes, and starts a run.
2. The uploaded bytes are written to a temporary file. `VideoSource` validates
   that the file exists, opens successfully, has usable FPS/frame count/
   dimensions, and contains a readable frame.
3. `run_detection` applies YOLO tracking with ByteTrack, the selected classes,
   confidence `0.35`, image size `960`, and CUDA device 0. It tracks detections
   frame-by-frame and writes an annotated H.264 video.
4. Every three frames and on the final frame, the detector can send a
   downscaled annotated RGB preview and counts for tracks that have met the
   five-frame minimum. A progress callback reports completed frames.
5. For each track, the pipeline records first/last seen times, confidence
   observations, and the crop from its highest-confidence detection. Tracks
   shorter than five frames are removed from saved snapshots and CSV output.
6. The completed run is saved in a timestamped `outputs/run_*` directory. The
   CSV is the authoritative source for analysis. Results are reloaded from the
   CSV rather than reconstructed from display-only state.
7. `analyze_csv` validates run metadata and derives unique class counts,
   five-second first-seen buckets, and template summary text. Results charts
   and run-browser metadata use this CSV-derived information.
8. When requested by the user, `build_brief` reads the run CSV and available
   snapshots, renders PDF charts, and writes `brief.pdf`. No PDF is generated
   before **Print Brief** is clicked.

The original uploaded video is not retained in the run folder. Annotated replay
is available from `annotated.mp4`; an original-versus-annotated viewer is
therefore not provided.

## 6. Run output and CSV schema

Each successful processing run writes:

```text
outputs/
└── run_YYYYMMDD_HHMMSS_microseconds/
    ├── detections.csv
    ├── annotated.mp4
    ├── snapshots/
    │   └── <class>_<track-id>.jpg
    └── brief.pdf               only after Print Brief
```

`detections.csv` columns:

| Column | Meaning |
|---|---|
| `video_name` | Original uploaded filename |
| `video_duration_sec` | Source video duration in seconds |
| `fps` | Source video frames per second |
| `processed_at` | Local timezone-aware processing timestamp |
| `track_id` | Tracker ID for the tracked object |
| `class` | Model class name |
| `first_seen_sec` | First observed time for this track |
| `last_seen_sec` | Last observed time for this track |
| `avg_confidence` | Mean detection confidence for this track |
| `snapshot_path` | Snapshot path relative to the run directory |

When no track meets the minimum length, the CSV contains a `__none__`
placeholder row with run metadata and blank object fields. This preserves run
metadata and allows zero-detection summaries and PDF briefs.

## 7. User interface

The interface remains a Streamlit application, styled with injected CSS. Its
default theme is dark graphite; the sidebar toggle switches to a light graphite
variant. IBM Plex Sans and IBM Plex Mono are requested via Google Fonts with
system-font fallbacks. If offline, the system fonts remain available.

### Analyze

- Upload MP4, AVI, or MOV.
- Choose model classes from all classes available in the loaded model, with
  curated defaults selected initially.
- Review read-only confidence, image-size, minimum-track, and device
  parameters.
- Run detection with progress text and elapsed time.
- View the live annotated frame and qualified class counts.
- Show an error for corrupt or unsupported video and a warning for video longer
  than five minutes; the long video can still be processed.

### Results

- KPI strip for unique object count, class count, most common class, busiest
  time window, duration, and processing speed.
- The existing CSV does not store processing throughput, so processing speed
  is explicitly displayed as **Not recorded**.
- Template summary and approximate-count warning.
- Hand-written SVG class-count/share bars, five-second timeline histogram with
  a rounded-top bar path and computed nice axis maximum, and 100% class-mix bar.
- Annotated video replay and saved snapshot cards linked to object dossiers.
- Detection parameters/provenance panel.
- CSV download, on-demand **Print Brief**, and PDF download after creation.

### Run Explorer

- Indexes run folders containing `detections.csv`.
- Filters by video filename, class, minimum unique-object count, and inclusive
  date range.
- Sorts by newest, most objects, or longest video.
- Shows matching-run count and loads results from a selected run.

### Object Dossier

- Opens from a Results snapshot card.
- Shows the selected object's snapshot when available, class, tracker ID,
  first/last seen, visible duration, average confidence, and share of total
  unique tracks in the run.
- Prev/Next navigation steps through the object list from which the dossier
  was opened; related objects of the same class are also shown.

The fixed class palette is defined in `ui/components.py`; unlisted classes use
a deterministic name-derived color. Class names accompany color swatches.
SVGs include responsive `viewBox` dimensions, accessible labels, and `<title>`
tooltips; they do not require JavaScript.

The UI contains no JavaScript-based interactions and uses no chart libraries.
CSS includes visible keyboard focus styling, reduced-motion handling, and
print rules that hide navigation and controls for browser printing.

## 8. PDF report

The PDF brief is a separate output from browser printing. `core/report.py`
builds the PDF only when explicitly requested and includes run metadata, a
unique-track count table, counts and timeline charts, the CSV-derived summary,
available snapshots (up to three per class), and a limitations note.
Matplotlib is used internally for these PDF charts only. Snapshot paths are
resolved relative to the run directory and rejected if they point outside it.

## 9. Installation and use

From PowerShell at the repository root:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Place the `yolo11s.pt` weights file in the project root, then verify CUDA:

```powershell
.\venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"
```

Start the web app:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

The default development URL is `http://localhost:8501`. To process a video
from the command line:

```powershell
.\venv\Scripts\python.exe -m core.detector test_videos\clip1.mp4
.\venv\Scripts\python.exe -m core.detector test_videos\clip1.mp4 --classes person car truck
```

To convert numbered JPEG sequence folders to H.264 test clips:

```powershell
.\venv\Scripts\python.exe -m tools.frames_to_video datasets\VisDrone-VID-val --output test_videos --fps 30 --limit 5
```

The README includes additional environment setup and demo instructions.

## 10. Tests and verification

Run the full test suite:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite currently contains 15 tests: the existing app and pipeline coverage
plus six UI helper/filter tests. Coverage includes:

- Corrupt upload reporting without app failure.
- Editing the class selection in the UI and passing it to detection.
- Synthetic selected-class tracking, CSV output, snapshot generation,
  annotated-video playability, preview callback cadence/counts, and class IDs.
- Corrupt video rejection and invalid preview parameter validation.
- Long video processing without retaining the full set of frames in memory.
- Zero-detection CSV analysis and PDF generation.
- JPEG sequence ordering, H.264 conversion, and command-line scanning.
- SVG content and values, sorting/share calculations, nice axis maximum,
  rounded bar path, deterministic class colors, time formatting, and run
  filtering/sorting.

The redesigned application was also started locally and checked through its
Streamlit health endpoint and browser/AppTest smoke tests. The last recorded
full-suite run after the UI change reported all 15 tests passing.

## 11. Validation and observed performance

The documented test machine is an NVIDIA GeForce RTX 4060 Laptop GPU with
CUDA-enabled PyTorch. Three VisDrone-VID validation sequences were converted at
an assumed 30 FPS and processed:

| Sequence | Frames | Resolution | End-to-end time | End-to-end FPS | Tracked IDs recorded |
|---|---:|---:|---:|---:|---|
| `uav0000137_00458_v` | 233 | 2688 × 1512 | 52.5 s | 4.44 | person 121, car 72, motorcycle 33, bicycle 24, bus 1, truck 1 |
| `uav0000305_00000_v` | 184 | 1904 × 1072 | 10.0 s | 18.41 | car 17, truck 1 |
| `uav0000339_00001_v` | 275 | 1904 × 1072 | 17.5 s | 15.76 | person 42, car 37, motorcycle 13, truck 6, bicycle 3 |

These are per-run observations including initialization and output writing, not
a controlled benchmark. The source archive frame rate was not independently
verified; durations depend on the 30 FPS conversion assumption. A separate
synthetic 90-frame, 320 × 240 blank clip completed in 7.47 seconds (12.04 FPS),
including model initialization and H.264 output. This synthetic result is not
representative of real footage.

Annotated frames and representative crops were visually checked. These
qualitative checks are not a formal accuracy evaluation. VisDrone categories do
not fully align with COCO, and trackers can split or merge identities.

## 12. Limitations and operational notes

- Counts are approximate: tracking can split one physical object into multiple
  IDs or merge different objects. Small or distant objects may be missed.
- CUDA is required for detection in the current pipeline. A CPU device label
  does not imply CPU inference support.
- The CSV does not include end-to-end processing time or processing FPS; the
  Results UI deliberately does not infer a speed metric.
- Original uploaded videos are temporary and are not kept alongside runs.
- A missing or corrupt snapshot does not change CSV-derived counts, but its
  image cannot be shown in the UI or PDF.
- The test clips, generated runs, dataset files, model weights, and Python
  environment are local/ignored files rather than committed project assets.
- The Google Fonts import requires network access to load IBM Plex; local
  system font fallbacks are used when unavailable.
- No accuracy claims should be inferred from the included tracked-ID counts.

## 13. Privacy, licensing, and data handling

Processing is local to the machine running Streamlit. The application does not
add accounts, roles, a database, or cloud processing. The uploaded source is
temporarily staged for detection; run outputs are stored under local
`outputs/`. Do not place sensitive footage in a publicly accessible deployment
without separately assessing access and storage controls.

The model library used is Ultralytics YOLO, which the project README identifies
as AGPL-3.0; review applicable license obligations before redistribution or
deployment. The VisDrone dataset and videos have their own terms. Check those
terms before reuse or redistribution; local dataset assets are excluded from
Git.

## 14. Current repository status

The UI redesign is on branch `ui-redesign`. The recent project history includes
the command-console redesign, project-log updates, and removal of the global
run/device/model/indexed/UTC status strip at the user's request. The frontend
currently retains sidebar navigation, the class legend, and the theme toggle.
Consult `git status` and the remote branch for the latest commit state.

## 15. Future work

Potential future work, not currently implemented:

- Batch upload queue with per-video statuses.
- Optional source-video retention for original-versus-annotated comparison.
- A safe, constrained query interface over CSV fields.
- Additional real-footage accuracy evaluation, high-altitude testing, and
  resource profiling on longer high-resolution clips.
