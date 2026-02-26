#!/usr/bin/env python3
"""Run one end-to-end management pipeline from sample generation to reports.

Flow:
1) Generate realistic source sample + mapped JSONL.
2) Run Senzing E2E in Docker.
3) Print key management artifact paths.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run sample generation and Senzing management reports in one command.")
    parser.add_argument("--records", type=int, default=500, help="Number of generated records (default: 500)")
    parser.add_argument("--person-ratio", type=float, default=0.70, help="Share of PERSON records (default: 0.70)")
    parser.add_argument("--ipg-rate", type=float, default=0.35, help="Share of records with IPG ID (default: 0.35)")
    parser.add_argument("--seed", type=int, default=20260226, help="Random seed (default: 20260226)")
    parser.add_argument("--sample-dir", default="sample", help="Sample directory (default: sample)")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--runs-root", default=".senzing_runs_test", help="E2E run root (default: .senzing_runs_test)")
    parser.add_argument(
        "--projects-root",
        default=".senzing_projects_test",
        help="Senzing project root (default: .senzing_projects_test)",
    )
    parser.add_argument("--run-name-prefix", default="run_full_mgmt", help="Run folder prefix")
    parser.add_argument("--project-name-prefix", default="Senzing_PoC_FULL", help="Project folder prefix")
    parser.add_argument(
        "--docker-image",
        default="mapper-senzing-poc:4.2.1",
        help="Docker image with Senzing binaries (default: mapper-senzing-poc:4.2.1)",
    )
    parser.add_argument(
        "--docker-platform",
        default="linux/amd64",
        help="Docker platform (default: linux/amd64)",
    )
    parser.add_argument("--step-timeout-seconds", type=int, default=1800, help="E2E step timeout seconds")
    parser.add_argument(
        "--keep-loader-temp-files",
        action="store_true",
        help="Keep sz_file_loader temporary shuffle files",
    )
    parser.add_argument(
        "--fast-mode",
        action="store_true",
        help="Enable fast mode (skip snapshot/export/explain/comparison)",
    )
    return parser.parse_args()


def to_container_path(repo_root: Path, host_path: Path) -> Path:
    """Convert host workspace path into /workspace container path."""
    resolved_root = repo_root.resolve()
    resolved_host = host_path.resolve()
    rel = resolved_host.relative_to(resolved_root)
    return Path("/workspace") / rel


def find_new_generation_summary(output_dir: Path, before: set[Path]) -> Path:
    """Find generation summary created by the current generation run."""
    after = set(output_dir.glob("generation_summary_*.json"))
    created = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if created:
        return created[0]
    fallback = sorted(after, key=lambda p: p.stat().st_mtime, reverse=True)
    if not fallback:
        raise FileNotFoundError("No generation_summary_*.json found in output directory")
    return fallback[0]


def find_new_run_dir(runs_root: Path, before: set[Path], prefix: str) -> Path:
    """Find newly created E2E run directory."""
    after = set(path for path in runs_root.glob(f"{prefix}_*") if path.is_dir())
    created = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if created:
        return created[0]
    fallback = sorted(after, key=lambda p: p.stat().st_mtime, reverse=True)
    if not fallback:
        raise FileNotFoundError(f"No run directory found under {runs_root} with prefix {prefix}")
    return fallback[0]


def run_subprocess(command: list[str], cwd: Path) -> None:
    """Run one command and stream output; fail hard on non-zero exit code."""
    subprocess.run(command, cwd=str(cwd), check=True)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    sample_dir = (repo_root / args.sample_dir).resolve()
    output_dir = (repo_root / args.output_dir).resolve()
    runs_root = (repo_root / args.runs_root).resolve()
    projects_root = (repo_root / args.projects_root).resolve()
    sample_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_root.mkdir(parents=True, exist_ok=True)
    projects_root.mkdir(parents=True, exist_ok=True)

    generation_script = repo_root / "senzing" / "tools" / "generate_realistic_partner_dataset.py"
    e2e_wrapper = repo_root / "senzing" / "workflows" / "e2e_runner" / "run_senzing_e2e.py"

    summaries_before = set(output_dir.glob("generation_summary_*.json"))
    generate_cmd = [
        sys.executable,
        str(generation_script),
        "--records",
        str(args.records),
        "--person-ratio",
        str(args.person_ratio),
        "--ipg-rate",
        str(args.ipg_rate),
        "--seed",
        str(args.seed),
        "--sample-dir",
        str(Path(args.sample_dir)),
        "--output-dir",
        str(Path(args.output_dir)),
    ]
    run_subprocess(generate_cmd, repo_root)

    generation_summary_path = find_new_generation_summary(output_dir, summaries_before)
    generation_summary = json.loads(generation_summary_path.read_text(encoding="utf-8"))
    mapped_output_jsonl = Path(str(generation_summary.get("mapped_output_jsonl") or "")).resolve()
    if not mapped_output_jsonl.exists():
        print(f"ERROR: mapped_output_jsonl not found: {mapped_output_jsonl}", file=sys.stderr)
        return 2

    runs_before = set(path for path in runs_root.glob(f"{args.run_name_prefix}_*") if path.is_dir())
    container_input_jsonl = to_container_path(repo_root, mapped_output_jsonl)
    container_runs_root = to_container_path(repo_root, runs_root)
    container_projects_root = to_container_path(repo_root, projects_root)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--platform",
        args.docker_platform,
        "-v",
        f"{repo_root}:/workspace",
        "-w",
        "/workspace",
        args.docker_image,
        "python3",
        str(to_container_path(repo_root, e2e_wrapper)),
        str(container_input_jsonl),
        "--output-root",
        str(container_runs_root),
        "--run-name-prefix",
        args.run_name_prefix,
        "--project-parent-dir",
        str(container_projects_root),
        "--project-name-prefix",
        args.project_name_prefix,
        "--max-explain-records",
        "0",
        "--max-explain-pairs",
        "0",
        "--step-timeout-seconds",
        str(args.step_timeout_seconds),
    ]
    if args.keep_loader_temp_files:
        docker_cmd.append("--keep-loader-temp-files")
    if args.fast_mode:
        docker_cmd.extend(["--fast-mode", "--data-sources", "PARTNERS"])

    run_subprocess(docker_cmd, repo_root)

    run_dir = find_new_run_dir(runs_root, runs_before, args.run_name_prefix)
    run_summary_path = run_dir / "run_summary.json"
    run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    artifacts = run_summary.get("artifacts", {})

    print("")
    print("Unified pipeline completed.")
    print(f"Generation summary: {generation_summary_path}")
    print(f"Run summary: {run_summary_path}")
    print(f"Management summary (md): {artifacts.get('management_summary_md')}")
    print(f"Ground truth quality (md): {artifacts.get('ground_truth_match_quality_md')}")
    print(f"Run registry CSV: {artifacts.get('run_registry_csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
