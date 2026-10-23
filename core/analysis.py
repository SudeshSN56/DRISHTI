from dataclasses import dataclass
from math import ceil
from pathlib import Path

import pandas as pd

from core.config import TIMELINE_BUCKET_SECONDS


REQUIRED_COLUMNS = {
    "video_name",
    "video_duration_sec",
    "processed_at",
    "track_id",
    "class",
    "first_seen_sec",
}


@dataclass(frozen=True)
class AnalysisResult:
    video_name: str
    video_duration_sec: float
    processed_at: str
    counts: pd.DataFrame
    timeline: pd.DataFrame
    visible_timeline: pd.DataFrame
    summary: str
    fps: float | None = None
    model: str | None = None
    confidence: float | None = None
    imgsz: int | None = None
    min_track_frames: int | None = None
    min_box_px: int | None = None
    processing_seconds: float | None = None
    device: str | None = None
    location: str | None = None
    confidence_overrides: str | None = None
    track_buffer: int | None = None
    max_inference_width: int | None = None
    half_precision: bool | None = None
    min_snapshot_size_px: int | None = None
    snapshot_padding_px: int | None = None

    @property
    def processing_fps(self) -> float | None:
        if self.fps is None or self.processing_seconds is None:
            return None
        if self.processing_seconds <= 0:
            return None
        return self.video_duration_sec * self.fps / self.processing_seconds


def _optional_metadata(detections: pd.DataFrame, column: str, numeric: bool = False):
    if column not in detections.columns:
        return None
    values = detections[column].dropna().unique()
    if len(values) == 0:
        return None
    if len(values) != 1:
        raise ValueError(f"Detection CSV contains inconsistent {column} metadata.")
    value = values[0]
    if numeric:
        converted = pd.to_numeric(pd.Series([value]), errors="raise").iloc[0]
        if not pd.notna(converted):
            return None
        return float(converted)
    text = str(value).strip()
    return text or None


def _format_time(seconds: float) -> str:
    minutes = int(seconds) // 60
    remaining_seconds = seconds - minutes * 60
    if remaining_seconds.is_integer():
        return f"{minutes}:{int(remaining_seconds):02d}"
    return f"{minutes}:{remaining_seconds:05.2f}"


def _load_csv(csv_path: str | Path) -> tuple[pd.DataFrame, str, float, str]:
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Detection CSV does not exist: {path}")

    detections = pd.read_csv(path, dtype={"track_id": "string", "class": "string"})
    missing_columns = REQUIRED_COLUMNS - set(detections.columns)
    if missing_columns:
        raise ValueError(f"Detection CSV is missing columns: {', '.join(sorted(missing_columns))}")
    if detections.empty:
        raise ValueError("Detection CSV contains no run details.")

    video_names = detections["video_name"].dropna().astype(str).unique()
    durations = pd.to_numeric(detections["video_duration_sec"], errors="raise").dropna().unique()
    processed_at_values = detections["processed_at"].dropna().astype(str).unique()
    if len(video_names) != 1 or len(durations) != 1 or len(processed_at_values) != 1:
        raise ValueError("Detection CSV must contain consistent video and run metadata.")

    duration = float(durations[0])
    if not pd.notna(duration) or duration <= 0:
        raise ValueError("Detection CSV contains an invalid video duration.")
    return detections, video_names[0], duration, processed_at_values[0]


