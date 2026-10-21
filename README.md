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
and minimum track length are in `core/config.py`.

Ultralytics YOLO is licensed under AGPL-3.0. Review its terms before
redistributing or deploying software that uses it.
