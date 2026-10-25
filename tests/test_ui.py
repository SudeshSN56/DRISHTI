from datetime import date
from pathlib import Path
import tempfile
import unittest

from core.report import _class_hex, _class_rgb
from ui.charts import (
    bar_list,
    bar_path,
    histogram,
    nice_max,
    stacked_bar,
    visible_objects_histogram,
)
from ui.components import class_color
from ui.data import (
    ObjectInfo,
    RunInfo,
    available_dataset_videos,
    filter_runs,
    sort_objects_by_confidence,
)
from ui.pages.library import scan_source_files
from ui.pages.results import _time_label


class UIHelperTests(unittest.TestCase):
    def test_bar_list_is_sorted_and_contains_counts_and_shares(self):
        svg = bar_list([("person", 1), ("car", 3)])
        self.assertIn('viewBox="0 0 800 100"', svg)
        self.assertLess(svg.index(">car</text>"), svg.index(">person</text>"))
        self.assertIn("3", svg)
        self.assertIn("75.0%", svg)
        self.assertIn("#6b9bea", svg)

    def test_histogram_contains_buckets_tooltips_and_nice_axis(self):
        svg = histogram([("00:00.0–00:05.0", 3), ("00:05.0–00:10.0", 1)])
        self.assertIn('aria-label="Five-second object timeline"', svg)
        self.assertIn("<title>00:00.0–00:05.0: 3 first-seen objects</title>", svg)
        self.assertIn("00:05.0–00:10.0", svg)
        self.assertEqual(nice_max(3), 5)

    def test_stacked_bar_shows_class_shares_and_empty_state(self):
        svg = stacked_bar([("car", 3), ("person", 1)])
        self.assertIn("<title>car: 3 objects (75.0%)</title>", svg)
        self.assertIn("#fab219", svg)
        self.assertIn("25.0%", svg)
        self.assertIn("No detections", stacked_bar([]))

    def test_visible_objects_histogram_labels_counts_as_active_objects(self):
        svg = visible_objects_histogram([("00:00–00:05", 4)])
        self.assertIn(
            'aria-label="Objects visible over time in five-second windows"',
            svg,
        )
        self.assertIn("<title>00:00–00:05: 4 active objects</title>", svg)

    def test_bar_path_and_axis_formatting(self):
        self.assertIn("Q 10 20 14 20", bar_path(10, 20, 30, 40, 4))
        self.assertEqual(_time_label(65.5), "01:05.5")
        self.assertEqual(nice_max(0), 1)

    def test_class_colors_are_fixed_or_deterministic(self):
        self.assertEqual(class_color("person"), "#fab219")
        self.assertEqual(class_color("unknown"), class_color("unknown"))

    def test_pdf_class_color_conversion_matches_ui_palette(self):
        self.assertEqual(_class_rgb("person"), (250, 178, 25))
        self.assertEqual(_class_hex("person"), "#fab219")
        self.assertTrue(_class_hex("unknown").startswith("#"))

    def test_run_filters_and_sorting(self):
        runs = [
            RunInfo(Path("run_20261001"), "traffic.mp4", "2026-10-01T10:00:00Z", 12, 4, ("car",), "Mumbai"),
            RunInfo(Path("run_20261002"), "crowd.mp4", "2026-10-02T10:00:00Z", 35, 9, ("person",), "Pune"),
            RunInfo(Path("run_20261003"), "traffic-night.mp4", "2026-10-03T10:00:00Z", 20, 6, ("car", "bus"), "Bengaluru"),
        ]
        filtered = filter_runs(
            runs,
            video_query="TRAFFIC",
            class_name="car",
            min_objects=5,
            after=date(2026, 10, 2),
            sort_by="most objects",
        )
        self.assertEqual([run.video_name for run in filtered], ["traffic-night.mp4"])
        city_filtered = filter_runs(runs, video_query="pune")
        self.assertEqual([run.video_name for run in city_filtered], ["crowd.mp4"])
        longest = filter_runs(runs, sort_by="longest video")
        self.assertEqual(longest[0].video_name, "crowd.mp4")
        newest = filter_runs(runs)
        self.assertEqual(newest[0].video_name, "traffic-night.mp4")

    def test_dataset_sequences_include_flat_and_nested_visdrone_layouts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            flat_sequence = root / "VisDrone2019-VID-train" / "sequences" / "uav_train"
            nested_sequence = (
                root
                / "VisDrone2019-VID-val"
                / "VisDrone2019-VID-val"
                / "sequences"
                / "uav_val"
            )
            flat_sequence.mkdir(parents=True)
            nested_sequence.mkdir(parents=True)
            (flat_sequence / "0000001.jpg").write_bytes(b"frame")
            (flat_sequence / "0000002.jpeg").write_bytes(b"frame")
            (flat_sequence / "readme.txt").write_text("not a frame")
            (nested_sequence / "0000001.jpg").write_bytes(b"frame")

            videos = available_dataset_videos(root)

        self.assertEqual(
            [(video.dataset_name, video.name, video.frame_count) for video in videos],
            [
                ("VisDrone2019-VID-train", "uav_train", 2),
                ("VisDrone2019-VID-val", "uav_val", 1),
            ],
        )

    def test_file_library_indexes_dataset_and_test_video_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            datasets = root / "datasets"
            test_videos = root / "test_videos"
            sequence = datasets / "VisDrone2019-VID-val" / "sequences" / "uav_val"
            sequence.mkdir(parents=True)
            test_videos.mkdir()
            (sequence / "0000001.jpg").write_bytes(b"frame")
            (datasets / "VisDrone2019-VID-val" / "annotations").mkdir()
            (datasets / "VisDrone2019-VID-val" / "annotations" / "uav_val.txt").write_text(
                "annotation"
            )
            (test_videos / "sample.mp4").write_bytes(b"video")

            files = scan_source_files(datasets, test_videos)

        self.assertEqual(len(files), 3)
        self.assertEqual(
            {(file["collection"], file["file"]) for file in files},
            {
                ("VisDrone datasets", "0000001.jpg"),
                ("VisDrone datasets", "uav_val.txt"),
                ("Test videos", "sample.mp4"),
            },
        )

    def test_snapshots_sort_by_average_confidence_with_missing_values_last(self):
        items = [
            ObjectInfo("1", "car", 0, 1, 0.4, None),
            ObjectInfo("2", "person", 0, 1, None, None),
            ObjectInfo("3", "truck", 0, 1, 0.9, None),
        ]
        self.assertEqual(
            [item.track_id for item in sort_objects_by_confidence(items)],
            ["3", "1", "2"],
        )


if __name__ == "__main__":
    unittest.main()