def _build_timeline(
    detections: pd.DataFrame,
    duration_sec: float,
    bucket_seconds: int,
    classes: list[str],
) -> pd.DataFrame:
    columns = ("bucket_start_sec", "bucket_end_sec", "class", "count")
    if not classes:
        return pd.DataFrame(columns=columns)

    bucket_count = ceil(duration_sec / bucket_seconds)
    bucket_starts = [index * bucket_seconds for index in range(bucket_count)]
    timeline = pd.MultiIndex.from_product(
        (bucket_starts, classes),
        names=("bucket_start_sec", "class"),
    ).to_frame(index=False)
    timeline["count"] = 0

    if not detections.empty:
        first_seen = pd.to_numeric(detections["first_seen_sec"], errors="raise")
        if first_seen.isna().any() or (first_seen < 0).any() or (first_seen > duration_sec).any():
            raise ValueError("Detection CSV contains an invalid first-seen timestamp.")
        events = detections[["class", "track_id"]].copy()
        events["first_seen_sec"] = first_seen
        events = events.groupby(["class", "track_id"], as_index=False)["first_seen_sec"].min()
        events["bucket_start_sec"] = (
            (events["first_seen_sec"] // bucket_seconds).astype(int) * bucket_seconds
        ).clip(upper=(bucket_count - 1) * bucket_seconds)
        counts_by_bucket = (
            events.groupby(["bucket_start_sec", "class"])["track_id"]
            .nunique()
            .rename("count")
            .reset_index()
        )
        timeline = timeline.drop(columns="count").merge(
            counts_by_bucket,
            on=["bucket_start_sec", "class"],
            how="left",
        )
        timeline["count"] = timeline["count"].fillna(0).astype(int)

    timeline["bucket_end_sec"] = (
        timeline["bucket_start_sec"] + bucket_seconds
    ).clip(upper=duration_sec)
    return timeline.loc[:, columns].sort_values(
        ["bucket_start_sec", "class"],
        ignore_index=True,
    )


def _build_visible_timeline(
    detections: pd.DataFrame,
    duration_sec: float,
    bucket_seconds: int,
    classes: list[str],
) -> pd.DataFrame:
    columns = ("bucket_start_sec", "bucket_end_sec", "class", "count")
    if not classes:
        return pd.DataFrame(columns=columns)

    bucket_count = ceil(duration_sec / bucket_seconds)
    bucket_starts = [index * bucket_seconds for index in range(bucket_count)]
    timeline = pd.MultiIndex.from_product(
        (bucket_starts, classes),
        names=("bucket_start_sec", "class"),
    ).to_frame(index=False)
    timeline["count"] = 0

    if not detections.empty:
        first_seen = pd.to_numeric(detections["first_seen_sec"], errors="raise")
        last_seen = pd.to_numeric(detections["last_seen_sec"], errors="raise")
        if (
            first_seen.isna().any()
            or last_seen.isna().any()
            or (first_seen < 0).any()
            or (last_seen < first_seen).any()
            or (last_seen > duration_sec).any()
        ):
            raise ValueError("Detection CSV contains an invalid object visibility interval.")
        intervals = detections[["class", "track_id"]].copy()
        intervals["first_seen_sec"] = first_seen
        intervals["last_seen_sec"] = last_seen
        intervals = intervals.groupby(
            ["class", "track_id"],
            as_index=False,
        ).agg(
            first_seen_sec=("first_seen_sec", "min"),
            last_seen_sec=("last_seen_sec", "max"),
        )
        active = []
        for bucket_start in bucket_starts:
            bucket_end = min(bucket_start + bucket_seconds, duration_sec)
            active_tracks = intervals.loc[
                (intervals["first_seen_sec"] < bucket_end)
                & (intervals["last_seen_sec"] >= bucket_start)
            ]
            if not active_tracks.empty:
                by_class = active_tracks.groupby("class")["track_id"].nunique()
                active.extend(
                    (bucket_start, class_name, int(count))
                    for class_name, count in by_class.items()
                )
        if active:
            active_counts = pd.DataFrame(
                active,
                columns=("bucket_start_sec", "class", "count"),
            )
            timeline = timeline.drop(columns="count").merge(
                active_counts,
                on=["bucket_start_sec", "class"],
                how="left",
            )
            timeline["count"] = timeline["count"].fillna(0).astype(int)

    timeline["bucket_end_sec"] = (
        timeline["bucket_start_sec"] + bucket_seconds
    ).clip(upper=duration_sec)
    return timeline.loc[:, columns].sort_values(
        ["bucket_start_sec", "class"],
        ignore_index=True,
    )


def _build_summary(
    video_name: str,
    duration_sec: float,
    counts: pd.DataFrame,
    timeline: pd.DataFrame,
) -> str:
    duration = _format_time(duration_sec)
    if counts.empty:
        return (
            f"No objects were detected in {video_name} ({duration}). "
            "Counts are approximate because tracking can split or merge object IDs."
        )

    total = int(counts["count"].sum())
    highest_count = int(counts["count"].max())
    common_classes = counts.loc[counts["count"] == highest_count, "class"].tolist()
    if len(common_classes) == 1:
        most_common = f"Most common class: {common_classes[0]} ({highest_count})."
    else:
        most_common = f"Most common classes: {', '.join(common_classes)} ({highest_count} each)."

    bucket_totals = timeline.groupby(
        ["bucket_start_sec", "bucket_end_sec"],
        as_index=False,
    )["count"].sum()
    busiest = bucket_totals.loc[bucket_totals["count"].idxmax()]
    busiest_window = (
        f"Busiest time window: {_format_time(float(busiest['bucket_start_sec']))}"
        f"-{_format_time(float(busiest['bucket_end_sec']))} "
        f"({int(busiest['count'])} first-seen objects)."
    )
    return (
        f"{total} unique tracked object(s) were detected in {video_name} "
        f"({duration}). {most_common} {busiest_window} "
        "Counts are approximate because tracking can split or merge object IDs."
    )


def analyze_csv(
    csv_path: str | Path,
    bucket_seconds: int = TIMELINE_BUCKET_SECONDS,
) -> AnalysisResult:
    """Build all analysis and chart data from a run's detections CSV."""
    if bucket_seconds <= 0:
        raise ValueError("Timeline bucket size must be a positive number of seconds.")

    detections, video_name, duration_sec, processed_at = _load_csv(csv_path)
    is_placeholder = detections["class"].eq("__none__")
    valid = detections.loc[~is_placeholder].copy()
    if (
        valid["class"].isna().any()
        or valid["track_id"].isna().any()
        or valid["track_id"].str.strip().eq("").any()
    ):
        raise ValueError("Detection CSV contains a tracked object with a missing class or track ID.")
    valid["class"] = valid["class"].astype(str)
    if valid["class"].str.strip().eq("").any():
        raise ValueError("Detection CSV contains an empty class for a tracked object.")

    distinct_tracks = valid.drop_duplicates(["class", "track_id"])
    counts = (
        distinct_tracks.groupby("class")["track_id"]
        .nunique()
        .rename("count")
        .reset_index()
        .sort_values(["count", "class"], ascending=[False, True], ignore_index=True)
    )
    classes = sorted(counts["class"].tolist())
    timeline = _build_timeline(valid, duration_sec, bucket_seconds, classes)
    visible_timeline = _build_visible_timeline(
        valid,
        duration_sec,
        bucket_seconds,
        classes,
    )
    summary = _build_summary(video_name, duration_sec, counts, timeline)
    metadata = {
        "fps": _optional_metadata(detections, "fps", numeric=True),
        "model": _optional_metadata(detections, "model"),
        "confidence": _optional_metadata(detections, "confidence", numeric=True),
        "imgsz": _optional_metadata(detections, "imgsz", numeric=True),
        "min_track_frames": _optional_metadata(detections, "min_track_frames", numeric=True),
        "min_box_px": _optional_metadata(detections, "min_box_px", numeric=True),
        "processing_seconds": _optional_metadata(detections, "processing_seconds", numeric=True),
        "device": _optional_metadata(detections, "device"),
        "location": _optional_metadata(detections, "location"),
        "confidence_overrides": _optional_metadata(detections, "confidence_overrides"),
        "track_buffer": _optional_metadata(detections, "track_buffer", numeric=True),
        "max_inference_width": _optional_metadata(
            detections,
            "max_inference_width",
            numeric=True,
        ),
        "half_precision": _optional_metadata(detections, "half_precision"),
        "min_snapshot_size_px": _optional_metadata(
            detections,
            "min_snapshot_size_px",
            numeric=True,
        ),
        "snapshot_padding_px": _optional_metadata(
            detections,
            "snapshot_padding_px",
            numeric=True,
        ),
    }
    for field in (
        "imgsz",
        "min_track_frames",
        "min_box_px",
        "track_buffer",
        "max_inference_width",
        "min_snapshot_size_px",
        "snapshot_padding_px",
    ):
        if metadata[field] is not None:
            metadata[field] = int(metadata[field])
    if metadata["half_precision"] is not None:
        metadata["half_precision"] = metadata["half_precision"].casefold() == "true"
    return AnalysisResult(
        video_name=video_name,
        video_duration_sec=duration_sec,
        processed_at=processed_at,
        counts=counts,
        timeline=timeline,
        visible_timeline=visible_timeline,
        summary=summary,
        **metadata,
    )
