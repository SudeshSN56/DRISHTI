# Chat Update Log

Project: Drone Surveillance Report System  
Last updated: 23 October 2026

## UI redesign — 23 October 2026

- Started from the clean committed `main` state on the `ui-redesign` branch.
- Replaced the single-page app UI with modular Streamlit pages for Analyze,
  Results, Run Explorer, and Object Dossier. Kept the detector, video source,
  report pipeline, CSV schema, and runtime dependencies unchanged.
- Added graphite dark/light CSS themes, a run/device/model/status top bar,
  persistent class legend, reusable console components, and accessible
  reduced-motion/focus styling.
- Added CSV-derived summary KPIs and pure responsive SVG class, five-second
  timeline, and stacked class-mix charts. Added snapshot dossier navigation,
  sortable/filterable run history, and print stylesheet.
- Existing nine tests passed before UI changes; all 15 tests pass with the new
  chart/filter helper coverage. The AppTest run-mocking seam was preserved.
- Launched Streamlit 1.66.0 and verified its local health endpoint, Analyze,
  zero-detection Results, and Run Explorer in a browser.
- Stretch work intentionally skipped: source-video retention, batch uploads,
  natural-language CSV queries, and a confidence histogram. Processing speed
  remains “Not recorded” because the current CSV does not include it.

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

- Revised Phase 0.5, Phase 1 live-preview, and Phase 3 live UI requirements are
  implemented. The full automated suite now has 9 passing tests.
- The VisDrone-VID validation archive is locally present under ignored
  `datasets/`, and three converted clips plus three detection runs are present
  locally. Dataset and generated video/output files are excluded from Git.
- The real detector completed all three selected sequences and the live-preview
  callback ran at the expected three-frame interval. A Streamlit AppTest
  rehearsal on a real VisDrone clip also verified preview rendering, CSV-based
  results, annotated video, and PDF generation only after **Print Brief**.
- Sampled first, middle, and last annotated frames from each clip and 13 of 371
  saved crops. The videos and crops are viewable, but crop usefulness varies:
  distant/partially visible objects can produce tiny or ambiguous crops. This
  was a qualitative output check, not a comparison against VisDrone ground
  truth or an accuracy evaluation.

## Remaining validation work

1. Compare sampled detections against corresponding VisDrone ground-truth
   annotations where classes and frame timing permit; do not treat raw track
   counts as accuracy metrics.
2. Obtain the planned separate stock clips and a 3–5-minute stress clip if
   available; currently the local sample consists of VisDrone validation
   sequences only. The synthetic >5-minute test does not replace measuring
   resource use on real 1080p footage.
3. Run a true high-altitude sample if available; the current selections are
   traffic/intersection footage and do not establish high-altitude behavior.
4. Review the dataset provider's reuse/redistribution terms before sharing any
   data or generated content derived from it.
5. Update this file with any further inspection results, resource measurements,
   or fixes.

## Candidate real-video validation data — VisDrone

