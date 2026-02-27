#!/usr/bin/env python3
"""MVP pipeline: JSON -> Senzing JSONL -> Senzing E2E -> output/<timestamp> artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def now_timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MVP pipeline from source JSON to timestamped output artifacts.")
    parser.add_argument("--input-json", required=True, help="Source JSON path (array of records)")
    parser.add_argument("--input-array-key", default=None, help="Optional key if JSON root is an object containing array")
    parser.add_argument("--data-source", default="PARTNERS", help="Senzing DATA_SOURCE (default: PARTNERS)")
    parser.add_argument("--tax-id-type", default="TIN", help="TAX_ID_TYPE for mapper (default: TIN)")
    parser.add_argument(
        "--include-unmapped-source-fields",
        action="store_true",
        help="Include non-mapped source fields as SRC_* payload fields",
    )
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
    parser.add_argument(
        "--execution-mode",
        choices=["auto", "docker", "local"],
        default="auto",
        help="Execution mode for E2E runner (default: auto)",
    )
    parser.add_argument(
        "--senzing-env",
        default=None,
        help="Optional setupEnv path for local mode (passed to run_senzing_end_to_end.py)",
    )
    parser.add_argument(
        "--output-root",
        default="output",
        help="Root directory for final artifacts (default: output)",
    )
    parser.add_argument(
        "--runtime-dir",
        default=None,
        help="Optional runtime directory (default: temporary directory outside MVP)",
    )
    parser.add_argument(
        "--keep-runtime-dir",
        action="store_true",
        help="Do not delete runtime directory after completion",
    )
    return parser.parse_args()


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def check_docker_ready() -> tuple[bool, str]:
    """Return Docker availability and a short diagnostic string."""
    if shutil.which("docker") is None:
        return False, "docker command not found"
    probe = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if probe.returncode == 0:
        return True, "docker ready"
    detail = (probe.stderr or probe.stdout or "").strip().splitlines()
    return False, detail[-1] if detail else "docker not available"


def find_new_run_dir(runs_root: Path, prefix: str) -> Path:
    run_dirs = sorted(
        [path for path in runs_root.glob(f"{prefix}_*") if path.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not run_dirs:
        raise FileNotFoundError(f"No run directory found under {runs_root} with prefix {prefix}")
    return run_dirs[0]


def copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    shutil.copy2(source, destination)
    return True


def copy_artifacts_to_output(
    output_run_dir: Path,
    mvp_root: Path,
    runtime_dir: Path,
    source_input_json: Path,
    run_dir: Path,
    mapped_output_jsonl: Path,
    field_map_json: Path,
    mapping_summary_json: Path,
    run_summary_json: Path,
) -> dict[str, str]:
    copied: dict[str, str] = {}
    technical_dir = output_run_dir / "technical output"
    technical_dir.mkdir(parents=True, exist_ok=True)

    def to_host_path(raw_path: Path) -> Path:
        raw = str(raw_path)
        if raw.startswith("/runtime/"):
            return runtime_dir / raw.removeprefix("/runtime/")
        if raw.startswith("/workspace/"):
            return mvp_root / raw.removeprefix("/workspace/")
        return raw_path

    targets = {
        source_input_json: output_run_dir / "input_source.json",
        mapped_output_jsonl: technical_dir / "mapped_output.jsonl",
        field_map_json: technical_dir / "field_map.json",
        mapping_summary_json: technical_dir / "mapping_summary.json",
        run_summary_json: technical_dir / "run_summary.json",
        run_dir / "input_normalized.jsonl": technical_dir / "input_normalized.jsonl",
    }
    run_summary_payload = json.loads(run_summary_json.read_text(encoding="utf-8"))
    artifacts = run_summary_payload.get("artifacts", {}) if isinstance(run_summary_payload.get("artifacts"), dict) else {}
    for key, destination in [
        ("management_summary_md", output_run_dir / "management_summary.md"),
        ("ground_truth_match_quality_md", output_run_dir / "ground_truth_match_quality.md"),
        ("management_summary_json", technical_dir / "management_summary.json"),
        ("ground_truth_match_quality_json", technical_dir / "ground_truth_match_quality.json"),
        ("matched_pairs_csv", technical_dir / "matched_pairs.csv"),
        ("match_stats_csv", technical_dir / "match_stats.csv"),
        ("entity_records_csv", technical_dir / "entity_records.csv"),
    ]:
        value = artifacts.get(key)
        if not value:
            continue
        targets[to_host_path(Path(str(value)))] = destination

    run_registry_candidate = mvp_root / "output" / "run_registry.csv"
    if run_registry_candidate.exists():
        targets[run_registry_candidate] = technical_dir / "run_registry.csv"

    for source, destination in targets.items():
        if copy_if_exists(source, destination):
            copied[destination.name] = str(destination.resolve())

    return copied


def main() -> int:
    args = parse_args()
    mvp_root = Path(__file__).resolve().parent
    input_json = Path(args.input_json).expanduser().resolve()

    if not input_json.exists():
        print(f"ERROR: input JSON not found: {input_json}", file=sys.stderr)
        return 2

    mapper_script = mvp_root / "partner_json_to_senzing.py"
    e2e_script = mvp_root / "run_senzing_end_to_end.py"
    missing_scripts = [str(path) for path in [mapper_script, e2e_script] if not path.exists()]
    if missing_scripts:
        print("ERROR: missing required scripts:", file=sys.stderr)
        for item in missing_scripts:
            print(f"  - {item}", file=sys.stderr)
        return 2

    ts = now_timestamp()
    output_root = (mvp_root / args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output_run_dir = output_root / ts
    output_run_dir.mkdir(parents=True, exist_ok=True)

    if args.runtime_dir:
        runtime_dir = Path(args.runtime_dir).expanduser().resolve()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_created = False
    else:
        runtime_dir = Path(tempfile.mkdtemp(prefix="mvp_runtime_"))
        runtime_created = True

    runtime_output = runtime_dir / "output"
    runtime_runs = runtime_dir / "runs"
    runtime_projects = runtime_dir / "projects"
    runtime_output.mkdir(parents=True, exist_ok=True)
    runtime_runs.mkdir(parents=True, exist_ok=True)
    runtime_projects.mkdir(parents=True, exist_ok=True)

    mapped_output_jsonl = runtime_output / f"partner_output_senzing_from_input_{ts}.jsonl"
    field_map_json = runtime_output / f"field_map_from_input_{ts}.json"
    mapping_summary_json = runtime_output / f"mapping_summary_from_input_{ts}.json"

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
        "runtime_dir": str(runtime_dir),
    }
    mapping_summary_json.write_text(json.dumps(mapping_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    docker_ready, docker_note = check_docker_ready()
    execution_mode = args.execution_mode
    if execution_mode == "docker" and not docker_ready:
        print(f"ERROR: --execution-mode docker requested but Docker is not available ({docker_note})", file=sys.stderr)
        return 2
    if execution_mode == "auto":
        execution_mode = "docker" if docker_ready else "local"

    e2e_cmd: list[str]
    if execution_mode == "docker":
        e2e_cmd = [
            "docker",
            "run",
            "--rm",
            "--platform",
            args.docker_platform,
            "-v",
            f"{mvp_root}:/workspace",
            "-v",
            f"{runtime_dir}:/runtime",
            "-w",
            "/workspace",
            args.docker_image,
            "python3",
            "/workspace/run_senzing_end_to_end.py",
            f"/runtime/output/{mapped_output_jsonl.name}",
            "--output-root",
            "/runtime/runs",
            "--run-name-prefix",
            args.run_name_prefix,
            "--project-parent-dir",
            "/runtime/projects",
            "--project-name-prefix",
            args.project_name_prefix,
            "--use-input-jsonl-directly",
            "--data-sources",
            args.data_source,
            "--step-timeout-seconds",
            str(args.step_timeout_seconds),
        ]
    else:
        e2e_cmd = [
            sys.executable,
            str(e2e_script),
            str(mapped_output_jsonl),
            "--output-root",
            str(runtime_runs),
            "--run-name-prefix",
            args.run_name_prefix,
            "--project-parent-dir",
            str(runtime_projects),
            "--project-name-prefix",
            args.project_name_prefix,
            "--use-input-jsonl-directly",
            "--data-sources",
            args.data_source,
            "--step-timeout-seconds",
            str(args.step_timeout_seconds),
        ]
        if args.senzing_env:
            e2e_cmd.extend(["--senzing-env", str(Path(args.senzing_env).expanduser().resolve())])

    if args.with_why:
        e2e_cmd.extend(["--max-explain-records", str(args.max_explain_records)])
        e2e_cmd.extend(["--max-explain-pairs", str(args.max_explain_pairs)])
    else:
        e2e_cmd.append("--skip-explain")
    if args.keep_loader_temp_files:
        e2e_cmd.append("--keep-loader-temp-files")

    mapping_summary["execution_mode"] = execution_mode
    mapping_summary["docker_probe"] = docker_note
    mapping_summary_json.write_text(json.dumps(mapping_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"E2E execution mode: {execution_mode}")
    if execution_mode == "local" and docker_note != "docker ready":
        print(f"Docker note: {docker_note}")

    run_command(e2e_cmd, mvp_root)

    run_dir = find_new_run_dir(runtime_runs, args.run_name_prefix)
    run_summary_json = run_dir / "run_summary.json"
    if not run_summary_json.exists():
        print(f"ERROR: run summary not found: {run_summary_json}", file=sys.stderr)
        return 2

    copied = copy_artifacts_to_output(
        output_run_dir=output_run_dir,
        mvp_root=mvp_root,
        runtime_dir=runtime_dir,
        source_input_json=input_json,
        run_dir=run_dir,
        mapped_output_jsonl=mapped_output_jsonl,
        field_map_json=field_map_json,
        mapping_summary_json=mapping_summary_json,
        run_summary_json=run_summary_json,
    )

    keep_runtime = args.keep_runtime_dir or not runtime_created
    if not keep_runtime:
        shutil.rmtree(runtime_dir, ignore_errors=True)

    print("\nMVP pipeline completed.")
    print(f"Input JSON: {input_json}")
    print(f"Output directory: {output_run_dir}")
    print(f"Technical directory: {output_run_dir / 'technical output'}")
    print(f"Artifacts copied: {len(copied)}")
    print(f"Mapped JSONL: {copied.get('mapped_output.jsonl')}")
    print(f"Management summary (md): {copied.get('management_summary.md')}")
    print(f"Ground truth quality (md): {copied.get('ground_truth_match_quality.md')}")
    print(f"Run summary (technical): {copied.get('run_summary.json')}")
    print(f"Run registry CSV: {copied.get('run_registry.csv')}")
    if keep_runtime:
        print(f"Runtime directory kept: {runtime_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
