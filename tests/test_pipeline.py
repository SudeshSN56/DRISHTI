import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from core.analysis import analyze_csv
from core.detector import run_detection
from core.report import build_brief
from core.video_source import VideoSource, VideoSourceError


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

    def run_with_fake_model(self, video_path, classes, output_root):
        with (
            patch("core.detector.torch.cuda.is_available", return_value=True),
            patch("core.detector.YOLO", FakeYOLO),
        ):
            return run_detection(
                video_path,
                selected_classes=classes,
                output_root=output_root,
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

        run_dir = self.run_with_fake_model(video_path, ["car"], self.root / "runs")
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

        analysis = analyze_csv(run_dir / "detections.csv")
        self.assertTrue(analysis.counts.empty)
        brief_path = build_brief(run_dir / "detections.csv")
        self.assertTrue(brief_path.is_file())
        self.assertTrue(brief_path.read_bytes().startswith(b"%PDF-"))

    def test_video_over_five_minutes_processes_without_full_frame_retention(self):
        video_path = self.make_video("long.mp4", frame_count=1501)
        FakeYOLO.detections = [[] for _ in range(1501)]
        progress = []
        output_root = self.root / "long_runs"
        with (
            patch("core.detector.torch.cuda.is_available", return_value=True),
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
