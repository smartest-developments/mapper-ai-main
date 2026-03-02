"""End-to-end assertions for dashboard KPIs against raw run artifacts."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from typing import Any

from testing.dashboard_assertions import (
    as_int,
    compute_expected_run_metrics,
    compute_summary_from_runs,
    normalize_distribution,
    parse_dashboard_data_js,
)

TOLERANCE = 0.01


class DashboardMetricsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mvp_root = Path(__file__).resolve().parents[1]

        dashboard_data_env = os.environ.get("MVP_DASHBOARD_DATA_PATH", "").strip()
        if dashboard_data_env:
            dashboard_data_path = Path(dashboard_data_env).expanduser()
            if not dashboard_data_path.is_absolute():
                dashboard_data_path = cls.mvp_root / dashboard_data_path
        else:
            dashboard_data_path = cls.mvp_root / "dashboard" / "management_dashboard_data.js"
        cls.dashboard_data_path = dashboard_data_path.resolve()

        cls.payload = parse_dashboard_data_js(cls.dashboard_data_path)
        runs = cls.payload.get("runs") if isinstance(cls.payload.get("runs"), list) else []
        cls.runs = [run for run in runs if isinstance(run, dict)]
        cls.success_runs = [run for run in cls.runs if run.get("run_status") == "success"]

        output_root_env = os.environ.get("MVP_OUTPUT_ROOT", "").strip()
        if output_root_env:
            output_root = Path(output_root_env).expanduser()
            if not output_root.is_absolute():
                output_root = cls.mvp_root / output_root
        else:
            output_root = Path(str(cls.payload.get("output_root") or "")).expanduser()
            if not output_root.is_absolute():
                output_root = cls.mvp_root / "output"
        cls.output_root = output_root.resolve()

        cls.expected_by_run: dict[str, dict[str, Any]] = {
            str(run.get("run_id")): compute_expected_run_metrics(run, cls.output_root)
            for run in cls.success_runs
        }

    def assert_metric(self, run_id: str, metric_name: str, dashboard_value: Any, expected_value: Any, tolerance: float = TOLERANCE) -> None:
        context = f"run_id={run_id} metric={metric_name}"
        if expected_value is None:
            self.assertIsNone(dashboard_value, msg=f"Expected None ({context}) but got {dashboard_value!r}")
            return
        if isinstance(expected_value, (int, float)):
            self.assertIsInstance(
                dashboard_value,
                (int, float),
                msg=f"Expected numeric value for {context}, got {type(dashboard_value).__name__}",
            )
            delta = abs(float(dashboard_value) - float(expected_value))
            self.assertLessEqual(
                delta,
                tolerance,
                msg=f"Value mismatch for {context}: dashboard={dashboard_value} expected={expected_value} delta={delta}",
            )
            return
        self.assertEqual(dashboard_value, expected_value, msg=f"Value mismatch for {context}")

    def test_payload_contains_runs(self) -> None:
        self.assertTrue(self.dashboard_data_path.exists(), "Dashboard data file does not exist")
        self.assertGreater(len(self.runs), 0, "Dashboard payload has no runs")

    def test_success_run_artifacts_exist(self) -> None:
        self.assertGreater(len(self.success_runs), 0, "No successful runs found in dashboard payload")
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            expected = self.expected_by_run[run_id]
            with self.subTest(run_id=run_id):
                paths = expected["paths"]
                self.assertTrue(paths["run_dir"].exists(), f"Missing run directory: {paths['run_dir']}")
                self.assertTrue(paths["technical_dir"].exists(), f"Missing technical output directory: {paths['technical_dir']}")
                self.assertTrue(paths["management_summary_json"].exists(), f"Missing management_summary.json for {run_id}")
                self.assertTrue(paths["ground_truth_json"].exists(), f"Missing ground_truth_match_quality.json for {run_id}")
                self.assertTrue(paths["entity_records_csv"].exists(), f"Missing entity_records.csv for {run_id}")
                self.assertTrue(paths["matched_pairs_csv"].exists(), f"Missing matched_pairs.csv for {run_id}")
                self.assertTrue(paths["input_source_json"].exists(), f"Missing input_source.json for {run_id}")

    def test_file_counts_match_dashboard_values(self) -> None:
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            expected = self.expected_by_run[run_id]["from_files"]
            with self.subTest(run_id=run_id):
                self.assert_metric(run_id, "records_input", run.get("records_input"), expected.get("records_input"), tolerance=0.0)
                self.assert_metric(run_id, "matched_pairs", run.get("matched_pairs"), expected.get("matched_pairs"), tolerance=0.0)
                self.assert_metric(run_id, "resolved_entities", run.get("resolved_entities"), expected.get("resolved_entities"), tolerance=0.0)
                self.assert_metric(
                    run_id,
                    "our_resolved_entities",
                    run.get("our_resolved_entities"),
                    expected.get("our_resolved_entities"),
                    tolerance=0.0,
                )

    def test_confusion_matrix_counts_match_ground_truth(self) -> None:
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            expected = self.expected_by_run[run_id]["from_ground_truth"]
            with self.subTest(run_id=run_id):
                self.assert_metric(run_id, "true_positive", run.get("true_positive"), expected.get("true_positive"), tolerance=0.0)
                self.assert_metric(run_id, "false_positive", run.get("false_positive"), expected.get("false_positive"), tolerance=0.0)
                self.assert_metric(run_id, "false_negative", run.get("false_negative"), expected.get("false_negative"), tolerance=0.0)
                self.assert_metric(
                    run_id,
                    "predicted_pairs_labeled",
                    run.get("predicted_pairs_labeled"),
                    expected.get("predicted_pairs_labeled"),
                    tolerance=0.0,
                )

    def test_kpi_percentages_match_formulas(self) -> None:
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            expected = self.expected_by_run[run_id]["from_ground_truth"]
            with self.subTest(run_id=run_id):
                self.assert_metric(
                    run_id,
                    "pair_precision_pct",
                    run.get("pair_precision_pct"),
                    expected.get("pair_precision_pct"),
                )
                self.assert_metric(
                    run_id,
                    "pair_recall_pct",
                    run.get("pair_recall_pct"),
                    expected.get("pair_recall_pct"),
                )
                self.assert_metric(
                    run_id,
                    "overall_false_positive_pct",
                    run.get("overall_false_positive_pct"),
                    expected.get("overall_false_positive_pct"),
                )
                self.assert_metric(
                    run_id,
                    "pair_precision_pct_from_counts",
                    run.get("pair_precision_pct"),
                    expected.get("pair_precision_pct_from_counts"),
                )
                self.assert_metric(
                    run_id,
                    "pair_recall_pct_from_counts",
                    run.get("pair_recall_pct"),
                    expected.get("pair_recall_pct_from_counts"),
                )

    def test_our_baseline_metrics_match_discovery_logic(self) -> None:
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            expected = self.expected_by_run[run_id]["from_discovery"]
            with self.subTest(run_id=run_id):
                self.assert_metric(run_id, "our_true_positive", run.get("our_true_positive"), expected.get("our_true_positive"), tolerance=0.0)
                self.assert_metric(
                    run_id,
                    "our_true_pairs_total",
                    run.get("our_true_pairs_total"),
                    expected.get("our_true_pairs_total"),
                    tolerance=0.0,
                )
                self.assert_metric(
                    run_id,
                    "our_false_positive",
                    run.get("our_false_positive"),
                    expected.get("our_false_positive"),
                    tolerance=0.0,
                )
                self.assert_metric(
                    run_id,
                    "our_false_negative",
                    run.get("our_false_negative"),
                    expected.get("our_false_negative"),
                    tolerance=0.0,
                )
                self.assert_metric(
                    run_id,
                    "our_match_coverage_pct",
                    run.get("our_match_coverage_pct"),
                    expected.get("our_match_coverage_pct"),
                )

    def test_extra_metrics_match_discovery_fields(self) -> None:
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            expected = self.expected_by_run[run_id]["from_discovery"]
            with self.subTest(run_id=run_id):
                self.assert_metric(
                    run_id,
                    "extra_true_matches_found",
                    run.get("extra_true_matches_found"),
                    expected.get("extra_true_matches_found"),
                    tolerance=0.0,
                )
                self.assert_metric(
                    run_id,
                    "extra_false_matches_found",
                    run.get("extra_false_matches_found"),
                    expected.get("extra_false_matches_found"),
                    tolerance=0.0,
                )
                self.assert_metric(
                    run_id,
                    "extra_gain_vs_known_pct",
                    run.get("extra_gain_vs_known_pct"),
                    expected.get("extra_gain_vs_known_pct"),
                )

    def test_entity_size_distribution_is_consistent(self) -> None:
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            expected_dist = self.expected_by_run[run_id]["from_files"].get("entity_size_distribution")
            dashboard_dist = normalize_distribution(run.get("entity_size_distribution"))
            with self.subTest(run_id=run_id):
                self.assertIsNotNone(dashboard_dist, f"Invalid entity_size_distribution type for {run_id}")
                self.assertEqual(dashboard_dist, expected_dist, f"Distribution mismatch for {run_id}")
                dist_total = sum(int(value) for value in (dashboard_dist or {}).values())
                self.assertEqual(
                    dist_total,
                    as_int(run.get("resolved_entities")),
                    f"Distribution total must match resolved_entities for {run_id}",
                )

    def test_summary_block_matches_recomputed_values(self) -> None:
        summary = self.payload.get("summary") if isinstance(self.payload.get("summary"), dict) else {}
        expected_summary = compute_summary_from_runs(self.runs)

        for key in (
            "runs_total",
            "quality_runs_total",
            "successful_runs",
            "failed_runs",
            "incomplete_runs",
            "latest_run_id",
            "records_input_total",
            "matched_pairs_total",
        ):
            with self.subTest(summary_key=key):
                self.assertEqual(summary.get(key), expected_summary.get(key), f"Summary mismatch for {key}")

        for key in ("avg_pair_precision_pct", "avg_pair_recall_pct"):
            with self.subTest(summary_key=key):
                expected_value = expected_summary.get(key)
                dashboard_value = summary.get(key)
                if expected_value is None:
                    self.assertIsNone(dashboard_value, f"Expected None for summary.{key}")
                else:
                    self.assertIsInstance(dashboard_value, (int, float), f"Expected numeric summary.{key}")
                    self.assertLessEqual(
                        abs(float(dashboard_value) - float(expected_value)),
                        TOLERANCE,
                        f"Summary mismatch for {key}: dashboard={dashboard_value} expected={expected_value}",
                    )

    def test_validation_checks_have_no_failures(self) -> None:
        for run in self.success_runs:
            run_id = str(run.get("run_id"))
            validation = run.get("validation") if isinstance(run.get("validation"), dict) else {}
            with self.subTest(run_id=run_id):
                self.assertNotEqual(validation.get("status"), "FAIL", f"Validation status FAIL in dashboard payload for {run_id}")
                checks = validation.get("checks") if isinstance(validation.get("checks"), list) else []
                for check in checks:
                    if not isinstance(check, dict):
                        continue
                    self.assertNotEqual(
                        check.get("status"),
                        "FAIL",
                        f"Validation check failed in payload for {run_id}: {check.get('name')}",
                    )

    def test_synthetic_noise_coverage_exists(self) -> None:
        sample_runs = [
            run
            for run in self.success_runs
            if "sample_" in str(run.get("source_input_name") or "")
            or "sample_" in str(run.get("run_label") or "")
        ]
        if len(sample_runs) < 5:
            self.skipTest("Synthetic sample runs not detected; skipping synthetic-noise coverage checks")

        self.assertTrue(
            any((as_int(run.get("our_false_positive")) or 0) > 0 for run in sample_runs),
            "Expected at least one sample run with Our False Positive > 0",
        )
        self.assertTrue(
            any((as_int(run.get("our_false_negative")) or 0) > 0 for run in sample_runs),
            "Expected at least one sample run with Our False Negative > 0",
        )
        self.assertTrue(
            any((as_int(run.get("false_positive")) or 0) > 0 for run in sample_runs),
            "Expected at least one sample run with Their False Positive > 0",
        )
        self.assertTrue(
            any((as_int(run.get("false_negative")) or 0) > 0 for run in sample_runs),
            "Expected at least one sample run with Their False Negative > 0",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
