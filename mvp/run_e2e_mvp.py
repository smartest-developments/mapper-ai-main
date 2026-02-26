#!/usr/bin/env python3
"""Single-folder MVP launcher for Senzing end-to-end execution."""

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
        default="sample_senzing_ready.jsonl",
        help="Input JSONL path (default: mvp/sample_senzing_ready.jsonl)",
    )
    parser.add_argument(
        "--output-root",
        default="/mnt/senzing_runs",
        help="Run artifacts root folder (default: /mnt/senzing_runs)",
    )
    parser.add_argument(
        "--project-parent-dir",
        default="/mnt",
        help="Parent directory for isolated Senzing projects (default: /mnt)",
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
    core_script = mvp_dir / "run_senzing_end_to_end.py"
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

    cmd = [
        sys.executable,
        str(core_script),
        str(input_path),
        "--project-parent-dir",
        str(Path(args.project_parent_dir).expanduser()),
        "--output-root",
        str(Path(args.output_root).expanduser()),
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
