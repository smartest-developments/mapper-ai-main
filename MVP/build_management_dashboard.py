#!/usr/bin/env python3
"""Build a static, local-first dashboard data file from MVP output runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
from pathlib import Path

RUN_DIR_RE = re.compile(r"^\d{8}_\d{6}$")
DASHBOARD_STATIC_FILES = [
    "management_dashboard.html",
    "management_dashboard.css",
    "management_dashboard.js",
    "tabler.min.css",
    "tabler.min.js",
    "chart.umd.js",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build management dashboard data from MVP outputs")
    parser.add_argument("--output-root", default="output", help="Output root containing timestamped run folders")
    parser.add_argument("--dashboard-subdir", default="dashboard", help="Dashboard directory under output root")
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
    try:
        return dt.datetime.strptime(run_id, "%Y%m%d_%H%M%S").isoformat(timespec="seconds")
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
    technical_dir = run_dir / "technical output"

    management_summary = read_json(technical_dir / "management_summary.json")
    ground_truth = read_json(technical_dir / "ground_truth_match_quality.json")
    run_summary = read_json(technical_dir / "run_summary.json")
    mapping_summary = read_json(technical_dir / "mapping_summary.json")

    pair_metrics = ground_truth.get("pair_metrics") if isinstance(ground_truth.get("pair_metrics"), dict) else {}
    distribution_metrics = (
        ground_truth.get("distribution_metrics") if isinstance(ground_truth.get("distribution_metrics"), dict) else {}
    )

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

    return {
        "run_id": run_id,
        "run_datetime": parse_run_datetime(run_id),
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

    precision_values = [float(run["pair_precision_pct"]) for run in runs if isinstance(run.get("pair_precision_pct"), (int, float))]
    recall_values = [float(run["pair_recall_pct"]) for run in runs if isinstance(run.get("pair_recall_pct"), (int, float))]

    total_input = sum(int(run.get("records_input")) for run in runs if isinstance(run.get("records_input"), int))
    total_pairs = sum(int(run.get("matched_pairs")) for run in runs if isinstance(run.get("matched_pairs"), int))

    return {
        "runs_total": len(runs),
        "latest_run_id": runs[0]["run_id"] if runs else None,
        "avg_pair_precision_pct": mean(precision_values),
        "avg_pair_recall_pct": mean(recall_values),
        "records_input_total": total_input,
        "matched_pairs_total": total_pairs,
    }


def write_data_js(path: Path, payload: dict) -> None:
    js = "window.MVP_DASHBOARD_DATA = " + json.dumps(payload, indent=2, ensure_ascii=True) + ";\n"
    path.write_text(js, encoding="utf-8")


def copy_static_dashboard_assets(mvp_root: Path, dashboard_dir: Path) -> None:
    for name in DASHBOARD_STATIC_FILES:
        source = mvp_root / name
        if not source.exists():
            raise FileNotFoundError(f"Dashboard static asset missing: {source}")
        shutil.copy2(source, dashboard_dir / name)


def main() -> int:
    args = parse_args()
    mvp_root = Path(__file__).resolve().parent
    output_root = (mvp_root / args.output_root).resolve()
    dashboard_dir = (output_root / args.dashboard_subdir).resolve()
    data_js_path = dashboard_dir / "management_dashboard_data.js"

    if not output_root.exists():
        output_root.mkdir(parents=True, exist_ok=True)
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    copy_static_dashboard_assets(mvp_root, dashboard_dir)

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
