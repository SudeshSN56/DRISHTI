import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from core.analysis import analyze_csv
from core.detector import run_detection
from core.report import build_brief
from core.video_source import VideoSource, VideoSourceError
from tools.frames_to_video import stitch_sequence


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def cpu(self):
        return self

    def int(self):
        return self

    def tolist(self):
        return self.values


class FakeBoxes:
    def __init__(self, detections):
        self.id = FakeTensor([item[0] for item in detections])
        self.xyxy = FakeTensor([item[1] for item in detections])
        self.cls = FakeTensor([item[2] for item in detections])
        self.conf = FakeTensor([item[3] for item in detections])


class FakeResult:
    def __init__(self, frame, detections):
        self.boxes = FakeBoxes(detections) if detections else None
        self.frame = frame

    def plot(self):
        return self.frame.copy()


class FakeYOLO:
    names = {3: "car", 8: "person"}
    detections = []
    track_kwargs = []

    def __init__(self, _model_name):
        self.frame_index = 0

    def track(self, frame, **kwargs):
        type(self).track_kwargs.append(kwargs)
        detections = type(self).detections[self.frame_index]
        self.frame_index += 1
        return [FakeResult(frame, detections)]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        FakeYOLO.track_kwargs = []

    def tearDown(self):
        self.temp_directory.cleanup()

    def make_video(self, name, frame_count, fps=5.0, size=(160, 120)):
        path = self.root / name
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            size,
        )
        self.assertTrue(writer.isOpened())
        for index in range(frame_count):
            frame = np.full(
                (size[1], size[0], 3),
                fill_value=index % 255,
                dtype=np.uint8,
            )
            writer.write(frame)
        writer.release()
        return path

    @staticmethod
    def detection(track_id, class_id=3, confidence=0.8):
        return (track_id, [20, 15, 80, 90], class_id, confidence)

    def run_with_fake_model(
        self,
        video_path,
        classes,
        output_root,
        preview_callback=None,
        preview_max_width=640,
    ):
        with (
            patch("core.detector.torch.cuda.is_available", return_value=True),
            patch("core.detector.torch.cuda.get_device_name", return_value="Test CUDA"),
            patch("core.detector.YOLO", FakeYOLO),
        ):
            return run_detection(
                video_path,
                selected_classes=classes,
                output_root=output_root,
                preview_callback=preview_callback,
                preview_max_width=preview_max_width,
                model_name="fake.pt",
            )

    def test_video_source_rejects_corrupt_video(self):
        corrupt_path = self.root / "corrupt.mp4"
        corrupt_path.write_bytes(b"not a video")
        with self.assertRaises(VideoSourceError):
            VideoSource(corrupt_path)

    def test_selected_class_tracks_write_csv_snapshot_and_playable_video(self):
        video_path = self.make_video("traffic.mp4", frame_count=7)
        FakeYOLO.detections = [
            [self.detection(11, confidence=confidence)]
            if frame_index < 6
            else [self.detection(22, confidence=0.99)]
            for frame_index, confidence in enumerate(
                (0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
            )
        ]
        FakeYOLO.detections.append([])

        previews = []
        run_dir = self.run_with_fake_model(
            video_path,
            ["car"],
            self.root / "runs",
            preview_callback=lambda frame, counts: previews.append((frame, counts)),
            preview_max_width=80,
        )
        self.assertEqual(len(previews), 3)
        self.assertEqual([counts for _, counts in previews], [{}, {"car": 1}, {"car": 1}])
        self.assertEqual(previews[0][0].shape, (60, 80, 3))
        self.assertEqual(previews[-1][0].dtype, np.uint8)
        with (run_dir / "detections.csv").open(
            encoding="utf-8",
            newline="",
        ) as csv_file:
            rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["video_name"], "traffic.mp4")
        self.assertEqual(rows[0]["track_id"], "11")
        self.assertEqual(rows[0]["class"], "car")
        self.assertEqual(rows[0]["avg_confidence"], "0.65")
        self.assertEqual(rows[0]["model"], "fake.pt")
        self.assertEqual(float(rows[0]["confidence"]), 0.35)
        self.assertEqual(int(rows[0]["imgsz"]), 960)
        self.assertEqual(int(rows[0]["min_track_frames"]), 5)
        self.assertEqual(int(rows[0]["min_box_px"]), 0)
        self.assertGreater(float(rows[0]["processing_seconds"]), 0)
        self.assertEqual(rows[0]["device"], "Test CUDA")
        snapshot = cv2.imread(str(run_dir / rows[0]["snapshot_path"]))
        self.assertIsNotNone(snapshot)
        capture = cv2.VideoCapture(str(video_path))
        for _ in range(6):
            readable, expected_frame = capture.read()
            self.assertTrue(readable)
        capture.release()
        expected_crop = expected_frame[15:90, 20:80]
        self.assertLess(
            abs(float(snapshot.mean()) - float(expected_crop.mean())),
            2,
            "Snapshot should come from the highest-confidence frame.",
        )
        self.assertTrue(all(call["classes"] == [3] for call in FakeYOLO.track_kwargs))

        capture = cv2.VideoCapture(str(run_dir / "annotated.mp4"))
        self.assertTrue(capture.isOpened())
        frame_count = 0
        while True:
            readable, _ = capture.read()
            if not readable:
                break
            frame_count += 1
        capture.release()
        self.assertEqual(frame_count, 7)

        analysis = analyze_csv(run_dir / "detections.csv")
        self.assertEqual(analysis.counts.to_dict("records"), [{"class": "car", "count": 1}])
        processing_seconds = float(rows[0]["processing_seconds"])
        source_frames = float(rows[0]["video_duration_sec"]) * float(rows[0]["fps"])
        self.assertAlmostEqual(
            analysis.processing_fps,
            source_frames / processing_seconds,
        )

    def test_frame_folder_stitches_naturally_sorted_frames_to_h264(self):
        sequence = self.root / "dataset" / "sequence_1"
        sequence.mkdir(parents=True)
        for frame_number, value in ((1, 10), (2, 80), (10, 180)):
            frame = np.full((48, 64, 3), value, dtype=np.uint8)
            self.assertTrue(
                cv2.imwrite(str(sequence / f"frame{frame_number:07d}.jpg"), frame)
            )
        (sequence / "annotations.txt").write_text("ignored", encoding="utf-8")

        output_path = stitch_sequence(sequence, self.root / "stitched" / "clip.mp4", fps=10)
        capture = cv2.VideoCapture(str(output_path))
        self.assertTrue(capture.isOpened())
        values = []
        while True:
            readable, frame = capture.read()
            if not readable:
                break
            values.append(float(frame.mean()))
        capture.release()

        self.assertEqual(len(values), 3)
        self.assertEqual(values, sorted(values))
        self.assertEqual(round(values[0]), 10)
        self.assertEqual(round(values[-1]), 180)

    def test_frame_stitcher_cli_scans_parent_and_limits_sequences(self):
        input_root = self.root / "dataset"
        for sequence_name in ("sequence10", "sequence2"):
            sequence_dir = input_root / sequence_name
            sequence_dir.mkdir(parents=True)
            frame = np.full((48, 64, 3), 40, dtype=np.uint8)
            self.assertTrue(cv2.imwrite(str(sequence_dir / "0000001.jpg"), frame))

        output_dir = self.root / "clips"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.frames_to_video",
                str(input_root),
                "--output",
                str(output_dir),
                "--limit",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output_dir / "sequence2.mp4").is_file(), result.stdout)
        self.assertFalse((output_dir / "sequence10.mp4").exists())

    def test_preview_configuration_is_validated(self):
        video_path = self.make_video("preview.mp4", frame_count=1)
        with patch("core.detector.torch.cuda.is_available", return_value=True):
            with self.assertRaisesRegex(ValueError, "interval"):
                run_detection(
                    video_path,
                    ["person"],
                    preview_every_n_frames=0,
                    output_root=self.root / "invalid_interval",
                    model_name="unused.pt",
                )

    def test_zero_detection_csv_can_produce_print_brief(self):
        video_path = self.make_video("empty.mp4", frame_count=3)
        FakeYOLO.detections = [[], [], []]
        run_dir = self.run_with_fake_model(video_path, ["person"], self.root / "empty_runs")

        self.assertFalse((run_dir / "brief.pdf").exists())
        with (run_dir / "detections.csv").open(
            encoding="utf-8",
            newline="",
        ) as csv_file:
            rows = list(csv.DictReader(csv_file))
        self.assertEqual(rows[0]["class"], "__none__")
        self.assertTrue(rows[0]["model"])
        self.assertGreater(float(rows[0]["processing_seconds"]), 0)

        analysis = analyze_csv(run_dir / "detections.csv")
        self.assertTrue(analysis.counts.empty)
        self.assertIsNotNone(analysis.processing_fps)
        brief_path = build_brief(run_dir / "detections.csv")
        self.assertTrue(brief_path.is_file())
        self.assertTrue(brief_path.read_bytes().startswith(b"%PDF-"))

    def test_legacy_csv_missing_provenance_loads_with_not_recorded_values(self):
        csv_path = self.root / "legacy.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
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
            writer.writerow(("legacy.mp4", 10, 30, "2026-01-01T00:00:00Z", 1, "car", 1, 2, 0.8, ""))
        analysis = analyze_csv(csv_path)
        self.assertEqual(analysis.model, None)
        self.assertEqual(analysis.confidence, None)
        self.assertEqual(analysis.imgsz, None)
        self.assertEqual(analysis.min_track_frames, None)
        self.assertEqual(analysis.min_box_px, None)
        self.assertEqual(analysis.processing_seconds, None)
        self.assertIsNone(analysis.processing_fps)

    def test_video_over_five_minutes_processes_without_full_frame_retention(self):
        video_path = self.make_video("long.mp4", frame_count=1501)
        FakeYOLO.detections = [[] for _ in range(1501)]
        progress = []
        output_root = self.root / "long_runs"
        with (
            patch("core.detector.torch.cuda.is_available", return_value=True),
            patch("core.detector.torch.cuda.get_device_name", return_value="Test CUDA"),
            patch("core.detector.YOLO", FakeYOLO),
        ):
            run_dir = run_detection(
                video_path,
                selected_classes=["person"],
                progress_callback=lambda processed, total: progress.append(
                    (processed, total)
                ),
                output_root=output_root,
                model_name="fake.pt",
            )

        analysis = analyze_csv(run_dir / "detections.csv")
        self.assertGreater(analysis.video_duration_sec, 300)
        self.assertEqual(progress[0], (1, 1501))
        self.assertEqual(progress[-1], (1501, 1501))
        self.assertEqual(len(progress), 1501)
        self.assertTrue((run_dir / "annotated.mp4").is_file())


if __name__ == "__main__":
    unittest.main()
