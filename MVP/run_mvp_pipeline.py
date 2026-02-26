#!/usr/bin/env python3
"""Portable MVP pipeline for JSON -> Senzing JSONL -> E2E -> management outputs.

This script is self-contained inside the MVP folder and does not rely on the
full repository layout.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


def now_timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MVP pipeline from source JSON to Senzing management outputs.")
    parser.add_argument("--input-json", required=True, help="Source JSON path (array of records)")
    parser.add_argument("--input-array-key", default=None, help="Optional key if JSON root is an object containing array")
    parser.add_argument("--data-source", default="PARTNERS", help="Senzing DATA_SOURCE (default: PARTNERS)")
    parser.add_argument("--tax-id-type", default="TIN", help="TAX_ID_TYPE for mapper (default: TIN)")
    parser.add_argument(
        "--include-unmapped-source-fields",
        action="store_true",
        help="Include non-mapped source fields as SRC_* payload fields",
    )
    parser.add_argument("--output-dir", default="output", help="Mapped artifacts directory (default: output)")
    parser.add_argument("--runs-root", default="runs", help="Run directory root (default: runs)")
    parser.add_argument("--projects-root", default="projects", help="Senzing project root (default: projects)")
    parser.add_argument("--run-name-prefix", default="run_mvp", help="Run folder prefix")
    parser.add_argument("--project-name-prefix", default="Senzing_MVP", help="Project folder prefix")
    parser.add_argument(
        "--docker-image",
        default="mapper-senzing-poc:4.2.1",
        help="Docker image containing Senzing tools (default: mapper-senzing-poc:4.2.1)",
    )
    parser.add_argument("--docker-platform", default="linux/amd64", help="Docker platform (default: linux/amd64)")
    parser.add_argument("--step-timeout-seconds", type=int, default=1800, help="Timeout per E2E step")
    parser.add_argument(
        "--with-why",
        action="store_true",
        help="Enable explain/WHY extraction (disabled by default for faster large runs)",
    )
    parser.add_argument("--max-explain-records", type=int, default=200, help="Max explain records when --with-why is enabled")
    parser.add_argument("--max-explain-pairs", type=int, default=200, help="Max explain pairs when --with-why is enabled")
    parser.add_argument(
        "--keep-loader-temp-files",
        action="store_true",
        help="Keep sz_file_loader temporary shuffle files",
    )
    return parser.parse_args()


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def to_container_path(root: Path, host_path: Path) -> Path:
    return Path("/workspace") / host_path.resolve().relative_to(root.resolve())


def from_container_path(root: Path, value: str | None) -> str | None:
    if not value:
        return value
    prefix = "/workspace/"
    if value == "/workspace":
        return str(root)
    if value.startswith(prefix):
        rel = value[len(prefix):]
        return str((root / rel).resolve())
    return value


def find_new_run_dir(runs_root: Path, prefix: str, before: set[Path]) -> Path:
    after = set(path for path in runs_root.glob(f"{prefix}_*") if path.is_dir())
    created = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if created:
        return created[0]
    fallback = sorted(after, key=lambda p: p.stat().st_mtime, reverse=True)
    if not fallback:
        raise FileNotFoundError(f"No run directory found under {runs_root} with prefix {prefix}")
    return fallback[0]


def main() -> int:
    args = parse_args()
    mvp_root = Path(__file__).resolve().parent
    input_json = Path(args.input_json).expanduser().resolve()

    if not input_json.exists():
        print(f"ERROR: input JSON not found: {input_json}", file=sys.stderr)
        return 2

    mapper_script = mvp_root / "senzing" / "tools" / "partner_json_to_senzing.py"
    e2e_script = mvp_root / "senzing" / "all_in_one" / "run_senzing_end_to_end.py"

    missing_scripts = [str(path) for path in [mapper_script, e2e_script] if not path.exists()]
    if missing_scripts:
        print("ERROR: missing required scripts:", file=sys.stderr)
        for item in missing_scripts:
            print(f"  - {item}", file=sys.stderr)
        return 2

    output_dir = (mvp_root / args.output_dir).resolve()
    runs_root = (mvp_root / args.runs_root).resolve()
    projects_root = (mvp_root / args.projects_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_root.mkdir(parents=True, exist_ok=True)
    projects_root.mkdir(parents=True, exist_ok=True)

    ts = now_timestamp()
    mapped_output_jsonl = output_dir / f"partner_output_senzing_from_input_{ts}.jsonl"
    field_map_json = output_dir / f"field_map_from_input_{ts}.json"
    mapping_summary_json = output_dir / f"mapping_summary_from_input_{ts}.json"

    mapper_cmd = [
        sys.executable,
        str(mapper_script),
        str(input_json),
        str(mapped_output_jsonl),
        "--data-source",
        args.data_source,
        "--tax-id-type",
        args.tax_id_type,
        "--write-field-map",
        str(field_map_json),
    ]
    if args.input_array_key:
        mapper_cmd.extend(["--array-key", args.input_array_key])
    if args.include_unmapped_source_fields:
        mapper_cmd.append("--include-unmapped-source-fields")

    run_command(mapper_cmd, mvp_root)

    mapping_summary = {
        "mode": "input_json",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "input_json": str(input_json),
        "mapped_output_jsonl": str(mapped_output_jsonl),
        "field_map_json": str(field_map_json),
        "data_source": args.data_source,
        "tax_id_type": args.tax_id_type,
        "input_array_key": args.input_array_key,
        "include_unmapped_source_fields": bool(args.include_unmapped_source_fields),
    }
    mapping_summary_json.write_text(json.dumps(mapping_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    runs_before = set(path for path in runs_root.glob(f"{args.run_name_prefix}_*") if path.is_dir())

    container_input_jsonl = to_container_path(mvp_root, mapped_output_jsonl)
    container_runs_root = to_container_path(mvp_root, runs_root)
    container_projects_root = to_container_path(mvp_root, projects_root)
    container_e2e_script = to_container_path(mvp_root, e2e_script)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--platform",
        args.docker_platform,
        "-v",
        f"{mvp_root}:/workspace",
        "-w",
        "/workspace",
        args.docker_image,
        "python3",
        str(container_e2e_script),
        str(container_input_jsonl),
        "--output-root",
        str(container_runs_root),
        "--run-name-prefix",
        args.run_name_prefix,
        "--project-parent-dir",
        str(container_projects_root),
        "--project-name-prefix",
        args.project_name_prefix,
        "--use-input-jsonl-directly",
        "--data-sources",
        args.data_source,
        "--step-timeout-seconds",
        str(args.step_timeout_seconds),
    ]

    if args.with_why:
        docker_cmd.extend(["--max-explain-records", str(args.max_explain_records)])
        docker_cmd.extend(["--max-explain-pairs", str(args.max_explain_pairs)])
    else:
        docker_cmd.append("--skip-explain")

    if args.keep_loader_temp_files:
        docker_cmd.append("--keep-loader-temp-files")

    run_command(docker_cmd, mvp_root)

    run_dir = find_new_run_dir(runs_root, args.run_name_prefix, runs_before)
    run_summary = run_dir / "run_summary.json"
    if not run_summary.exists():
        print(f"ERROR: run summary not found: {run_summary}", file=sys.stderr)
        return 2

    payload = json.loads(run_summary.read_text(encoding="utf-8"))
    artifacts = payload.get("artifacts", {})

    print("\nMVP pipeline completed.")
    print(f"Input JSON: {input_json}")
    print(f"Mapping summary: {mapping_summary_json}")
    print(f"Mapped JSONL: {mapped_output_jsonl}")
    print(f"Run summary: {run_summary}")
    print(f"Management summary (md): {from_container_path(mvp_root, artifacts.get('management_summary_md'))}")
    print(f"Ground truth quality (md): {from_container_path(mvp_root, artifacts.get('ground_truth_match_quality_md'))}")
    print(f"Run registry CSV: {from_container_path(mvp_root, artifacts.get('run_registry_csv'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
