from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from core.analysis import analyze_csv
from core.config import (
    CONFIDENCE_THRESHOLD,
    IMAGE_SIZE,
    MIN_BOX_PX,
    MIN_TRACK_FRAMES,
    OUTPUTS_DIR,
    TRACKER_CONFIG_PATH,
)


def load_manual_counts(path: str | Path) -> dict[str, dict[str, int]]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read manual counts JSON: {error}") from error
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Manual counts must be a non-empty JSON object keyed by video filename.")
    normalized: dict[str, dict[str, int]] = {}
    for clip, counts in payload.items():
        if not isinstance(clip, str) or not clip.strip() or not isinstance(counts, dict):
            raise ValueError("Each manual-count entry must map a video filename to class counts.")
        normalized[clip] = {}
        for class_name, count in counts.items():
            if (
                not isinstance(class_name, str)
                or not class_name.strip()
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
            ):
                raise ValueError("Manual class counts must be non-negative integers.")
            normalized[clip][class_name] = count
    return normalized


def comparison_rows(
    clip: str,
    manual_counts: dict[str, int],
    app_counts: dict[str, int],
    *,
    variant: str = "recorded run",
    run_dir: str = "",
) -> list[dict[str, Any]]:
    rows = []
    for class_name in sorted(set(manual_counts) | set(app_counts), key=str.casefold):
        manual = manual_counts.get(class_name, 0)
        app = app_counts.get(class_name, 0)
        difference = abs(app - manual)
        percentage = (difference / manual * 100) if manual else (0.0 if difference == 0 else None)
        rows.append(
            {
                "clip": clip,
                "class": class_name,
                "manual_count": manual,
                "app_count": app,
                "absolute_difference": difference,
                "percentage_difference": percentage,
                "variant": variant,
                "run_dir": run_dir,
            }
        )
    return rows


def _counts_for_csv(csv_path: Path) -> dict[str, int]:
    analysis = analyze_csv(csv_path)
    return {
        str(row["class"]): int(row["count"])
        for row in analysis.counts.to_dict("records")
    }


def _write_tracker_variant(source_path: Path, destination: Path, track_buffer: int) -> Path:
    with source_path.open(encoding="utf-8") as tracker_file:
        settings = yaml.safe_load(tracker_file)
    if not isinstance(settings, dict) or "track_buffer" not in settings:
        raise ValueError(f"Tracker config is missing track_buffer: {source_path}")
    settings["track_buffer"] = track_buffer
    destination.write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
    return destination


def _evaluate_video(
    video_path: Path,
    manual_counts: dict[str, int],
    *,
    sweep: bool,
) -> list[dict[str, Any]]:
    from core.detector import run_detection

    selected_classes = list(manual_counts)
    if not selected_classes:
        raise ValueError(f"No manual classes were supplied for {video_path.name}.")

    if not sweep:
        run_dir = run_detection(video_path, selected_classes=selected_classes)
        return comparison_rows(
            video_path.name,
            manual_counts,
            _counts_for_csv(run_dir / "detections.csv"),
            run_dir=str(run_dir),
        )

    default_buffer = int(
        yaml.safe_load(TRACKER_CONFIG_PATH.read_text(encoding="utf-8"))["track_buffer"]
    )
    variants = [
        ("baseline", CONFIDENCE_THRESHOLD, MIN_TRACK_FRAMES, MIN_BOX_PX, default_buffer),
        ("min-track-10", CONFIDENCE_THRESHOLD, 10, MIN_BOX_PX, default_buffer),
        ("min-track-15", CONFIDENCE_THRESHOLD, 15, MIN_BOX_PX, default_buffer),
        ("confidence-0.45", 0.45, MIN_TRACK_FRAMES, MIN_BOX_PX, default_buffer),
        ("confidence-0.55", 0.55, MIN_TRACK_FRAMES, MIN_BOX_PX, default_buffer),
        ("min-box-12", CONFIDENCE_THRESHOLD, MIN_TRACK_FRAMES, 12, default_buffer),
        ("min-box-20", CONFIDENCE_THRESHOLD, MIN_TRACK_FRAMES, 20, default_buffer),
        ("track-buffer-15", CONFIDENCE_THRESHOLD, MIN_TRACK_FRAMES, MIN_BOX_PX, 15),
        ("track-buffer-60", CONFIDENCE_THRESHOLD, MIN_TRACK_FRAMES, MIN_BOX_PX, 60),
    ]
    rows = []
    with tempfile.TemporaryDirectory(prefix="drishti-eval-") as temporary:
        tracker_dir = Path(temporary)
        for name, confidence, min_frames, min_box, buffer in variants:
            tracker_path = _write_tracker_variant(
                TRACKER_CONFIG_PATH,
                tracker_dir / f"{name}.yaml",
                buffer,
            )
            run_dir = run_detection(
                video_path,
                selected_classes=selected_classes,
                confidence_threshold=confidence,
                min_track_frames=min_frames,
                min_box_px=min_box,
                tracker_config=tracker_path,
            )
            rows.extend(
                comparison_rows(
                    video_path.name,
                    manual_counts,
                    _counts_for_csv(run_dir / "detections.csv"),
                    variant=name,
                    run_dir=str(run_dir),
                )
            )
    return rows


