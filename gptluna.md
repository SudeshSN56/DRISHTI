# Chat Update Log

Project: Drone Surveillance Report System  
Last updated: 21 October 2026

This file records the implementation updates completed in this chat. The project
plan is being followed phase by phase.

## Phase 0 — Setup

- Created the project scaffold, including `core`, `outputs`, `test_videos`, and
  `.streamlit`.
- Installed Python 3.12.10 and created the `venv` environment.
- Installed CUDA-enabled PyTorch and the project dependencies.
- Verified CUDA is available on the NVIDIA GeForce RTX 4060 Laptop GPU.
- Ran an Ultralytics YOLO prediction on the GPU successfully.
- Added initial configuration, dependency list, upload-size configuration,
  `.gitignore`, and setup instructions in README.

## Phase 1 — Core video pipeline

- Added `core/video_source.py` to open video files, validate metadata and
  readable frames, and report clear errors for invalid input.
- Added `core/detector.py` to run YOLO with ByteTrack on CUDA, derive class IDs
  from the model, track selected classes, save highest-confidence snapshots,
  and report progress.
- The pipeline writes `detections.csv`, an H.264 `annotated.mp4`, and qualifying
  object snapshots. It writes the required `__none__` placeholder when there
  are no qualifying tracks.
- Added the ByteTrack `lap` dependency and CLI usage instructions to README.
- Verified a generated clip through the CUDA detector CLI, checked the CSV,
  H.264 codec, and playable output frames. Also tested tracked CSV rows,
  snapshots, progress reporting, zero detections, and invalid video handling.
- No real demo footage was supplied, so real-footage acceptance remains to be
  tested.

## Phase 2 — CSV analysis

- Added `core/analysis.py` with `analyze_csv(path)`.
- Analysis reads the CSV only and returns run metadata, unique per-class track
  counts, first-seen counts in five-second buckets, and a template summary.
- The summary includes total objects, the most common class, the busiest time
  window, video duration, and a note that tracking counts are approximate.
- Added handling for the zero-detection placeholder and validation for malformed
  CSV data and invalid bucket sizes.
- Verified counts, timeline buckets, summary content, empty results, and that
  analysis works with only the CSV present.

## Phase 3 — Streamlit UI

- Added `app.py` with video upload, model-derived class selection, curated
  defaults, a Run button with progress, and a warning for videos longer than
  five minutes.
- Results are computed from the saved CSV and include counts, charts, timeline,
  summary, CSV download, annotated-video playback, and snapshot gallery.
- Added navigation for previous output folders that contain a `detections.csv`.
- Added clear errors for unreadable/corrupt video uploads. Temporary uploads are
  cleaned up after processing, and the original upload filename is preserved
  in the detection CSV.
- Added launch instructions to README.
- Verified the UI renders with all model class options and expected defaults;
  exercised upload, processing, results, CSV download, video display, and corrupt
  upload behavior using a generated test clip. Also verified the local app in a
  browser and cleaned temporary test outputs.

## Phase 4 — Print Brief PDF

- Added `core/report.py` to create `brief.pdf` from the selected run's CSV and
  available snapshot images. Counts and timeline charts are rendered from the
  CSV analysis; the brief includes run metadata, a counts table, summary,
  snapshot grid, and limitations note.
- Added **Print Brief** and **Download Brief PDF** to the results UI. The PDF is
  not created until the user clicks **Print Brief**, and older run folders can
  be selected and reported.
- Documented the report workflow in README.
- Verified PDF text and counts against a prior-format CSV with saved snapshots.
  Also verified the zero-detection PDF and the UI behavior that no PDF exists
  until the button is clicked.

## Phase 5 — Automated testing

- Phase 5 automated checks pass for synthetic normal, empty, corrupt, class
  selection, and 5-minute-plus video cases (`python -m unittest discover -s tests
  -v`: 6 tests passed). Core/app/test compilation also passed. A synthetic
  90-frame CUDA benchmark measured 12.04 end-to-end FPS on the RTX 4060 Laptop
  GPU.
- Real traffic/crowd/high-altitude footage was not supplied. The real-world
  accuracy checks, memory behavior on real 1080p input, and two-clip acceptance
  run remain pending.

## Phase 6 — Demo preparation

- Phase 6 README updates include a Windows clean-start demo checklist and the
  known limitations.
- Rehearsed the complete Streamlit flow twice in clean sessions with generated
  clips and the real CUDA detector: upload, choose class, run, view results,
  download CSV, verify annotated video, click **Print Brief**, and download the
  resulting PDF. Confirmed no PDF existed before the click and cleaned up both
  runs afterward.
- The rehearsals validate the application flow only. The live evaluator demo
  and accuracy checks on traffic/crowd/high-altitude footage still require real
  supplied clips.

## Current status

- Phases 0–6 software implementation and synthetic verification are complete;
  final tests pass (6 automated tests).
- The app is ready for real-video validation. No demo videos are currently in
  `test_videos`.

## When demo videos are provided — remaining work

1. Put the traffic and crowd clips in `test_videos` and record their filenames
   and basic properties (duration, resolution, and FPS) in this log.
2. Run both clips end to end. Check CSV rows against a manual sample count,
   verify snapshots and annotated H.264 playback, download the CSV, click
   **Print Brief**, and compare PDF counts with the CSV.
3. Run a clip with no selected objects and confirm the friendly empty-results
   message and a valid zero-detection PDF.
4. Run a corrupt or non-video file and confirm the app shows a clear error
   without crashing.
5. Run a clip near five minutes and record elapsed time, processed FPS, and
   peak memory. Confirm upload and processing work.
6. Run a high-altitude clip, record observed misses, and report them as the
   documented small-object limitation rather than assuming perfect detection.
7. Repeat with edited class selections and confirm CSV/results change
   accordingly.
8. Update this `gptluna.md` with the video names, results, measurements, failures
   and fixes, then update README's test status if the measured results change.

Do not mark real-footage acceptance complete until the two different real clips
have passed the end-to-end checks. The current synthetic FPS figure is only a
baseline and must not be presented as measured real-footage performance.

## 21 October 2026 — Release-readiness recheck

- Re-ran the full automated suite: all 6 tests passed.
- Recompiled the app, core modules, and tests successfully.
- `pip check` reported no broken requirements.
- Confirmed `test_videos` has no supplied clips and `outputs` contains no test
  runs. Real-footage acceptance is still the next external prerequisite.

## Repository publishing

- Created seven local Git commits, one for each implementation phase (0–6),
  with the requested Copilot co-author trailer.
- GitHub CLI is installed, but `gh auth status` reports no authenticated
  account. The private remote repository has not yet been created and no
  commits have been uploaded. Before publishing, authenticate with
  `gh auth login`, then create a private repository and push `main`.
- `.gitignore` excludes the virtual environment, model weights, Python caches,
  generated run folders, and local demo clips. `.vscode` is intentionally not
  included.
