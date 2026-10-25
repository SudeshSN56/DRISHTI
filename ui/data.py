from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha1
from pathlib import Path

import pandas as pd

from core.analysis import AnalysisResult, analyze_csv
from core.config import DATASETS_DIR, OUTPUTS_DIR


DEMO_CITY_NAMES = (
    "Bengaluru",
    "Chennai",
    "Delhi",
    "Hyderabad",
    "Kolkata",
    "Mumbai",
    "Pune",
    "Ahmedabad",
    "Jaipur",
    "Surat",
)


def _demo_city_for_run(run_dir: Path) -> str | None:
    seed = int.from_bytes(sha1(run_dir.name.encode("utf-8")).digest()[:4], "big")
    return DEMO_CITY_NAMES[seed % len(DEMO_CITY_NAMES)]


@dataclass(frozen=True)
class RunInfo:
    path: Path
    video_name: str
    processed_at: str
    duration_sec: float
    total_objects: int
    class_names: tuple[str, ...]
    location: str | None = None


@dataclass(frozen=True)
class DatasetVideo:
    path: Path
    name: str
    dataset_name: str
    frame_count: int
    demo_city: str


@dataclass(frozen=True)
class ObjectInfo:
    track_id: str
    class_name: str
    first_seen_sec: float
    last_seen_sec: float
    avg_confidence: float | None
    snapshot_path: Path | None


def available_runs(outputs_dir: Path = OUTPUTS_DIR) -> list[Path]:
    return sorted(
        (
            run_dir
            for run_dir in outputs_dir.glob("run_*")
            if (run_dir / "detections.csv").is_file()
        ),
        key=lambda run_dir: run_dir.name,
        reverse=True,
    )


def available_dataset_videos(datasets_dir: Path = DATASETS_DIR) -> list[DatasetVideo]:
    if not datasets_dir.is_dir():
        return []

    videos: list[DatasetVideo] = []
    for dataset_dir in sorted(
        (path for path in datasets_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    ):
        sequence_roots = [
            path
            for path in (dataset_dir / "sequences", *dataset_dir.glob("*/sequences"))
            if path.is_dir()
        ]
        for sequence_root in sequence_roots:
            for sequence_dir in sorted(
                (path for path in sequence_root.iterdir() if path.is_dir()),
                key=lambda path: path.name.casefold(),
            ):
                frame_count = sum(
                    1
                    for path in sequence_dir.iterdir()
                    if path.is_file() and path.suffix.casefold() in {".jpg", ".jpeg"}
                )
                if frame_count:
                    city_seed = int.from_bytes(
                        sha1(sequence_dir.name.encode("utf-8")).digest()[:4],
                        "big",
                    )
                    videos.append(
                        DatasetVideo(
                            path=sequence_dir,
                            name=sequence_dir.name,
                            dataset_name=dataset_dir.name,
                            frame_count=frame_count,
                            demo_city=DEMO_CITY_NAMES[city_seed % len(DEMO_CITY_NAMES)],
                        )
                    )
    return sorted(videos, key=lambda video: (video.dataset_name.casefold(), video.name.casefold()))


def run_info(run_dir: Path) -> RunInfo:
    analysis: AnalysisResult = analyze_csv(run_dir / "detections.csv")
    total = int(analysis.counts["count"].sum()) if not analysis.counts.empty else 0
    fallback_location = analysis.location or _demo_city_for_run(run_dir)
    return RunInfo(
        path=run_dir,
        video_name=analysis.video_name,
        processed_at=analysis.processed_at,
        duration_sec=analysis.video_duration_sec,
        total_objects=total,
        class_names=tuple(analysis.counts["class"].astype(str).tolist()),
        location=fallback_location,
    )


def read_objects(csv_path: Path) -> list[ObjectInfo]:
    rows = pd.read_csv(csv_path, dtype={"track_id": "string", "class": "string"})
    required = {
        "track_id",
        "class",
        "first_seen_sec",
        "last_seen_sec",
        "avg_confidence",
        "snapshot_path",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Detection CSV is missing columns: {', '.join(sorted(missing))}")
    rows = rows.loc[rows["class"].notna() & rows["class"].ne("__none__")]
    objects: list[ObjectInfo] = []
    run_dir = csv_path.parent.resolve()
    for row in rows.to_dict("records"):
        class_name = str(row["class"])
        if not class_name.strip() or pd.isna(row["track_id"]) or not str(row["track_id"]).strip():
            raise ValueError("Detection CSV contains a tracked object with a missing class or track ID.")
        first_seen = pd.to_numeric(pd.Series([row["first_seen_sec"]]), errors="raise").iloc[0]
        last_seen = pd.to_numeric(pd.Series([row["last_seen_sec"]]), errors="raise").iloc[0]
        if pd.isna(first_seen) or pd.isna(last_seen) or first_seen < 0 or last_seen < first_seen:
            raise ValueError("Detection CSV contains invalid object timestamps.")
        confidence_value = pd.to_numeric(
            pd.Series([row["avg_confidence"]]), errors="coerce"
        ).iloc[0]
        relative_snapshot = row["snapshot_path"]
        snapshot_path = None
        if isinstance(relative_snapshot, str) and relative_snapshot.strip():
            resolved = (run_dir / relative_snapshot).resolve()
            try:
                resolved.relative_to(run_dir)
            except ValueError as error:
                raise ValueError("A snapshot path in the CSV points outside its run folder.") from error
            if resolved.is_file():
                snapshot_path = resolved
        objects.append(
            ObjectInfo(
                track_id=str(row["track_id"]),
                class_name=class_name,
                first_seen_sec=float(first_seen),
                last_seen_sec=float(last_seen),
                avg_confidence=(
                    float(confidence_value) if not pd.isna(confidence_value) else None
                ),
                snapshot_path=snapshot_path,
            )
        )
    return sorted(objects, key=lambda item: (item.first_seen_sec, item.class_name, item.track_id))


def sort_objects_by_confidence(objects: list[ObjectInfo]) -> list[ObjectInfo]:
    return sorted(
        objects,
        key=lambda item: (
            item.avg_confidence is None,
            -(item.avg_confidence if item.avg_confidence is not None else 0),
            item.class_name.casefold(),
            item.track_id,
        ),
    )


def filter_runs(
    runs: list[RunInfo],
    *,
    video_query: str = "",
    class_name: str = "",
    min_objects: int = 0,
    after: date | None = None,
    before: date | None = None,
    sort_by: str = "newest",
) -> list[RunInfo]:
    query = video_query.strip().casefold()
    filtered = [
        run
        for run in runs
        if (
            not query
            or query in run.video_name.casefold()
            or (run.location and query in run.location.casefold())
        )
        and (not class_name or class_name in run.class_names)
        and run.total_objects >= min_objects
        and (after is None or run.processed_at[:10] >= after.isoformat())
        and (before is None or run.processed_at[:10] <= before.isoformat())
    ]
    if sort_by == "most objects":
        return sorted(filtered, key=lambda run: (-run.total_objects, run.path.name))
    if sort_by == "longest video":
        return sorted(filtered, key=lambda run: (-run.duration_sec, run.path.name))
    return sorted(filtered, key=lambda run: run.path.name, reverse=True)
