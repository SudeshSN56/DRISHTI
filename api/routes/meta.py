from __future__ import annotations

from pathlib import Path
import torch
from fastapi import APIRouter
from ultralytics import YOLO

from core.config import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_CLASSES,
    HALF_PRECISION,
    IMAGE_SIZE,
    MAX_INFERENCE_WIDTH,
    MIN_BOX_PX,
    MIN_TRACK_FRAMES,
    MODEL_NAME,
    PROJECT_ROOT,
    TEST_VIDEOS_DIR,
)
from api.schemas import ModelInfoResponse

router = APIRouter(prefix="/api/model", tags=["model"])

_CACHED_MODEL_CLASSES: tuple[str, ...] | None = None


def get_all_model_classes() -> list[str]:
    global _CACHED_MODEL_CLASSES
    if _CACHED_MODEL_CLASSES is None:
        try:
            model = YOLO(MODEL_NAME)
            _CACHED_MODEL_CLASSES = tuple(sorted(model.names.values()))
        except Exception:
            _CACHED_MODEL_CLASSES = tuple(DEFAULT_CLASSES)
    return list(_CACHED_MODEL_CLASSES)


@router.get("/info", response_model=ModelInfoResponse)
def get_model_info() -> ModelInfoResponse:
    classes = get_all_model_classes()
    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else None
    return ModelInfoResponse(
        model_name=MODEL_NAME,
        default_classes=[c for c in DEFAULT_CLASSES if c in classes],
        all_classes=classes,
        cuda_available=cuda_avail,
        device_name=device_name,
        confidence_threshold=CONFIDENCE_THRESHOLD,
        image_size=IMAGE_SIZE,
        min_track_frames=MIN_TRACK_FRAMES,
        min_box_px=MIN_BOX_PX,
        max_inference_width=MAX_INFERENCE_WIDTH,
        half_precision=HALF_PRECISION,
    )


@router.get("/classes")
def get_classes() -> list[str]:
    return get_all_model_classes()


@router.get("/sample-videos")
def get_sample_videos() -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    if TEST_VIDEOS_DIR.is_dir():
        for vid in sorted(TEST_VIDEOS_DIR.glob("*.mp4")):
            samples.append({
                "name": vid.name,
                "path": str(vid.relative_to(PROJECT_ROOT)),
                "size_mb": round(vid.stat().st_size / (1024 * 1024), 2),
            })
    return samples
