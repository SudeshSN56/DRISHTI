"""Batch process all surveillance video clips in test_videos/ through DRISHTI detector."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from core.config import DEFAULT_CLASSES, OUTPUTS_DIR, TEST_VIDEOS_DIR
from core.detector import run_detection
from core.analysis import analyze_csv
from core.report import build_brief


def batch_process_all():
    videos = sorted(TEST_VIDEOS_DIR.glob("*.mp4"))
    if not videos:
        print("No MP4 videos found in test_videos/", file=sys.stderr)
        return

    print(f"=== DRISHTI BATCH SURVEILLANCE PROCESSING ===")
    print(f"Found {len(videos)} video clips to process in {TEST_VIDEOS_DIR}")
    print(f"Target classes: {', '.join(DEFAULT_CLASSES[:7])}...")
    print("==============================================\n")

    overall_start = time.perf_counter()
    results = []

    for idx, video_path in enumerate(videos, 1):
        print(f"[{idx}/{len(videos)}] Processing: {video_path.name}...")
        start_t = time.perf_counter()

        def progress(processed: int, total: int):
            if processed % 50 == 0 or processed == total:
                pct = (processed / total) * 100
                print(f"  --> Frame {processed}/{total} ({pct:.0f}%)", flush=True)

        try:
            run_dir = run_detection(
                video_path=video_path,
                selected_classes=DEFAULT_CLASSES,
                progress_callback=progress,
            )
            elapsed = time.perf_counter() - start_t
            csv_path = run_dir / "detections.csv"

            # Run CSV analysis
            analysis = analyze_csv(csv_path)
            total_objects = int(analysis.counts["count"].sum()) if not analysis.counts.empty else 0

            # Build PDF mission brief
            pdf_path = build_brief(csv_path)

            print(f"  [COMPLETED] Run: {run_dir.name}")
            print(f"  Elapsed: {elapsed:.1f}s | Speed: {analysis.processing_fps:.1f} FPS" if analysis.processing_fps else f"  Elapsed: {elapsed:.1f}s")
            print(f"  Unique objects tracked: {total_objects}")
            print(f"  PDF Brief: {pdf_path.name}\n")

            results.append({
                "video": video_path.name,
                "run": run_dir.name,
                "objects": total_objects,
                "elapsed": round(elapsed, 1),
                "fps": round(analysis.processing_fps, 1) if analysis.processing_fps else None,
            })
        except Exception as e:
            print(f"  [ERROR] Failed to process {video_path.name}: {e}\n", file=sys.stderr)

    total_time = time.perf_counter() - overall_start
    print("==============================================")
    print(f"Batch processing finished in {total_time:.1f}s!")
    print(f"Successfully processed {len(results)} of {len(videos)} clips.")
    for r in results:
        print(f" - {r['video']}: {r['objects']} objects tracked (Run: {r['run']})")
    print("==============================================")


if __name__ == "__main__":
    batch_process_all()
