from __future__ import annotations

from pydantic import BaseModel


class CountItem(BaseModel):
    class_name: str
    count: int


class TimelineItem(BaseModel):
    bucket_start_sec: float
    bucket_end_sec: float
    class_name: str
    count: int


class SnapshotItem(BaseModel):
    track_id: str
    class_name: str
    first_seen_sec: float
    last_seen_sec: float
    avg_confidence: float | None = None
    path: str | None = None


class RunSummaryResponse(BaseModel):
    id: str
    video_name: str
    processed_at: str
    duration_sec: float
    total_objects: int
    classes: list[str]
    location: str | None = None
    has_annotated_video: bool = False
    has_brief: bool = False


class RunDetailResponse(BaseModel):
    id: str
    video_name: str
    processed_at: str
    duration_sec: float
    summary: str
    counts: list[CountItem]
    timeline: list[TimelineItem]
    visible_timeline: list[TimelineItem]
    fps: float | None = None
    processing_fps: float | None = None
    model: str | None = None
    confidence: float | None = None
    imgsz: int | None = None
    min_track_frames: int | None = None
    min_box_px: int | None = None
    processing_seconds: float | None = None
    device: str | None = None
    location: str | None = None
    confidence_overrides: str | None = None
    snapshots: list[SnapshotItem]
    has_annotated_video: bool = False
    has_brief: bool = False


class ModelInfoResponse(BaseModel):
    model_name: str
    default_classes: list[str]
    all_classes: list[str]
    cuda_available: bool
    device_name: str | None = None
    confidence_threshold: float
    image_size: int
    min_track_frames: int
    min_box_px: int
    max_inference_width: int
    half_precision: bool


class BriefResponse(BaseModel):
    status: str
    path: str
    filename: str
