#!/usr/bin/env python3
"""Single-folder MVP launcher for Senzing end-to-end execution.

This script keeps all runtime artifacts under ./mvp to minimize folder spread.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Senzing end-to-end with MVP defaults.")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="input/sample_senzing_ready.jsonl",
        help="Input JSONL path (default: mvp/input/sample_senzing_ready.jsonl)",
    )
    parser.add_argument(
        "--skip-snapshot",
        action="store_true",
        help="Skip snapshot step",
    )
    parser.add_argument(
        "--skip-explain",
        action="store_true",
        help="Skip explain step",
    )
    parser.add_argument(
        "--max-explain-records",
        type=int,
        default=200,
        help="Maximum matched records to explain (default: 200)",
    )
    parser.add_argument(
        "--max-explain-pairs",
        type=int,
        default=200,
        help="Maximum matched pairs to explain (default: 200)",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    mvp_dir = Path(__file__).resolve().parent
    repo_root = mvp_dir.parent
    core_script = mvp_dir / "bin" / "run_senzing_end_to_end.py"
    if not core_script.exists():
        # Fallback for development mode.
        core_script = repo_root / "senzing" / "all_in_one" / "run_senzing_end_to_end.py"

    if not core_script.exists():
        print(f"ERROR: Core runner not found: {core_script}", file=sys.stderr)
        return 2

    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = mvp_dir / input_path
    input_path = input_path.resolve()

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 2

    runs_dir = mvp_dir / "runs"
    projects_dir = mvp_dir / "projects"
    runs_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(core_script),
        str(input_path),
        "--project-parent-dir",
        str(projects_dir),
        "--output-root",
        str(runs_dir),
        "--run-name-prefix",
        "run",
        "--project-name-prefix",
        "project",
        "--max-explain-records",
        str(args.max_explain_records),
        "--max-explain-pairs",
        str(args.max_explain_pairs),
    ]

    if args.skip_snapshot:
        cmd.append("--skip-snapshot")
    if args.skip_explain:
        cmd.append("--skip-explain")

    print("Executing:")
    print(" ".join(cmd))

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