def evaluate(
    manual_counts: dict[str, dict[str, int]],
    inputs: list[Path],
    *,
    sweep: bool = False,
    output_dir: Path = OUTPUTS_DIR,
) -> tuple[pd.DataFrame, Path]:
    if sweep and (
        len(inputs) != 1
        or not inputs[0].is_file()
        or inputs[0].suffix.casefold() not in {".mp4", ".avi", ".mov"}
    ):
        raise ValueError("--sweep requires exactly one MP4, AVI, or MOV video input.")
    rows: list[dict[str, Any]] = []
    for item in inputs:
        if item.is_dir():
            csv_path = item / "detections.csv"
        elif item.suffix.casefold() == ".csv":
            csv_path = item
        else:
            clip_manual = manual_counts.get(item.name)
            if clip_manual is None:
                raise ValueError(f"No manual counts found for video filename: {item.name}")
            rows.extend(_evaluate_video(item, clip_manual, sweep=sweep))
            continue
        if not csv_path.is_file():
            raise FileNotFoundError(f"Run folder has no detections.csv: {item}")
        analysis = analyze_csv(csv_path)
        clip_manual = manual_counts.get(analysis.video_name)
        if clip_manual is None:
            raise ValueError(
                f"No manual counts found for video filename: {analysis.video_name}"
            )
        rows.extend(
            comparison_rows(
                analysis.video_name,
                clip_manual,
                _counts_for_csv(csv_path),
                run_dir=str(csv_path.parent),
            )
        )
    if not rows:
        raise ValueError("No videos or run folders were evaluated.")
    results = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_path = output_dir / f"evaluation_{timestamp}.csv"
    results.to_csv(output_path, index=False)
    return results, output_path


def _format_table(results: pd.DataFrame) -> str:
    printable = results.copy()
    printable["percentage_difference"] = printable["percentage_difference"].map(
        lambda value: "N/A" if pd.isna(value) else f"{value:.1f}%"
    )
    return printable[
        [
            "clip",
            "class",
            "manual_count",
            "app_count",
            "absolute_difference",
            "percentage_difference",
            "variant",
        ]
    ].to_string(index=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare detected unique-track counts against your manual counts."
    )
    parser.add_argument("manual_json", type=Path, help="JSON mapping clip names to manual class counts.")
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Run folders, detections.csv files, or videos to process.",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run a small one-factor-at-a-time parameter sweep on video inputs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUTS_DIR,
        help="Directory for the evaluation CSV (default: project outputs).",
    )
    args = parser.parse_args()
    try:
        manual = load_manual_counts(args.manual_json)
        results, output_path = evaluate(
            manual,
            args.inputs,
            sweep=args.sweep,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Evaluation failed: {error}", file=sys.stderr)
        return 1
    print(_format_table(results))
    print(f"\nSaved manual-count comparison to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
