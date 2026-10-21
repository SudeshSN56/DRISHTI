import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from streamlit.testing.v1 import AppTest

from core.config import DEFAULT_CLASSES


class FakeClassModel:
    names = {2: "car", 7: "person"}

    def __init__(self, _model_name):
        pass


class AppTests(unittest.TestCase):
    def test_corrupt_upload_shows_error_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            import streamlit as st

            st.cache_data.clear()
            with (
                patch("core.config.OUTPUTS_DIR", Path(temporary_directory)),
                patch("ultralytics.YOLO", FakeClassModel),
            ):
                app = AppTest.from_file(
                    str(Path(__file__).resolve().parent.parent / "app.py"),
                    default_timeout=120,
                ).run()
                app.get("file_uploader")[0].set_value(
                    ("corrupt.mp4", b"not a valid video", "video/mp4")
                )
                app.run()
                app.get("button")[0].click()
                app.run()

            self.assertFalse(app.exception, app.exception)
            self.assertTrue(
                any(
                    "Could not process this video" in error.value
                    for error in app.get("error")
                )
            )

    def test_editing_classes_in_ui_changes_detection_selection_and_results(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "outputs"
            output_root.mkdir()
            video_path = root / "upload.mp4"
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                5.0,
                (64, 48),
            )
            self.assertTrue(writer.isOpened())
            writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
            writer.release()

            selected_classes = []

            def fake_run_detection(video, classes, progress_callback=None):
                selected_classes.extend(classes)
                run_dir = output_root / "run_20261021_000000"
                run_dir.mkdir()
                with (run_dir / "detections.csv").open(
                    "w",
                    newline="",
                    encoding="utf-8",
                ) as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(
                        (
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
                        )
                    )
                    writer.writerow(
                        (
                            Path(video).name,
                            0.2,
                            5.0,
                            "2026-10-21T00:00:00+00:00",
                            44,
                            classes[0],
                            0,
                            0,
                            0.9,
                            "",
                        )
                    )
                return run_dir

            import streamlit as st

            st.cache_data.clear()
            with (
                patch("core.config.OUTPUTS_DIR", output_root),
                patch("core.detector.run_detection", side_effect=fake_run_detection),
                patch("ultralytics.YOLO", FakeClassModel),
            ):
                app = AppTest.from_file(
                    str(Path(__file__).resolve().parent.parent / "app.py"),
                    default_timeout=120,
                ).run()
                self.assertFalse(app.exception, app.exception)
                self.assertTrue(set(DEFAULT_CLASSES).issuperset({"person", "car"}))

                app.get("multiselect")[0].set_value(["car"])
                app.get("file_uploader")[0].set_value(
                    ("upload.mp4", video_path.read_bytes(), "video/mp4")
                )
                app.run()
                app.get("button")[0].click()
                app.run()

            self.assertFalse(app.exception, app.exception)
            self.assertEqual(selected_classes, ["car"])
            self.assertIn("1 unique tracked object(s)", app.get("info")[0].value)
            self.assertTrue(
                any(
                    header.value == "Results: upload.mp4"
                    for header in app.get("header")
                )
            )


if __name__ == "__main__":
    unittest.main()
