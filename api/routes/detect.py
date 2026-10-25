from __future__ import annotations

import base64
import json
import queue
import tempfile
import threading
import time
from pathlib import Path
from typing import AsyncGenerator

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from core import detector
from core.analysis import analyze_csv
from core.config import DEFAULT_CLASSES, PROJECT_ROOT

router = APIRouter(prefix="/api/detect", tags=["detection"])


def _encode_frame_jpeg_base64(frame_rgb: np.ndarray, quality: int = 70) -> str:
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    success, buffer = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("ascii")


def _run_detection_thread(
    video_path: Path,
    selected_classes: list[str],
    event_queue: queue.Queue,
    temp_dir_to_clean: tempfile.TemporaryDirectory | None,
):
    start_time = time.perf_counter()

    def progress_callback(processed: int, total: int) -> None:
        elapsed = time.perf_counter() - start_time
        fps = processed / max(elapsed, 1e-6)
        percent = round(min(processed / max(total, 1), 1.0) * 100, 1)
        event_queue.put(
            {
                "type": "progress",
                "processed": processed,
                "total": total,
                "percent": percent,
                "fps": round(fps, 1),
                "elapsed": round(elapsed, 1),
            }
        )

    def preview_callback(frame_rgb: np.ndarray, live_counts: dict[str, int]) -> None:
        frame_b64 = _encode_frame_jpeg_base64(frame_rgb, quality=75)
        event_queue.put(
            {
                "type": "preview",
                "frame": frame_b64,
                "counts": live_counts,
            }
        )

    try:
        run_dir = detector.run_detection(
            video_path=video_path,
            selected_classes=selected_classes,
            progress_callback=progress_callback,
            preview_callback=preview_callback,
        )
        csv_path = run_dir / "detections.csv"
        summary = ""
        if csv_path.is_file():
            try:
                analysis = analyze_csv(csv_path)
                summary = analysis.summary
            except Exception:
                summary = "Analysis generated."

        event_queue.put(
            {
                "type": "complete",
                "run_id": run_dir.name,
                "summary": summary,
                "elapsed": round(time.perf_counter() - start_time, 1),
            }
        )
    except Exception as e:
        event_queue.put({"type": "error", "message": str(e)})
    finally:
        event_queue.put(None)  # Sentinel to end SSE
        if temp_dir_to_clean:
            try:
                temp_dir_to_clean.cleanup()
            except Exception:
                pass


@router.post("")
async def start_detection(
    file: UploadFile | None = File(None),
    sample_path: str | None = Form(None),
    classes: str = Form(""),
):
    selected_classes: list[str] = []
    if classes.strip():
        try:
            parsed = json.loads(classes)
            if isinstance(parsed, list):
                selected_classes = [str(c).strip() for c in parsed if str(c).strip()]
        except Exception:
            selected_classes = [c.strip() for c in classes.split(",") if c.strip()]

    if not selected_classes:
        selected_classes = list(DEFAULT_CLASSES)

    temp_dir = None
    target_video_path: Path

    if file and file.filename:
        temp_dir = tempfile.TemporaryDirectory()
        target_video_path = Path(temp_dir.name) / Path(file.filename).name
        content = await file.read()
        target_video_path.write_bytes(content)
    elif sample_path:
        target_video_path = (PROJECT_ROOT / sample_path).resolve()
        if not target_video_path.is_file():
            raise HTTPException(status_code=404, detail=f"Sample video not found: {sample_path}")
    else:
        raise HTTPException(status_code=400, detail="Either file upload or sample_path must be provided")

    event_queue: queue.Queue = queue.Queue(maxsize=100)

    worker = threading.Thread(
        target=_run_detection_thread,
        args=(target_video_path, selected_classes, event_queue, temp_dir),
        daemon=True,
    )
    worker.start()

    async def sse_event_generator() -> AsyncGenerator[str, None]:
        while True:
            # Check for events without busy-waiting
            try:
                item = event_queue.get(timeout=0.1)
            except queue.Empty:
                # Send SSE ping to keep connection open
                yield ": keep-alive\n\n"
                continue

            if item is None:
                # Finished
                break

            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
