import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.evaluate_counts import comparison_rows, load_manual_counts


class EvaluateCountsTests(unittest.TestCase):
    def test_comparison_math_uses_manual_count_denominator(self):
        rows = comparison_rows(
            "clip.mp4",
            {"car": 20, "person": 0},
            {"car": 15, "bus": 2},
        )
        self.assertEqual(
            rows,
            [
                {
                    "clip": "clip.mp4",
                    "class": "bus",
                    "manual_count": 0,
                    "app_count": 2,
                    "absolute_difference": 2,
                    "percentage_difference": None,
                    "variant": "recorded run",
                    "run_dir": "",
                },
                {
                    "clip": "clip.mp4",
                    "class": "car",
                    "manual_count": 20,
                    "app_count": 15,
                    "absolute_difference": 5,
                    "percentage_difference": 25.0,
                    "variant": "recorded run",
                    "run_dir": "",
                },
                {
                    "clip": "clip.mp4",
                    "class": "person",
                    "manual_count": 0,
                    "app_count": 0,
                    "absolute_difference": 0,
                    "percentage_difference": 0.0,
                    "variant": "recorded run",
                    "run_dir": "",
                },
            ],
        )

    def test_manual_counts_json_loads_and_rejects_invalid_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manual.json"
            path.write_text(
                json.dumps({"clip.mp4": {"car": 3, "person": 1}}),
                encoding="utf-8",
            )
            self.assertEqual(
                load_manual_counts(path),
                {"clip.mp4": {"car": 3, "person": 1}},
            )
            path.write_text('{"clip.mp4":{"car":-1}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manual_counts(path)

    def test_cli_prints_manual_count_comparison_and_saves_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run_empty"
            run_dir.mkdir()
            (run_dir / "detections.csv").write_text(
                "video_name,video_duration_sec,fps,processed_at,track_id,class,first_seen_sec\n"
                "empty.mp4,1,5,2026-01-01T00:00:00Z,,__none__,\n",
                encoding="utf-8",
            )
            manual_path = root / "manual.json"
            manual_path.write_text('{"empty.mp4":{"car":0}}', encoding="utf-8")
            output_dir = root / "results"
            with patch("tools.evaluate_counts.OUTPUTS_DIR", output_dir):
                from tools.evaluate_counts import evaluate

                results, output_path = evaluate(
                    load_manual_counts(manual_path),
                    [run_dir],
                    output_dir=output_dir,
                )
            self.assertTrue(output_path.is_file())
            self.assertEqual(int(results.iloc[0]["manual_count"]), 0)
            self.assertEqual(int(results.iloc[0]["app_count"]), 0)
            self.assertEqual(float(results.iloc[0]["percentage_difference"]), 0.0)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.evaluate_counts",
                    str(manual_path),
                    str(run_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=Path(__file__).resolve().parent.parent,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("manual_count", completed.stdout)
            self.assertIn("absolute_difference", completed.stdout)
            self.assertIn("Saved manual-count comparison", completed.stdout)


if __name__ == "__main__":
    unittest.main()
