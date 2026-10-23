import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import sys
import time
from collections import Counter
from typing import Callable, Mapping, Sequence

import cv2
import numpy as np
import torch
import yaml
from imageio_ffmpeg import write_frames
from ultralytics import YOLO

from core.config import (
    CONFIDENCE_THRESHOLD,
    CLASS_CONFIDENCE_OVERRIDES,
    DEFAULT_CLASSES,
    IMAGE_SIZE,
    MAX_INFERENCE_WIDTH,
    HALF_PRECISION,
    MIN_BOX_PX,
    MIN_TRACK_FRAMES,
    MODEL_NAME,
    OUTPUTS_DIR,
    TRACKER_CONFIG_PATH,
)
from core.video_source import VideoSource, VideoSourceError


ProgressCallback = Callable[[int, int], None]
LivePreviewCallback = Callable[[np.ndarray, dict[str, int]], None]

CSV_COLUMNS = (
    "video_name",
    "video_duration_sec",
    "fps",
    "processed_at",
    "track_id",
    "class",
    "first_seen_sec",
    "last_seen_sec",
    "avg_confidence",
    "snapshot_path",
    "model",
    "confidence",
    "imgsz",
    "min_track_frames",
    "min_box_px",
    "processing_seconds",
    "device",
    "confidence_overrides",
    "track_buffer",
    "max_inference_width",
    "half_precision",
)


@dataclass
class TrackSummary:
    track_id: int
    class_name: str
    first_seen_sec: float
    last_seen_sec: float
    confidence_sum: float
    frames_seen: int
    best_confidence: float
    snapshot_path: Path

    @property
    def avg_confidence(self) -> float:
        return self.confidence_sum / self.frames_seen


def _create_run_directory(output_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = output_root / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "snapshots").mkdir()
    return run_dir


