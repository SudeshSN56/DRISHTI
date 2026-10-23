from datetime import date
from pathlib import Path
import unittest

from ui.charts import (
    bar_list,
    bar_path,
    histogram,
    nice_max,
    stacked_bar,
    visible_objects_histogram,
)
from ui.components import class_color
from ui.data import RunInfo, filter_runs
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

    def test_run_filters_and_sorting(self):
        runs = [
            RunInfo(Path("run_20261001"), "traffic.mp4", "2026-10-01T10:00:00Z", 12, 4, ("car",)),
            RunInfo(Path("run_20261002"), "crowd.mp4", "2026-10-02T10:00:00Z", 35, 9, ("person",)),
            RunInfo(Path("run_20261003"), "traffic-night.mp4", "2026-10-03T10:00:00Z", 20, 6, ("car", "bus")),
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
        longest = filter_runs(runs, sort_by="longest video")
        self.assertEqual(longest[0].video_name, "crowd.mp4")
        newest = filter_runs(runs)
        self.assertEqual(newest[0].video_name, "traffic-night.mp4")


if __name__ == "__main__":
    unittest.main()
