from __future__ import annotations

import shutil
from pathlib import Path
from hashlib import sha1
from fastapi import APIRouter, HTTPException

import pandas as pd
from core.analysis import AnalysisResult, analyze_csv
from core.config import OUTPUTS_DIR
from api.schemas import (
    CountItem,
    RunDetailResponse,
    RunSummaryResponse,
    SnapshotItem,
    TimelineItem,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])

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


def _demo_city_for_run(run_dir: Path) -> str:
    seed = int.from_bytes(sha1(run_dir.name.encode("utf-8")).digest()[:4], "big")
    return DEMO_CITY_NAMES[seed % len(DEMO_CITY_NAMES)]


def _read_snapshots(csv_path: Path) -> list[SnapshotItem]:
    if not csv_path.is_file():
        return []
    try:
        df = pd.read_csv(csv_path, dtype={"track_id": "string", "class": "string"})
    except Exception:
        return []
    valid = df.loc[df["class"].notna() & df["class"].ne("__none__")]
    snapshots: list[SnapshotItem] = []
    run_dir = csv_path.parent
    for _, row in valid.iterrows():
        rel_snap = str(row.get("snapshot_path", "") or "")
        snap_path = None
        if rel_snap.strip():
            candidate = (run_dir / rel_snap).resolve()
            if candidate.is_file():
                snap_path = rel_snap.replace("\\", "/")

        first_seen = float(row.get("first_seen_sec", 0.0) or 0.0)
        last_seen = float(row.get("last_seen_sec", first_seen) or first_seen)
        conf_val = row.get("avg_confidence")
        avg_conf = float(conf_val) if pd.notna(conf_val) else None

        snapshots.append(
            SnapshotItem(
                track_id=str(row["track_id"]),
                class_name=str(row["class"]),
                first_seen_sec=round(first_seen, 2),
                last_seen_sec=round(last_seen, 2),
                avg_confidence=round(avg_conf, 3) if avg_conf is not None else None,
                path=snap_path,
            )
        )
    return sorted(
        snapshots,
        key=lambda s: (s.avg_confidence is None, -(s.avg_confidence or 0), s.class_name, s.track_id),
    )


@router.get("", response_model=list[RunSummaryResponse])
def list_runs() -> list[RunSummaryResponse]:
    summaries: list[RunSummaryResponse] = []
    if not OUTPUTS_DIR.is_dir():
        return summaries

    for run_dir in sorted(OUTPUTS_DIR.glob("run_*"), key=lambda d: d.name, reverse=True):
        csv_path = run_dir / "detections.csv"
        if not csv_path.is_file():
            continue
        try:
            analysis = analyze_csv(csv_path)
            total = int(analysis.counts["count"].sum()) if not analysis.counts.empty else 0
            classes = analysis.counts["class"].astype(str).tolist() if not analysis.counts.empty else []
            summaries.append(
                RunSummaryResponse(
                    id=run_dir.name,
                    video_name=analysis.video_name,
                    processed_at=analysis.processed_at,
                    duration_sec=round(analysis.video_duration_sec, 2),
                    total_objects=total,
                    classes=classes,
                    location=analysis.location or _demo_city_for_run(run_dir),
                    has_annotated_video=(run_dir / "annotated.mp4").is_file(),
                    has_brief=(run_dir / "brief.pdf").is_file(),
                )
            )
        except Exception:
            continue
    return summaries


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str) -> RunDetailResponse:
    run_dir = OUTPUTS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    csv_path = run_dir / "detections.csv"
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail=f"Detections CSV missing for run: {run_id}")

    try:
        analysis = analyze_csv(csv_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing run CSV: {e}")

    counts = [
        CountItem(class_name=str(row["class"]), count=int(row["count"]))
        for _, row in analysis.counts.iterrows()
    ]

    timeline = [
        TimelineItem(
            bucket_start_sec=float(row["bucket_start_sec"]),
            bucket_end_sec=float(row["bucket_end_sec"]),
            class_name=str(row["class"]),
            count=int(row["count"]),
        )
        for _, row in analysis.timeline.iterrows()
    ]

    visible_timeline = [
        TimelineItem(
            bucket_start_sec=float(row["bucket_start_sec"]),
            bucket_end_sec=float(row["bucket_end_sec"]),
            class_name=str(row["class"]),
            count=int(row["count"]),
        )
        for _, row in analysis.visible_timeline.iterrows()
    ]

    snapshots = _read_snapshots(csv_path)

    return RunDetailResponse(
        id=run_dir.name,
        video_name=analysis.video_name,
        processed_at=analysis.processed_at,
        duration_sec=round(analysis.video_duration_sec, 2),
        summary=analysis.summary,
        counts=counts,
        timeline=timeline,
        visible_timeline=visible_timeline,
        fps=analysis.fps,
        processing_fps=round(analysis.processing_fps, 2) if analysis.processing_fps else None,
        model=analysis.model,
        confidence=analysis.confidence,
        imgsz=analysis.imgsz,
        min_track_frames=analysis.min_track_frames,
        min_box_px=analysis.min_box_px,
        processing_seconds=round(analysis.processing_seconds, 2) if analysis.processing_seconds else None,
        device=analysis.device,
        location=analysis.location or _demo_city_for_run(run_dir),
        confidence_overrides=analysis.confidence_overrides,
        snapshots=snapshots,
        has_annotated_video=(run_dir / "annotated.mp4").is_file(),
        has_brief=(run_dir / "brief.pdf").is_file(),
    )


@router.delete("/{run_id}")
def delete_run(run_id: str) -> dict[str, str]:
    run_dir = OUTPUTS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    try:
        shutil.rmtree(run_dir)
        return {"status": "deleted", "id": run_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete run: {e}")