- Recommended candidate: [VisDrone-VID](https://github.com/VisDrone/VisDrone-Dataset),
  the repository's video object-detection benchmark. Prefer a small number of
  validation or `test-dev` clips for local inference/validation; the repository
  lists these splits separately. Do not use the training split for this
  project's validation, because the project scope explicitly excludes model
  training.
- Use downloaded clips locally under `test_videos` after checking the dataset's
  download terms. That directory is intentionally git-ignored; do not add
  dataset videos or annotations to the source repository or its GitHub remote.
- The GitHub repository metadata reports no declared license and the README
  links to hosted downloads without stating reuse/redistribution terms. Confirm
  the applicable terms with the dataset providers before redistribution or
  public release. Citing the source is good practice, but attribution alone
  does not replace permission.
- The linked VID toolkit describes separate training, validation, and
  test-challenge sets; annotations are available for training/validation, while
  challenge annotations are unavailable. Its page says access is obtained via
  challenge registration and calls its code research-purpose-only.
- Check the downloaded file layout before using it: the toolkit works with
  per-frame sequences and benchmark annotation files, while this app's upload
  UI accepts MP4, AVI, or MOV. If the data arrives as ordered frames, create a
  local review video without changing the original dataset; record the chosen
  frame rate and sequence name so the test is reproducible.
- The project detector uses pretrained COCO classes, while VisDrone annotations
  contain dataset-specific categories. Treat this first as an end-to-end
  robustness check; do not claim annotation-level accuracy for categories that
  do not map directly to the selected COCO classes.
- Suggested citation from the official repository:

  ```bibtex
  @article{zhu2021detection,
    title={Detection and tracking meet drones challenge},
    author={Zhu, Pengfei and Wen, Longyin and Du, Dawei and Bian, Xiao and Fan, Heng and Hu, Qinghua and Ling, Haibin},
    journal={IEEE Transactions on Pattern Analysis and Machine Intelligence},
    volume={44},
    number={11},
    pages={7380--7399},
    year={2021},
    publisher={IEEE}
  }
  ```

## 21 October 2026 — Release-readiness recheck

- Re-ran the full automated suite: all 6 tests passed.
- Recompiled the app, core modules, and tests successfully.
- `pip check` reported no broken requirements.
- Confirmed `test_videos` has no supplied clips and `outputs` contains no test
  runs. Real-footage acceptance is still the next external prerequisite.

## 23 October 2026 — Revised plan implementation

- Added `tools/frames_to_video.py` to find sequence folders under a dataset
  parent, naturally sort JPG/JPEG frames, ignore annotation files, and write
  one H.264 MP4 per sequence. It supports FPS and sequence-limit arguments.
- Added ignored `datasets/` storage and documented the Phase 0.5 VisDrone
  validation workflow. Dataset archives and generated demo videos stay out of
  Git.
- The official Google Drive link initially returned a quota-exceeded page.
  Later the complete archive (`VisDrone2019-VID-val.zip`, 1,602,397,759 bytes)
  and extracted data appeared in the workspace. The archive passed ZIP
  validation and was moved under ignored `datasets/`; no unofficial mirror was
  used by the implementation.
- The validation set contains seven sequence frame folders. Selected the
  daytime traffic/crowd sequences `uav0000137_00458_v`, `uav0000305_00000_v`,
  and `uav0000339_00001_v` after checking sample images and annotation
  categories. The annotated sequences contain category-1 pedestrian and
  category-2 people instances as well as category-4 car instances.
- Stitched the three sequences to H.264 at the assumed 30 FPS. Verified all
  frames are playable:
  - `uav0000137_00458_v.mp4`: 233 frames, 2688x1512, about 7.77 seconds.
  - `uav0000305_00000_v.mp4`: 184 frames, 1904x1072, about 6.13 seconds.
  - `uav0000339_00001_v.mp4`: 275 frames, 1904x1072, about 9.17 seconds.
- Extended the detector with an optional live-preview callback. It supplies a
  downscaled annotated RGB image and per-class qualified track counts every
  three frames and at the last frame. The Streamlit Run view updates the image
  and counts beside progress.
- Revised automated tests to check callback interval/counts/dimensions, frame
  natural ordering and H.264 readability, and the UI's live preview.
- Added this `PLAN.md` to record phase status and revised requirements.

### Revised-plan verification

- Final revised suite: 9 automated tests pass; app/core/tests/tools compilation
  passes.
- Actual CUDA detections on the RTX 4060 Laptop GPU, using selected classes
  `person`, `car`, `truck`, `bus`, `bicycle`, and `motorcycle`:

  | Clip | Frames / size | Time | FPS | Tracked IDs by class |
  |---|---|---:|---:|---|
  | `uav0000137_00458_v.mp4` | 233 / 2688x1512 | 52.5 s | 4.44 | person 121, car 72, motorcycle 33, bicycle 24, bus 1, truck 1 |
  | `uav0000305_00000_v.mp4` | 184 / 1904x1072 | 10.0 s | 18.41 | car 17, truck 1 |
  | `uav0000339_00001_v.mp4` | 275 / 1904x1072 | 17.5 s | 15.76 | person 42, car 37, motorcycle 13, truck 6, bicycle 3 |

- The preview callback ran 78, 62, and 92 times for those clips. The Streamlit
  UI was also exercised with the 233-frame clip: live preview rendered; the
  results came from CSV; CSV and annotated video were present; no PDF existed
  until **Print Brief** was clicked; then a downloadable PDF was created.
- The three measured speeds are individual end-to-end runs with differing
  initialization/warm-up; do not compare them as a controlled benchmark or
  claim annotation-level model accuracy from these track counts. COCO and
  VisDrone classes differ, and trackers can split or merge IDs.
- Phase 0.5's three-playable-clip acceptance is met. The additional stock clips,
  real 3–5-minute stress footage, and high-altitude footage remain outstanding.

## Repository publishing

- Created seven local Git commits, one for each implementation phase (0–6),
  with the requested Copilot co-author trailer.
- GitHub CLI is installed, but `gh auth status` reports no authenticated
  account. The private remote repository has not yet been created and no
  commits have been uploaded. Before publishing, authenticate with
  `gh auth login`, then create a private repository and push `main`.
- Device-code login is currently waiting at `https://github.com/login/device`.
  A fresh one-time code was issued in the terminal output for this chat, but
  device authorization has not completed. The pending login process was stopped
  when account approval was unavailable. To continue, run
  `gh auth login --hostname github.com --git-protocol https --web --skip-ssh-key`,
  sign in and approve the device code in the browser, then confirm
  `gh auth status` before creating the private repository and pushing `main`.
- `.gitignore` excludes the virtual environment, model weights, Python caches,
  generated run folders, and local demo clips. `.vscode` is intentionally not
  included.

## 23 October 2026 — Local app preview

- Started Streamlit at `http://127.0.0.1:8501`; the local HTTP endpoint returned
  200 and the integrated browser rendered the project title, video upload, and
  class selector.
- To preview this checkout, open that URL while the Streamlit process is
  running. Upload one of the local converted clips from `test_videos/` and
  click **Run** to see live annotated frames/counts and the saved results.
- The server was started with
  `venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true`.

## 23 October 2026 — UI redesign handoff and app run

- Completed and committed the Streamlit command-console redesign on branch
  `ui-redesign` as `27aa42f` (`Redesign Streamlit command console UI`).
- Validation: all 15 tests pass, Python compilation and `git diff --check` pass,
  Streamlit's local health endpoint returns HTTP 200, and browser/AppTest
  smoke checks cover Analyze, CSV-based zero-detection and populated Results,
  Run Explorer selection, and Object Dossier navigation.
- No inference pipeline, detector/video source, CSV schema, or runtime
  dependency was changed. Print Brief remains generated only on request.
- The app is currently running at `http://localhost:8501`; its health endpoint
  returned HTTP 200 during this session.
- Removed the global run/device/model/indexed-runs/UTC status strip from the
  frontend while keeping sidebar navigation and the theme toggle. AppTest
  verified the strip is absent, and the running app health endpoint remains
  HTTP 200.
- The user requested publishing the work to GitHub. `origin` is
  `https://github.com/SudeshSN56/DRISHTI.git`, but `gh auth status` reports
  that no GitHub host is authenticated. The redesign commit is local on
  `ui-redesign`; push requires GitHub authentication.
