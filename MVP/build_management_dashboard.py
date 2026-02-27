#!/usr/bin/env python3
"""Build a static, local-first dashboard data file from MVP output runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

RUN_DIR_RE = re.compile(r"^(?P<ts>\d{8}_\d{6})(?:__(?P<label>[A-Za-z0-9._-]+))?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build management dashboard data from MVP outputs")
    parser.add_argument("--output-root", default="output", help="Output root containing timestamped run folders")
    parser.add_argument("--dashboard-dir", default="dashboard", help="Dashboard directory under MVP root")
    return parser.parse_args()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def parse_run_datetime(run_id: str) -> str | None:
    match = RUN_DIR_RE.match(run_id)
    timestamp = match.group("ts") if match else run_id
    try:
        return dt.datetime.strptime(timestamp, "%Y%m%d_%H%M%S").isoformat(timespec="seconds")
    except ValueError:
        return None


def to_num(value: object) -> float | int | None:
    if isinstance(value, (int, float)):
        return value
    return None


def pct(value: object) -> float | None:
    number = to_num(value)
    if number is None:
        return None
    return round(float(number) * 100.0, 2)


def collect_run_record(output_root: Path, run_dir: Path) -> dict:
    run_id = run_dir.name
    match = RUN_DIR_RE.match(run_id)
    run_timestamp = match.group("ts") if match else run_id
    run_folder_label = match.group("label") if match else None
    technical_dir = run_dir / "technical output"

    management_summary = read_json(technical_dir / "management_summary.json")
    ground_truth = read_json(technical_dir / "ground_truth_match_quality.json")
    run_summary = read_json(technical_dir / "run_summary.json")
    mapping_summary = read_json(technical_dir / "mapping_summary.json")
    discovery_metrics = (
        management_summary.get("discovery_metrics") if isinstance(management_summary.get("discovery_metrics"), dict) else {}
    )

    pair_metrics = ground_truth.get("pair_metrics") if isinstance(ground_truth.get("pair_metrics"), dict) else {}
    distribution_metrics = (
        ground_truth.get("distribution_metrics") if isinstance(ground_truth.get("distribution_metrics"), dict) else {}
    )
    baseline_match_coverage_raw = discovery_metrics.get("baseline_match_coverage")
    if not isinstance(baseline_match_coverage_raw, (int, float)):
        known_pairs = discovery_metrics.get("known_pairs_ipg")
        true_pairs = discovery_metrics.get("true_pairs_total")
        if isinstance(known_pairs, int) and isinstance(true_pairs, int) and true_pairs > 0:
            baseline_match_coverage_raw = known_pairs / true_pairs

    senzing_true_coverage_raw = discovery_metrics.get("senzing_true_coverage")
    if not isinstance(senzing_true_coverage_raw, (int, float)):
        true_found = discovery_metrics.get("overall_true_pairs_found")
        true_pairs = discovery_metrics.get("true_pairs_total")
        if isinstance(true_found, int) and isinstance(true_pairs, int) and true_pairs > 0:
            senzing_true_coverage_raw = true_found / true_pairs

    mapping_input = str(mapping_summary.get("input_json") or "").strip()
    source_input_name = Path(mapping_input).name if mapping_input else None
    output_label = str(mapping_summary.get("output_label") or "").strip() or run_folder_label

    artifact_entries: list[dict[str, object]] = []
    for file_path in sorted(path for path in run_dir.rglob("*") if path.is_file()):
        if any(part.startswith(".") for part in file_path.relative_to(run_dir).parts):
            continue
        rel = file_path.relative_to(output_root)
        artifact_entries.append(
            {
                "relative_path": rel.as_posix(),
                "display_name": str(file_path.relative_to(run_dir)).replace("\\", "/"),
                "size_bytes": file_path.stat().st_size,
            }
        )

    has_management_summary = bool(management_summary)
    has_ground_truth = bool(ground_truth)
    has_run_summary = bool(run_summary)
    overall_ok = run_summary.get("overall_ok") if isinstance(run_summary.get("overall_ok"), bool) else None
    quality_available = (
        isinstance(pair_metrics.get("pair_precision"), (int, float))
        and isinstance(pair_metrics.get("pair_recall"), (int, float))
        and isinstance(pair_metrics.get("true_positive"), int)
        and isinstance(pair_metrics.get("false_positive"), int)
        and isinstance(pair_metrics.get("false_negative"), int)
    )
    if has_run_summary and overall_ok is False:
        run_status = "failed"
    elif has_management_summary and has_ground_truth:
        run_status = "success"
    else:
        run_status = "incomplete"

    return {
        "run_id": run_id,
        "run_timestamp": run_timestamp,
        "run_datetime": parse_run_datetime(run_id),
        "run_label": output_label,
        "source_input_name": source_input_name,
        "run_status": run_status,
        "has_management_summary": has_management_summary,
        "has_ground_truth_summary": has_ground_truth,
        "has_run_summary": has_run_summary,
        "overall_ok": overall_ok,
        "quality_available": quality_available,
        "generated_at": management_summary.get("generated_at")
        or ground_truth.get("generated_at")
        or run_summary.get("generated_at"),
        "records_input": management_summary.get("records_input"),
        "records_exported": management_summary.get("records_exported"),
        "resolved_entities": management_summary.get("resolved_entities"),
        "matched_records": management_summary.get("matched_records"),
        "matched_pairs": management_summary.get("matched_pairs"),
        "pair_precision_pct": pct(pair_metrics.get("pair_precision")),
        "pair_recall_pct": pct(pair_metrics.get("pair_recall")),
        "true_positive": pair_metrics.get("true_positive"),
        "false_positive": pair_metrics.get("false_positive"),
        "false_negative": pair_metrics.get("false_negative"),
        "discovery_available": bool(discovery_metrics.get("available")),
        "extra_true_matches_found": discovery_metrics.get("extra_true_matches_found"),
        "extra_false_matches_found": discovery_metrics.get("extra_false_matches_found"),
        "extra_match_precision_pct": pct(discovery_metrics.get("extra_match_precision")),
        "extra_match_recall_pct": pct(discovery_metrics.get("extra_match_recall")),
        "extra_gain_vs_known_pct": pct(discovery_metrics.get("extra_gain_vs_known")),
        "discoverable_true_pairs": discovery_metrics.get("discoverable_true_pairs"),
        "predicted_pairs_beyond_known": discovery_metrics.get("predicted_pairs_beyond_known"),
        "net_extra_matches": discovery_metrics.get("net_extra_matches"),
        "overall_false_positive_pct": pct(discovery_metrics.get("overall_false_positive_rate")),
        "overall_match_correctness_pct": pct(discovery_metrics.get("overall_match_correctness")),
        "our_match_coverage_pct": pct(baseline_match_coverage_raw),
        "senzing_true_coverage_pct": pct(senzing_true_coverage_raw),
        "predicted_pairs_labeled": pair_metrics.get("predicted_pairs_labeled"),
        "ground_truth_pairs_labeled": pair_metrics.get("ground_truth_pairs_labeled"),
        "match_level_distribution": management_summary.get("match_level_distribution", {}),
        "top_match_keys": sorted(
            (
                (
                    str(key),
                    int(value),
                )
                for key, value in (management_summary.get("match_key_distribution") or {}).items()
                if isinstance(key, str) and isinstance(value, int)
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:10],
        "entity_size_distribution": distribution_metrics.get("entity_size_distribution", {}),
        "entity_pairings_distribution": distribution_metrics.get("entity_pairings_distribution", {}),
        "record_pairing_degree_distribution": distribution_metrics.get("record_pairing_degree_distribution", {}),
        "explain_coverage": management_summary.get("explain_coverage", {}),
        "runtime_warnings": run_summary.get("runtime_warnings", []),
        "input_source_path": f"{run_id}/input_source.json",
        "management_summary_path": f"{run_id}/management_summary.md",
        "ground_truth_summary_path": f"{run_id}/ground_truth_match_quality.md",
        "technical_path": f"{run_id}/technical output",
        "mapping_info": {
            "data_source": mapping_summary.get("data_source"),
            "tax_id_type": mapping_summary.get("tax_id_type"),
            "execution_mode": mapping_summary.get("execution_mode"),
        },
        "artifacts": artifact_entries,
    }


def collect_runs(output_root: Path) -> list[dict]:
    run_dirs = [path for path in output_root.iterdir() if path.is_dir() and RUN_DIR_RE.match(path.name)]
    run_dirs.sort(key=lambda path: path.name, reverse=True)
    return [collect_run_record(output_root, run_dir) for run_dir in run_dirs]


def aggregate(runs: list[dict]) -> dict:
    def mean(values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    quality_runs = [run for run in runs if bool(run.get("quality_available"))]
    precision_values = [float(run["pair_precision_pct"]) for run in quality_runs if isinstance(run.get("pair_precision_pct"), (int, float))]
    recall_values = [float(run["pair_recall_pct"]) for run in quality_runs if isinstance(run.get("pair_recall_pct"), (int, float))]

    total_input = sum(int(run.get("records_input")) for run in quality_runs if isinstance(run.get("records_input"), int))
    total_pairs = sum(int(run.get("matched_pairs")) for run in quality_runs if isinstance(run.get("matched_pairs"), int))
    successful_runs = sum(1 for run in runs if run.get("run_status") == "success")
    failed_runs = sum(1 for run in runs if run.get("run_status") == "failed")
    incomplete_runs = sum(1 for run in runs if run.get("run_status") == "incomplete")

    return {
        "runs_total": len(runs),
        "quality_runs_total": len(quality_runs),
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "incomplete_runs": incomplete_runs,
        "latest_run_id": runs[0]["run_id"] if runs else None,
        "avg_pair_precision_pct": mean(precision_values),
        "avg_pair_recall_pct": mean(recall_values),
        "records_input_total": total_input,
        "matched_pairs_total": total_pairs,
    }


def write_data_js(path: Path, payload: dict) -> None:
    js = "window.MVP_DASHBOARD_DATA = " + json.dumps(payload, indent=2, ensure_ascii=True) + ";\n"
    path.write_text(js, encoding="utf-8")


def main() -> int:
    args = parse_args()
    mvp_root = Path(__file__).resolve().parent
    output_root = (mvp_root / args.output_root).resolve()
    dashboard_dir = (mvp_root / args.dashboard_dir).resolve()
    data_js_path = dashboard_dir / "management_dashboard_data.js"

    if not output_root.exists():
        output_root.mkdir(parents=True, exist_ok=True)
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    runs = collect_runs(output_root)
    payload = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "output_root": str(output_root),
        "runs": runs,
        "summary": aggregate(runs),
    }

    write_data_js(data_js_path, payload)
    print(f"Dashboard data generated: {data_js_path}")
    print(f"Runs indexed: {len(runs)}")
    print(f"Dashboard directory: {dashboard_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
