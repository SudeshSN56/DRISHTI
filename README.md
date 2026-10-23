# Drone Surveillance Report System

A local Streamlit application for analyzing recorded drone video with a
pretrained Ultralytics YOLO model. The project targets Windows 11 and Python
3.12.

## Phase 0: setup

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

The PyTorch command uses the CUDA 12.8 wheel index from the official
[PyTorch installation selector](https://pytorch.org/get-started/locally/).
Verify the installation:

```powershell
.\venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"
```

## Phase 0.5: prepare local demo clips

Keep downloaded datasets under `datasets/` and do not commit dataset archives,
frames, or derived clips. That folder and `test_videos/` are git-ignored.
VisDrone's official [dataset page](https://github.com/VisDrone/VisDrone-Dataset)
links the VisDrone-VID validation archive (about 1.49 GB). Check its download
and reuse terms before use or redistribution.

If the extracted data contains numbered JPG frame folders, stitch up to five
sequences into H.264 MP4 clips at 30 FPS (or use the FPS specified by the
dataset):

```powershell
.\venv\Scripts\python.exe -m tools.frames_to_video datasets\VisDrone-VID-val --output test_videos --fps 30 --limit 5
```

The utility scans child directories containing JPG/JPEG frames, sorts numbered
names naturally, ignores annotation/text files, and creates one MP4 per
sequence. Add a few separate stock or stress-test clips to `test_videos`
manually. No dataset files are committed with this source project. Google Drive
reported that its quota was exceeded during an initial automated download
attempt; a local validation archive has since been placed under `datasets/`.

## Phase 1: video detection

Run the command-line pipeline with the curated default class list:

```powershell
.\venv\Scripts\python.exe -m core.detector test_videos\clip1.mp4
```

Or choose model class names explicitly:

```powershell
.\venv\Scripts\python.exe -m core.detector test_videos\clip1.mp4 --classes person car truck
```

Each run writes `detections.csv`, an H.264 `annotated.mp4`, and qualifying
highest-confidence object crops under a timestamped folder in `outputs`.
Detection requires CUDA; the current confidence threshold, image size, model,
and minimum track length are in `core/config.py`. The optional live-preview
callback receives a downscaled annotated RGB frame and per-class counts every
three frames (and on the final frame); tracks shorter than the configured
minimum are excluded from live counts.

## Phase 2: CSV analysis

`core.analysis.analyze_csv(path)` reads only `detections.csv` and returns run
metadata, unique track counts by class, a five-second first-seen timeline with
zero-count buckets, and a template-based summary. It also handles the
`__none__` placeholder without requiring other run files.

## Phase 3: Streamlit app

Start the local app:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

Upload an MP4, AVI, or MOV, choose from the model's available classes, and
select **Run**. While the video is processed, the page refreshes a downscaled
annotated preview and qualified per-class live counts beside the progress bar.
After processing, results are read from the saved CSV and include counts,
charts, a first-seen timeline, a summary, the annotated video, and snapshots.
Download the CSV or select a previous run from the results list. Corrupt video
files show a clear error; videos over five minutes show a warning but still run.

## Phase 4: Print Brief

Select any run with a `detections.csv`, then click **Print Brief** to create
`brief.pdf` in that run folder. Metadata, counts, charts, and summary are built
from the selected CSV; available snapshots are included. The PDF is created
only when the user clicks the button.

## Phase 5: automated checks and current test coverage

Run the synthetic-video and UI tests:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers class filtering, CSV/snapshot output, H.264 video, corrupt
uploads, zero-detection reports, editable classes, and a synthetic clip longer
than five minutes. It also verifies live-preview frame/counter callbacks and
the JPG-sequence conversion utility.

An end-to-end benchmark on the RTX 4060 Laptop GPU processed a generated
90-frame, 320x240 blank clip in 7.47 seconds (12.04 FPS), including model
loading and H.264 output. This synthetic result is not representative of real
drone footage.

Three VisDrone-VID validation sequences were converted and processed on the
RTX 4060 Laptop GPU at 30 FPS:

The source archive's native frame rate was not independently verified; 30 FPS
is the conversion assumption, so durations and processing rates below are
conditional on that setting.

| Sequence | Frames | Resolution | End-to-end time | End-to-end FPS | YOLO tracked IDs by class |
|---|---:|---:|---:|---:|---|
| `uav0000137_00458_v` | 233 | 2688x1512 | 52.5 s | 4.44 | person 121, car 72, motorcycle 33, bicycle 24, bus 1, truck 1 |
| `uav0000305_00000_v` | 184 | 1904x1072 | 10.0 s | 18.41 | car 17, truck 1 |
| `uav0000339_00001_v` | 275 | 1904x1072 | 17.5 s | 15.76 | person 42, car 37, motorcycle 13, truck 6, bicycle 3 |

Times include model initialization and full video output and vary with warm-up;
these are per-clip observations, not a controlled benchmark. COCO and VisDrone
categories do not fully align, and trackers may split or merge IDs, so these
counts are not a formal accuracy evaluation. Sampled annotated frames and
representative saved crops were visually checked; crop usefulness varies for
distant or partially visible objects. Ground-truth comparison and resource
measurement on real stress footage remain future validation work.

## Phase 6: clean-start demo checklist

From a fresh PowerShell window in the project directory:

1. Confirm CUDA and the RTX 4060 with
   `.\venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`.
2. Start the app with `.\venv\Scripts\python.exe -m streamlit run app.py`.
3. Upload a recorded clip, choose classes, and click **Run**.
4. Review the CSV-derived results and annotated video, then download the CSV.
5. Click **Print Brief**, download the PDF, and compare its counts to the CSV.
6. Repeat with a second clip and test a corrupt/non-video upload.

Small objects at altitude may be missed; tracking can split or merge IDs, so
counts are approximate. Live streams, GPS, thermal/night footage, model
training, and cloud processing are outside this version's scope.

Ultralytics YOLO is licensed under AGPL-3.0. Review its terms before
redistributing or deploying software that uses it.