def _safe_class_name(name: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return safe_name or "object"


def resize_for_inference(
    frame: np.ndarray,
    max_width: int,
) -> tuple[np.ndarray, float, float]:
    """Resize only for inference and return source-pixel scale factors."""
    if max_width < 0:
        raise ValueError("Maximum inference width cannot be negative.")
    height, width = frame.shape[:2]
    if max_width == 0 or width <= max_width:
        return frame, 1.0, 1.0
    resized_height = max(1, round(height * max_width / width))
    resized = cv2.resize(
        frame,
        (max_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )
    return resized, width / max_width, height / resized_height


def map_box_to_source(
    box: Sequence[float],
    scale_x: float,
    scale_y: float,
    source_width: int,
    source_height: int,
) -> tuple[int, int, int, int]:
    return (
        max(0, int(box[0] * scale_x)),
        max(0, int(box[1] * scale_y)),
        min(source_width, int(box[2] * scale_x)),
        min(source_height, int(box[3] * scale_y)),
    )


def _write_csv(
    csv_path: Path,
    video_name: str,
    duration_sec: float,
    fps: float,
    processed_at: str,
    tracks: dict[int, TrackSummary],
    processing_seconds: float,
    device: str,
    model_name: str,
    confidence: float,
    imgsz: int,
    min_track_frames: int,
    min_box_px: int,
    confidence_overrides: Mapping[str, float],
    track_buffer: int,
    max_inference_width: int,
    half_precision: bool,
) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        kept_tracks = [
            track for track in tracks.values()
            if track.frames_seen >= min_track_frames
        ]
        if not kept_tracks:
            writer.writerow(
                {
                    "video_name": video_name,
                    "video_duration_sec": duration_sec,
                    "fps": fps,
                    "processed_at": processed_at,
                    "track_id": "",
                    "class": "__none__",
                    "first_seen_sec": "",
                    "last_seen_sec": "",
                    "avg_confidence": "",
                    "snapshot_path": "",
                    "model": model_name,
                    "confidence": confidence,
                    "imgsz": imgsz,
                    "min_track_frames": min_track_frames,
                    "min_box_px": min_box_px,
                    "processing_seconds": round(processing_seconds, 6),
                    "device": device,
                    "confidence_overrides": json.dumps(
                        confidence_overrides,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "track_buffer": track_buffer,
                    "max_inference_width": max_inference_width,
                    "half_precision": half_precision,
                }
            )
            return

        for track in sorted(kept_tracks, key=lambda item: (item.class_name, item.track_id)):
            writer.writerow(
                {
                    "video_name": video_name,
                    "video_duration_sec": duration_sec,
                    "fps": fps,
                    "processed_at": processed_at,
                    "track_id": track.track_id,
                    "class": track.class_name,
                    "first_seen_sec": round(track.first_seen_sec, 3),
                    "last_seen_sec": round(track.last_seen_sec, 3),
                    "avg_confidence": round(track.avg_confidence, 5),
                    "snapshot_path": track.snapshot_path.relative_to(csv_path.parent).as_posix(),
                    "model": model_name,
                    "confidence": confidence,
                    "imgsz": imgsz,
                    "min_track_frames": min_track_frames,
                    "min_box_px": min_box_px,
                    "processing_seconds": round(processing_seconds, 6),
                    "device": device,
                    "confidence_overrides": json.dumps(
                        confidence_overrides,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "track_buffer": track_buffer,
                    "max_inference_width": max_inference_width,
                    "half_precision": half_precision,
                }
            )


def run_detection(
    video_path: str | Path,
    selected_classes: Sequence[str] | None = None,
    progress_callback: ProgressCallback | None = None,
    preview_callback: LivePreviewCallback | None = None,
    preview_every_n_frames: int = 3,
    preview_max_width: int = 640,
    output_root: str | Path = OUTPUTS_DIR,
    model_name: str = MODEL_NAME,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    imgsz: int = IMAGE_SIZE,
    min_track_frames: int = MIN_TRACK_FRAMES,
    min_box_px: int = MIN_BOX_PX,
    confidence_overrides: Mapping[str, float] | None = None,
    tracker_config: str | Path = TRACKER_CONFIG_PATH,
    max_inference_width: int = MAX_INFERENCE_WIDTH,
    half_precision: bool = HALF_PRECISION,
) -> Path:
    """Track selected COCO classes and optionally stream RGB preview frames."""
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Install a CUDA-enabled PyTorch build to run detection.")
    if preview_every_n_frames <= 0:
        raise ValueError("Live preview interval must be a positive number of frames.")
    if preview_max_width <= 0:
        raise ValueError("Live preview width must be a positive number of pixels.")

    classes = tuple(selected_classes if selected_classes is not None else DEFAULT_CLASSES)
    if not classes:
        raise ValueError("Select at least one object class before running detection.")
    if len(set(classes)) != len(classes):
        raise ValueError("Selected object classes must not contain duplicates.")
    if not 0 <= confidence_threshold <= 1:
        raise ValueError("Confidence threshold must be between 0 and 1.")
    if imgsz <= 0 or min_track_frames <= 0 or min_box_px < 0:
        raise ValueError("Image size and minimum track length must be positive; pixel settings cannot be negative.")
    if max_inference_width < 0:
        raise ValueError("Maximum inference width cannot be negative.")
    overrides = dict(
        CLASS_CONFIDENCE_OVERRIDES
        if confidence_overrides is None
        else confidence_overrides
    )
    if any(not 0 <= value <= 1 for value in overrides.values()):
        raise ValueError("Per-class confidence thresholds must be between 0 and 1.")
    tracker_config = Path(tracker_config)
    if not tracker_config.is_file():
        raise FileNotFoundError(f"Tracker configuration does not exist: {tracker_config}")
    with tracker_config.open(encoding="utf-8") as tracker_file:
        tracker_settings = yaml.safe_load(tracker_file)
    if not isinstance(tracker_settings, dict) or "track_buffer" not in tracker_settings:
        raise ValueError(f"Tracker config is missing track_buffer: {tracker_config}")
    track_buffer = int(tracker_settings["track_buffer"])

    started_at = time.perf_counter()
    with VideoSource(video_path) as source:
        metadata = source.metadata
        model = YOLO(model_name)
        names = model.names
        names_by_id = {int(class_id): name for class_id, name in names.items()}
        class_ids_by_name = {name: class_id for class_id, name in names_by_id.items()}
        unknown_classes = sorted(set(classes) - class_ids_by_name.keys())
        if unknown_classes:
            raise ValueError(f"Selected classes are not in the model: {', '.join(unknown_classes)}")
        selected_class_ids = [class_ids_by_name[name] for name in classes]

        run_dir = _create_run_directory(Path(output_root))
        snapshots_dir = run_dir / "snapshots"
        annotated_path = run_dir / "annotated.mp4"
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        tracks: dict[int, TrackSummary] = {}
        frame_index = 0
        writer = write_frames(
            annotated_path,
            (metadata.width + metadata.width % 2, metadata.height + metadata.height % 2),
            fps=metadata.fps,
            codec="libx264",
            macro_block_size=1,
            output_params=["-movflags", "+faststart"],
        )
        writer.send(None)

        try:
            while True:
                readable, frame = source.read()
                if not readable:
                    break

                source_height, source_width = frame.shape[:2]
                inference_frame, scale_x, scale_y = resize_for_inference(
                    frame,
                    max_inference_width,
                )

                result = model.track(
                    inference_frame,
                    persist=True,
                    tracker=str(tracker_config),
                    classes=selected_class_ids,
                    conf=min([confidence_threshold, *overrides.values()]),
                    imgsz=imgsz,
                    device=0,
                    quantize=16 if half_precision else None,
                    verbose=False,
                )[0]

                if result.boxes is not None and result.boxes.id is not None:
                    boxes = result.boxes.xyxy.cpu().tolist()
                    class_ids = result.boxes.cls.cpu().tolist()
                    confidences = result.boxes.conf.cpu().tolist()
                    track_ids = result.boxes.id.int().cpu().tolist()
                    time_sec = frame_index / metadata.fps
                    for box, class_id, confidence, track_id in zip(
                        boxes, class_ids, confidences, track_ids
                    ):
                        class_name = names_by_id[int(class_id)]
                        if float(confidence) < overrides.get(class_name, confidence_threshold):
                            continue
                        if min_box_px and (
                            float(box[2]) - float(box[0]) < min_box_px
                            or float(box[3]) - float(box[1]) < min_box_px
                        ):
                            continue
                        track = tracks.get(track_id)
                        x1, y1, x2, y2 = map_box_to_source(
                            box,
                            scale_x,
                            scale_y,
                            metadata.width,
                            metadata.height,
                        )
                        if track is None:
                            snapshot_path = snapshots_dir / (
                                f"{_safe_class_name(class_name)}_{track_id}.jpg"
                            )
                            track = TrackSummary(
                                track_id=track_id,
                                class_name=class_name,
                                first_seen_sec=time_sec,
                                last_seen_sec=time_sec,
                                confidence_sum=0.0,
                                frames_seen=0,
                                best_confidence=-1.0,
                                snapshot_path=snapshot_path,
                            )
                            tracks[track_id] = track

                        track.last_seen_sec = time_sec
                        track.confidence_sum += float(confidence)
                        track.frames_seen += 1
                        if confidence > track.best_confidence and x2 > x1 and y2 > y1:
                            if not cv2.imwrite(
                                str(track.snapshot_path),
                                frame[y1:y2, x1:x2],
                            ):
                                raise OSError(f"Could not write snapshot: {track.snapshot_path}")
                            track.best_confidence = float(confidence)

                annotated_frame = result.plot()
                if annotated_frame.shape[:2] != (metadata.height, metadata.width):
                    annotated_frame = cv2.resize(
                        annotated_frame,
                        (metadata.width, metadata.height),
                        interpolation=cv2.INTER_LINEAR,
                    )
                frame_index += 1
                if preview_callback is not None and (
                    frame_index % preview_every_n_frames == 0
                    or frame_index == metadata.frame_count
                ):
                    preview_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                    if metadata.width > preview_max_width:
                        preview_height = round(
                            metadata.height * preview_max_width / metadata.width
                        )
                        preview_frame = cv2.resize(
                            preview_frame,
                            (preview_max_width, preview_height),
                            interpolation=cv2.INTER_AREA,
                        )
                    live_counts = Counter(
                        track.class_name
                        for track in tracks.values()
                        if track.frames_seen >= min_track_frames
                    )
                    preview_callback(
                        preview_frame,
                        dict(sorted(live_counts.items())),
                    )

                if metadata.width % 2 or metadata.height % 2:
                    annotated_frame = cv2.copyMakeBorder(
                        annotated_frame,
                        0,
                        metadata.height % 2,
                        0,
                        metadata.width % 2,
                        cv2.BORDER_CONSTANT,
                        value=(0, 0, 0),
                    )
                writer.send(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))
                if progress_callback is not None:
                    progress_callback(frame_index, metadata.frame_count)
        finally:
            writer.close()

        kept_track_ids = {
            track_id for track_id, track in tracks.items()
            if track.frames_seen >= min_track_frames
        }
        for track_id, track in tracks.items():
            if track_id not in kept_track_ids and track.snapshot_path.exists():
                track.snapshot_path.unlink()

        processing_seconds = time.perf_counter() - started_at
        _write_csv(
            run_dir / "detections.csv",
            metadata.path.name,
            metadata.duration_sec,
            metadata.fps,
            timestamp,
            tracks,
            processing_seconds,
            torch.cuda.get_device_name(0),
            model_name,
            confidence_threshold,
            imgsz,
            min_track_frames,
            min_box_px,
            overrides,
            track_buffer,
            max_inference_width,
            half_precision,
        )
        return run_dir


def _main() -> int:
    parser = argparse.ArgumentParser(description="Track selected objects in a video.")
    parser.add_argument("video", type=Path, help="Path to an MP4, AVI, or MOV video.")
    parser.add_argument(
        "--classes",
        nargs="+",
        default=list(DEFAULT_CLASSES),
        help="COCO class names to detect (default: curated drone-surveillance list).",
    )
    args = parser.parse_args()

    def show_progress(processed: int, total: int) -> None:
        percent = processed * 100 // total
        print(f"\rProcessing: {processed}/{total} frames ({percent}%)", end="", flush=True)

    try:
        run_dir = run_detection(args.video, args.classes, show_progress)
    except (VideoSourceError, ValueError, RuntimeError, OSError) as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1
    print(f"\nRun complete: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
