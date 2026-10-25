# DRISHTI Manual Startup Guide

Use these steps to start the DRISHTI app manually on Windows 11.

## 1. Open the project folder

Open PowerShell and change to the folder containing `app.py`:

```powershell
cd C:\army\DRISHTI
```

If your project is stored elsewhere, use that folder path instead.

## 2. Set up the environment (first time only)

DRISHTI uses Python 3.12 and CUDA-enabled PyTorch. If the project `venv`
already exists and has its dependencies installed, skip to step 3.

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install torch==2.11.0+cu128 torchvision==0.26.0+cu128 --index-url https://download.pytorch.org/whl/cu128
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

The detector requires CUDA. Check that PyTorch can see the GPU:

```powershell
.\venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"
```

The first app launch may take longer while the model is initialized. Keep the
project's `yolo11s.pt` weights file available in the project folder.

## 3. Start the app

Run this command from the project folder:

```powershell
.\venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
```

Streamlit normally opens the app in your browser. If it does not, open:

```text
http://localhost:8000
```

To select another port:

```powershell
.\venv\Scripts\python.exe -m uvicorn api.main:app --port 8000 --server.port 8502
```

Then browse to `http://localhost:8502`.

## 4. Use the app

1. Open **Analyze** and upload a supported video file.
2. Choose the object classes and select **Run**.
3. Review the CSV-derived results, annotated replay, and snapshots.
4. Download the CSV as needed. Select **Print Brief** only when you want the
   app to create the PDF.
5. Use **Run Explorer** to browse saved runs. Its city labels are dummy demo
   labels when a run has no recorded location; they are not verified
   geographic metadata.

New runs and reports are saved under `outputs\`. Sample clips, if present, are
under `test_videos\`.

## 5. Stop the app

Return to the PowerShell window where Streamlit is running and press:

```text
Ctrl+C
```

Wait for the process to exit before closing the terminal.

## Troubleshooting

- **`python.exe` not found:** Confirm the terminal is in the project folder and
  that `venv\Scripts\python.exe` exists. Recreate the environment using step 2
  if needed.
- **CUDA unavailable:** Confirm the NVIDIA driver is installed and the CUDA
  PyTorch check in step 2 reports `True`. The current detector does not support
  CPU inference.
- **Port already in use:** Start with a different port, such as `8502`, and
  open the matching local URL.
- **Video will not process:** Try a readable MP4, AVI, or MOV file. Corrupt
  videos are rejected with an app error.
- **No results appear:** Check that at least one class is selected and review
  the run's detection settings. A valid run can still have zero detections.

For setup details, detection settings, evaluation instructions, and known
limitations, see [README.md](README.md).
