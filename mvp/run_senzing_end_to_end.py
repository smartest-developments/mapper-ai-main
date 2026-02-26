#!/usr/bin/env python3
"""Run Senzing end-to-end with the same command flow used manually.

This script intentionally uses Senzing CLI tools in shell order:
1. Create project (`sz_create_project` / `G2CreateProject.py`)
2. source <project>/setupEnv
3. Configure DATA_SOURCE (`sz_configtool`)
4. Load input JSONL (`sz_file_loader`)
5. Snapshot (`sz_snapshot`)
6. Export (`sz_export -o <file>`)
7. Extract matched records from export
8. Run explain commands for matched records only (`why...`)

Input must already be Senzing-ready JSON objects (JSONL or JSON array).
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime as dt
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def now_timestamp() -> str:
    """Return timestamp suitable for directory naming."""
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def read_records(input_path: Path) -> list[dict[str, Any]]:
    """Read Senzing-ready records from JSONL or JSON array."""
    if input_path.suffix.lower() == ".jsonl":
        records: list[dict[str, Any]] = []
        with input_path.open("r", encoding="utf-8") as infile:
            for line_no, line in enumerate(infile, start=1):
                text = line.strip()
                if not text:
                    continue
                obj = json.loads(text)
                if not isinstance(obj, dict):
                    raise ValueError(f"Line {line_no} is not a JSON object")
                records.append(obj)
        return records

    with input_path.open("r", encoding="utf-8") as infile:
        data = json.load(infile)
    if not isinstance(data, list):
        raise ValueError("JSON input must be an array of objects")
    records = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Record {idx} is not a JSON object")
        records.append(item)
    return records


def run_shell_step(step_name: str, shell_command: str, log_path: Path) -> dict[str, Any]:
    """Run one shell command and store stdout/stderr into log file."""
    start = time.time()
    result = subprocess.run(
        ["bash", "-lc", shell_command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    elapsed = round(time.time() - start, 3)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as outfile:
        outfile.write(f"STEP: {step_name}\n")
        outfile.write(f"COMMAND: {shell_command}\n")
        outfile.write(f"EXIT_CODE: {result.returncode}\n")
        outfile.write(f"DURATION_SECONDS: {elapsed}\n")
        outfile.write("\n--- STDOUT ---\n")
        outfile.write(result.stdout or "")
        outfile.write("\n--- STDERR ---\n")
        outfile.write(result.stderr or "")

    return {
        "step": step_name,
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "duration_seconds": elapsed,
        "log_file": str(log_path),
        "stdout_tail": (result.stdout or "")[-1200:],
        "stderr_tail": (result.stderr or "")[-1200:],
    }


def run_shell_with_fallback(
    step_name: str,
    commands: list[str],
    log_path: Path,
) -> dict[str, Any]:
    """Try commands in order, return success of first passing command."""
    start = time.time()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    selected_command = ""
    selected_stdout = ""
    selected_stderr = ""
    selected_exit_code = 1
    ok = False

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"STEP: {step_name}\n")
        for index, command in enumerate(commands, start=1):
            result = subprocess.run(
                ["bash", "-lc", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            log.write(f"\n--- ATTEMPT {index} ---\n")
            log.write(f"COMMAND: {command}\n")
            log.write(f"EXIT_CODE: {result.returncode}\n")
            log.write("\nSTDOUT:\n")
            log.write(result.stdout or "")
            log.write("\nSTDERR:\n")
            log.write(result.stderr or "")

            selected_command = command
            selected_stdout = result.stdout or ""
            selected_stderr = result.stderr or ""
            selected_exit_code = result.returncode
            if result.returncode == 0:
                ok = True
                break

    elapsed = round(time.time() - start, 3)
    return {
        "step": step_name,
        "ok": ok,
        "exit_code": selected_exit_code,
        "duration_seconds": elapsed,
        "command_used": selected_command,
        "log_file": str(log_path),
        "stdout_tail": selected_stdout[-1200:],
        "stderr_tail": selected_stderr[-1200:],
        "stdout_full": selected_stdout,
        "stderr_full": selected_stderr,
    }


def command_available(project_setup_env: Path, command_name: str) -> bool:
    """Return True when command exists after sourcing project setupEnv."""
    cmd = (
        f"source {shlex.quote(str(project_setup_env))} >/dev/null 2>&1 && "
        f"command -v {shlex.quote(command_name)} >/dev/null 2>&1"
    )
    result = subprocess.run(
        ["bash", "-lc", cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0


def create_project(project_dir: Path, base_setup_env: Path | None, log_path: Path) -> dict[str, Any]:
    """Create an isolated project, trying preferred Senzing commands first."""
    project_dir.parent.mkdir(parents=True, exist_ok=True)
    quoted_project = shlex.quote(str(project_dir))
    base_source = (
        f"source {shlex.quote(str(base_setup_env))} >/dev/null 2>&1 && "
        if base_setup_env is not None
        else ""
    )
    attempts = [
        f"{base_source}/opt/senzing/er/bin/sz_create_project {quoted_project}",
        f"{base_source}sz_create_project {quoted_project}",
        f"{base_source}G2CreateProject.py {quoted_project}",
        f"{base_source}g2createproject.py {quoted_project}",
    ]

    combined_log = {
        "step": "create_project",
        "ok": False,
        "exit_code": 1,
        "duration_seconds": 0.0,
        "log_file": str(log_path),
        "stdout_tail": "",
        "stderr_tail": "",
    }
    start = time.time()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("STEP: create_project\n")
        log.write(f"PROJECT_DIR: {project_dir}\n")
        log.write(f"BASE_SETUP_ENV: {base_setup_env if base_setup_env else '<none>'}\n")
        for idx, command in enumerate(attempts, start=1):
            result = subprocess.run(
                ["bash", "-lc", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            log.write(f"\n--- ATTEMPT {idx} ---\n")
            log.write(f"COMMAND: {command}\n")
            log.write(f"EXIT_CODE: {result.returncode}\n")
            log.write("\nSTDOUT:\n")
            log.write(result.stdout or "")
            log.write("\nSTDERR:\n")
            log.write(result.stderr or "")

            setup_env = project_dir / "setupEnv"
            if result.returncode == 0 and setup_env.exists():
                combined_log["ok"] = True
                combined_log["exit_code"] = 0
                combined_log["stdout_tail"] = (result.stdout or "")[-1200:]
                combined_log["stderr_tail"] = (result.stderr or "")[-1200:]
                break

            combined_log["stdout_tail"] = (result.stdout or "")[-1200:]
            combined_log["stderr_tail"] = (result.stderr or "")[-1200:]

    combined_log["duration_seconds"] = round(time.time() - start, 3)
    return combined_log


def parse_args() -> argparse.Namespace:
    """Build CLI parser and return parsed args."""
    parser = argparse.ArgumentParser(description="Manual-style Senzing all-in-one runner.")
    parser.add_argument("input_file", help="Senzing-ready input (.jsonl or .json array)")
    parser.add_argument("--output-root", default="senzing_runs", help="Run artifacts root folder")
    parser.add_argument("--run-name-prefix", default="senzing_e2e", help="Run folder prefix")
    parser.add_argument(
        "--project-parent-dir",
        default="/mnt",
        help="Parent directory for isolated project (default: /mnt)",
    )
    parser.add_argument(
        "--project-name-prefix",
        default="Senzing_PoC",
        help="Isolated project name prefix (default: Senzing_PoC)",
    )
    parser.add_argument(
        "--senzing-env",
        default=None,
        help="Optional base setupEnv path. Used only to bootstrap create-project command.",
    )
    parser.add_argument("--skip-snapshot", action="store_true", help="Skip snapshot step")
    parser.add_argument("--skip-export", action="store_true", help="Skip sz_export step")
    parser.add_argument(
        "--skip-explain",
        action="store_true",
        help="Skip explain phase (whyEntityByRecordID / whyRecords)",
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
    parser.add_argument(
        "--export-output-name",
        default="entity_export.csv",
        help="Export filename inside run directory (default: entity_export.csv)",
    )
    return parser.parse_args()


def parse_int(value: Any, fallback: int = 0) -> int:
    """Parse integer values from export CSV safely."""
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    try:
        return int(text)
    except ValueError:
        return fallback


def parse_export_rows(export_file: Path) -> list[dict[str, str]]:
    """Read sz_export CSV and normalize keys and values."""
    if not export_file.exists():
        return []

    with export_file.open("r", encoding="utf-8", newline="") as infile:
        sample = infile.read(4096)
        infile.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(infile, dialect=dialect)
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized: dict[str, str] = {}
            for key, value in row.items():
                if key is None:
                    continue
                norm_key = key.strip().strip('"').strip().upper()
                norm_value = (value or "").strip().strip('"').strip()
                normalized[norm_key] = norm_value
            if normalized:
                rows.append(normalized)
    return rows


def build_match_inputs(export_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Extract matched records and matched pairs from sz_export rows."""
    first_record_by_entity: dict[str, tuple[str, str]] = {}
    anchor_by_entity: dict[str, tuple[str, str]] = {}
    matched_records: dict[tuple[str, str], dict[str, str]] = {}
    matched_pairs: dict[tuple[str, str, str, str], dict[str, str]] = {}

    for row in export_rows:
        entity_id = row.get("RESOLVED_ENTITY_ID", "")
        data_source = row.get("DATA_SOURCE", "")
        record_id = row.get("RECORD_ID", "")
        match_level = parse_int(row.get("MATCH_LEVEL", "0"), fallback=0)
        match_key = row.get("MATCH_KEY", "")

        if not entity_id or not data_source or not record_id:
            continue

        first_record_by_entity.setdefault(entity_id, (data_source, record_id))
        if match_level == 0:
            anchor_by_entity.setdefault(entity_id, (data_source, record_id))

        if match_level <= 0:
            continue

        matched_records[(data_source, record_id)] = {
            "resolved_entity_id": entity_id,
            "data_source": data_source,
            "record_id": record_id,
            "match_level": str(match_level),
            "match_key": match_key,
        }

        anchor = anchor_by_entity.get(entity_id) or first_record_by_entity.get(entity_id)
        if not anchor:
            continue
        anchor_ds, anchor_rid = anchor
        if anchor_ds == data_source and anchor_rid == record_id:
            continue

        pair_key = (anchor_ds, anchor_rid, data_source, record_id)
        matched_pairs[pair_key] = {
            "resolved_entity_id": entity_id,
            "anchor_data_source": anchor_ds,
            "anchor_record_id": anchor_rid,
            "matched_data_source": data_source,
            "matched_record_id": record_id,
            "match_level": str(match_level),
            "match_key": match_key,
        }

    return list(matched_records.values()), list(matched_pairs.values())


def try_parse_json(text: str) -> Any:
    """Parse text as JSON when possible, else return None."""
    cleaned = text.strip()
    if not cleaned:
        return None
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def make_why_entity_commands(project_setup_env: Path, data_source: str, record_id: str) -> list[str]:
    """Build command fallbacks for whyEntityByRecordID-style explain."""
    source = f"source {shlex.quote(str(project_setup_env))} >/dev/null 2>&1 && "
    ds = shlex.quote(data_source)
    rid = shlex.quote(record_id)
    return [
        f"{source}sz_why_entity_by_record_id {ds} {rid}",
        f"{source}sz_why_record_in_entity {ds} {rid}",
    ]


def make_why_records_commands(
    project_setup_env: Path,
    data_source_1: str,
    record_id_1: str,
    data_source_2: str,
    record_id_2: str,
) -> list[str]:
    """Build command fallbacks for whyRecords explain."""
    source = f"source {shlex.quote(str(project_setup_env))} >/dev/null 2>&1 && "
    ds1 = shlex.quote(data_source_1)
    rid1 = shlex.quote(record_id_1)
    ds2 = shlex.quote(data_source_2)
    rid2 = shlex.quote(record_id_2)
    return [
        f"{source}sz_why_records {ds1} {rid1} {ds2} {rid2}",
    ]


def extract_reason_summary(output_json: Any, output_text: str | None, max_items: int = 4) -> str:
    """Create a short human-readable reason summary from explain output."""
    candidates: list[str] = []
    seen: set[str] = set()

    def push(value: str) -> None:
        cleaned = " ".join(value.split())
        if not cleaned:
            return
        if len(cleaned) > 240:
            cleaned = cleaned[:237] + "..."
        if cleaned in seen:
            return
        seen.add(cleaned)
        candidates.append(cleaned)

    signal_tokens = ("MATCH", "REASON", "RULE", "FEATURE", "PRINCIPLE", "ATTRIBUTE", "WHY", "EVIDENCE")

    def walk(node: Any, key_hint: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_text = str(key)
                key_upper = key_text.upper()
                if isinstance(value, (str, int, float, bool)) and any(token in key_upper for token in signal_tokens):
                    push(f"{key_text}={value}")
                walk(value, key_text)
            return
        if isinstance(node, list):
            for item in node:
                walk(item, key_hint)
            return
        if isinstance(node, (str, int, float, bool)):
            hint_upper = key_hint.upper()
            if any(token in hint_upper for token in signal_tokens):
                push(f"{key_hint}={node}")

    if output_json is not None:
        walk(output_json)

    if not candidates and output_text:
        lines = [line.strip() for line in output_text.splitlines() if line.strip()]
        for line in lines[:max_items]:
            push(line)

    if not candidates:
        return ""
    return " | ".join(candidates[:max_items])


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """Write rows to CSV with a stable schema."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {name: row.get(name, "") for name in fieldnames}
            writer.writerow(normalized)


def make_comparison_outputs(
    run_dir: Path,
    export_rows: list[dict[str, str]],
    matched_records: list[dict[str, str]],
    matched_pairs: list[dict[str, str]],
    why_entity_results: list[dict[str, Any]],
    why_records_results: list[dict[str, Any]],
    records_input_count: int,
) -> dict[str, str | int | dict[str, int] | None]:
    """Create comparison-ready artifacts for downstream testing and management."""
    comparison_dir = run_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    entity_records_csv = comparison_dir / "entity_records.csv"
    matched_pairs_csv = comparison_dir / "matched_pairs.csv"
    match_stats_csv = comparison_dir / "match_key_stats.csv"
    management_json = comparison_dir / "management_summary.json"
    management_md = comparison_dir / "management_summary.md"

    why_entity_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for item in why_entity_results:
        rec = item.get("input", {})
        key = (str(rec.get("data_source", "")), str(rec.get("record_id", "")))
        why_entity_by_key[key] = item

    why_records_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in why_records_results:
        rec = item.get("input", {})
        key = (
            str(rec.get("anchor_data_source", "")),
            str(rec.get("anchor_record_id", "")),
            str(rec.get("matched_data_source", "")),
            str(rec.get("matched_record_id", "")),
        )
        why_records_by_key[key] = item

    entity_rows: list[dict[str, Any]] = []
    entity_ids: set[str] = set()
    for row in export_rows:
        resolved_entity_id = row.get("RESOLVED_ENTITY_ID", "")
        data_source = row.get("DATA_SOURCE", "")
        record_id = row.get("RECORD_ID", "")
        match_level = parse_int(row.get("MATCH_LEVEL", "0"), fallback=0)
        match_key = row.get("MATCH_KEY", "")
        if resolved_entity_id:
            entity_ids.add(resolved_entity_id)

        why_info = why_entity_by_key.get((data_source, record_id), {})
        reason = extract_reason_summary(
            why_info.get("output_json"),
            why_info.get("output_text"),
        )
        entity_rows.append(
            {
                "resolved_entity_id": resolved_entity_id,
                "data_source": data_source,
                "record_id": record_id,
                "match_level": match_level,
                "match_key": match_key,
                "is_anchor": 1 if match_level == 0 else 0,
                "why_entity_ok": 1 if why_info.get("ok") else 0,
                "why_entity_reason_summary": reason,
            }
        )

    pair_rows: list[dict[str, Any]] = []
    for pair in matched_pairs:
        key = (
            pair["anchor_data_source"],
            pair["anchor_record_id"],
            pair["matched_data_source"],
            pair["matched_record_id"],
        )
        why_info = why_records_by_key.get(key, {})
        reason = extract_reason_summary(
            why_info.get("output_json"),
            why_info.get("output_text"),
        )
        pair_rows.append(
            {
                "resolved_entity_id": pair["resolved_entity_id"],
                "anchor_data_source": pair["anchor_data_source"],
                "anchor_record_id": pair["anchor_record_id"],
                "matched_data_source": pair["matched_data_source"],
                "matched_record_id": pair["matched_record_id"],
                "match_level": parse_int(pair.get("match_level", "0"), fallback=0),
                "match_key": pair.get("match_key", ""),
                "why_records_ok": 1 if why_info.get("ok") else 0,
                "why_records_reason_summary": reason,
            }
        )

    match_key_counts = Counter([p.get("match_key", "") for p in matched_pairs if p.get("match_key", "")])
    match_level_counts = Counter([parse_int(p.get("match_level", "0"), fallback=0) for p in matched_pairs])

    stats_rows = [
        {"metric": "records_input", "value": records_input_count},
        {"metric": "records_exported", "value": len(export_rows)},
        {"metric": "resolved_entities", "value": len(entity_ids)},
        {"metric": "matched_records", "value": len(matched_records)},
        {"metric": "matched_pairs", "value": len(matched_pairs)},
    ]
    for level, count in sorted(match_level_counts.items()):
        stats_rows.append({"metric": f"match_level_{level}", "value": count})
    for key, count in sorted(match_key_counts.items(), key=lambda x: (-x[1], x[0])):
        stats_rows.append({"metric": f"match_key::{key}", "value": count})

    write_csv(
        entity_records_csv,
        [
            "resolved_entity_id",
            "data_source",
            "record_id",
            "match_level",
            "match_key",
            "is_anchor",
            "why_entity_ok",
            "why_entity_reason_summary",
        ],
        entity_rows,
    )
    write_csv(
        matched_pairs_csv,
        [
            "resolved_entity_id",
            "anchor_data_source",
            "anchor_record_id",
            "matched_data_source",
            "matched_record_id",
            "match_level",
            "match_key",
            "why_records_ok",
            "why_records_reason_summary",
        ],
        pair_rows,
    )
    write_csv(match_stats_csv, ["metric", "value"], stats_rows)

    summary_obj = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "records_input": records_input_count,
        "records_exported": len(export_rows),
        "resolved_entities": len(entity_ids),
        "matched_records": len(matched_records),
        "matched_pairs": len(matched_pairs),
        "match_level_distribution": {str(k): v for k, v in sorted(match_level_counts.items())},
        "match_key_distribution": dict(sorted(match_key_counts.items(), key=lambda x: (-x[1], x[0]))),
        "explain_coverage": {
            "why_entity_total": len(why_entity_results),
            "why_entity_ok": sum(1 for item in why_entity_results if item.get("ok")),
            "why_records_total": len(why_records_results),
            "why_records_ok": sum(1 for item in why_records_results if item.get("ok")),
        },
        "artifacts": {
            "entity_records_csv": str(entity_records_csv),
            "matched_pairs_csv": str(matched_pairs_csv),
            "match_stats_csv": str(match_stats_csv),
            "management_summary_md": str(management_md),
        },
    }
    management_json.write_text(json.dumps(summary_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("# Senzing Matching Summary")
    lines.append("")
    lines.append(f"- Generated at: {summary_obj['generated_at']}")
    lines.append(f"- Records input: {records_input_count}")
    lines.append(f"- Records exported: {len(export_rows)}")
    lines.append(f"- Resolved entities: {len(entity_ids)}")
    lines.append(f"- Matched records: {len(matched_records)}")
    lines.append(f"- Matched pairs: {len(matched_pairs)}")
    lines.append(
        "- Explain coverage: "
        f"whyEntity {summary_obj['explain_coverage']['why_entity_ok']}/{summary_obj['explain_coverage']['why_entity_total']}, "
        f"whyRecords {summary_obj['explain_coverage']['why_records_ok']}/{summary_obj['explain_coverage']['why_records_total']}"
    )
    lines.append("")
    lines.append("## Top Match Keys")
    lines.append("")
    lines.append("| Match Key | Count |")
    lines.append("| --- | ---: |")
    if match_key_counts:
        for key, count in sorted(match_key_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"| {key} | {count} |")
    else:
        lines.append("| (none) | 0 |")

    lines.append("")
    lines.append("## Match Level Distribution")
    lines.append("")
    lines.append("| Match Level | Count |")
    lines.append("| --- | ---: |")
    if match_level_counts:
        for level, count in sorted(match_level_counts.items()):
            lines.append(f"| {level} | {count} |")
    else:
        lines.append("| 0 | 0 |")

    lines.append("")
    lines.append("## First 20 Matched Pairs")
    lines.append("")
    lines.append("| Entity | Anchor | Matched | Match Key | Level | Explain |")
    lines.append("| --- | --- | --- | --- | ---: | --- |")
    for row in pair_rows[:20]:
        anchor = f"{row['anchor_data_source']}:{row['anchor_record_id']}"
        matched = f"{row['matched_data_source']}:{row['matched_record_id']}"
        explain_text = str(row["why_records_reason_summary"] or "").replace("\n", " ")
        lines.append(
            f"| {row['resolved_entity_id']} | {anchor} | {matched} | "
            f"{row['match_key']} | {row['match_level']} | {explain_text} |"
        )
    if not pair_rows:
        lines.append("| - | - | - | - | - | No matched pairs detected |")

    management_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "comparison_dir": str(comparison_dir),
        "entity_records_csv": str(entity_records_csv),
        "matched_pairs_csv": str(matched_pairs_csv),
        "match_stats_csv": str(match_stats_csv),
        "management_summary_json": str(management_json),
        "management_summary_md": str(management_md),
        "matched_pairs_count": len(matched_pairs),
    }


def main() -> int:
    """Entry point."""
    args = parse_args()
    input_path = Path(args.input_file).expanduser().resolve()
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 2

    base_setup_env = Path(args.senzing_env).expanduser().resolve() if args.senzing_env else None
    if base_setup_env and not base_setup_env.exists():
        print(f"ERROR: --senzing-env not found: {base_setup_env}", file=sys.stderr)
        return 2

    run_dir = Path(args.output_root).expanduser().resolve() / f"{args.run_name_prefix}_{now_timestamp()}"
    logs_dir = run_dir / "logs"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    project_dir = Path(args.project_parent_dir).expanduser() / f"{args.project_name_prefix}_{now_timestamp()}"
    project_setup_env = project_dir / "setupEnv"

    normalized_jsonl = run_dir / "input_normalized.jsonl"
    config_scripts_dir = run_dir / "config_scripts"
    snapshot_prefix = run_dir / "snapshot"
    snapshot_json = run_dir / "snapshot.json"
    export_file = run_dir / args.export_output_name
    explain_dir = run_dir / "explain"
    explain_logs_dir = explain_dir / "logs"
    match_inputs_file = explain_dir / "match_inputs.json"
    why_entity_file = explain_dir / "why_entity_by_record.jsonl"
    why_records_file = explain_dir / "why_records_pairs.jsonl"
    summary_file = run_dir / "run_summary.json"
    comparison_artifacts: dict[str, str | int | dict[str, int] | None] = {}

    print(f"Run directory: {run_dir}")
    print(f"Input file: {input_path}")
    print(f"Project dir: {project_dir}")

    try:
        records = read_records(input_path)
    except Exception as err:  # pylint: disable=broad-exception-caught
        print(f"ERROR: Unable to parse input: {err}", file=sys.stderr)
        return 2
    if not records:
        print("ERROR: Input contains no records.", file=sys.stderr)
        return 2

    data_sources = sorted({str(r.get("DATA_SOURCE", "")).strip() for r in records if str(r.get("DATA_SOURCE", "")).strip()})
    if not data_sources:
        print("ERROR: No DATA_SOURCE found in input records.", file=sys.stderr)
        return 2

    with normalized_jsonl.open("w", encoding="utf-8") as outfile:
        for record in records:
            outfile.write(json.dumps(record, ensure_ascii=False) + "\n")

    config_scripts_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    step = create_project(project_dir, base_setup_env, logs_dir / "00_create_project.log")
    steps.append(step)
    if not step["ok"] or not project_setup_env.exists():
        summary = {
            "overall_ok": False,
            "error": "create_project failed",
            "run_directory": str(run_dir),
            "project_dir": str(project_dir),
            "steps": steps,
        }
        summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("FAILED at create_project", file=sys.stderr)
        return 1

    for index, data_source in enumerate(data_sources, start=1):
        cfg_file = config_scripts_dir / f"add_{data_source}.g2c"
        cfg_file.write_text(f"addDataSource {data_source}\nsave\n", encoding="utf-8")
        command = (
            f"source {shlex.quote(str(project_setup_env))} >/dev/null 2>&1 && "
            f"sz_configtool -f {shlex.quote(str(cfg_file))}"
        )
        step = run_shell_step(
            f"configure_data_source_{data_source}",
            command,
            logs_dir / f"01_configure_{index:02d}_{data_source}.log",
        )
        steps.append(step)
        if not step["ok"]:
            stdout = (step.get("stdout_tail") or "").lower()
            stderr = (step.get("stderr_tail") or "").lower()
            already_exists = "already" in stdout or "already" in stderr or "exist" in stdout or "exist" in stderr
            if not already_exists:
                summary = {
                    "overall_ok": False,
                    "error": f"configure_data_source failed for {data_source}",
                    "run_directory": str(run_dir),
                    "project_dir": str(project_dir),
                    "steps": steps,
                }
                summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print(f"FAILED at configure_data_source_{data_source}", file=sys.stderr)
                return 1

    load_cmd = (
        f"source {shlex.quote(str(project_setup_env))} >/dev/null 2>&1 && "
        f"sz_file_loader -f {shlex.quote(str(normalized_jsonl))}"
    )
    step = run_shell_step("load_records", load_cmd, logs_dir / "02_load.log")
    steps.append(step)
    if not step["ok"]:
        summary = {
            "overall_ok": False,
            "error": "load_records failed",
            "run_directory": str(run_dir),
            "project_dir": str(project_dir),
            "steps": steps,
        }
        summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("FAILED at load_records", file=sys.stderr)
        return 1

    if not args.skip_snapshot:
        snapshot_cmd = (
            f"source {shlex.quote(str(project_setup_env))} >/dev/null 2>&1 && "
            f"sz_snapshot -o {shlex.quote(str(snapshot_prefix))} -Q"
        )
        step = run_shell_step("snapshot", snapshot_cmd, logs_dir / "03_snapshot.log")
        steps.append(step)
        if not step["ok"]:
            summary = {
                "overall_ok": False,
                "error": "snapshot failed",
                "run_directory": str(run_dir),
                "project_dir": str(project_dir),
                "steps": steps,
            }
            summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print("FAILED at snapshot", file=sys.stderr)
            return 1

        candidates = sorted(run_dir.glob("snapshot*.json"))
        if candidates:
            candidates[0].replace(snapshot_json)

    if not args.skip_export:
        export_cmd = (
            f"source {shlex.quote(str(project_setup_env))} >/dev/null 2>&1 && "
            f"sz_export -o {shlex.quote(str(export_file))}"
        )
        step = run_shell_step("export", export_cmd, logs_dir / "04_export.log")
        steps.append(step)
        if not step["ok"]:
            summary = {
                "overall_ok": False,
                "error": "export failed",
                "run_directory": str(run_dir),
                "project_dir": str(project_dir),
                "steps": steps,
            }
            summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print("FAILED at export", file=sys.stderr)
            return 1

    export_rows: list[dict[str, str]] = parse_export_rows(export_file) if export_file.exists() else []
    matched_records: list[dict[str, str]] = []
    matched_pairs: list[dict[str, str]] = []
    if export_rows:
        matched_records, matched_pairs = build_match_inputs(export_rows)

    why_entity_results: list[dict[str, Any]] = []
    why_records_results: list[dict[str, Any]] = []

    explain_summary: dict[str, Any] = {
        "enabled": not args.skip_explain,
        "status": "skipped" if args.skip_explain else "not_started",
        "matched_records_detected": len(matched_records),
        "matched_pairs_detected": len(matched_pairs),
        "why_entity_attempted": 0,
        "why_entity_ok": 0,
        "why_records_attempted": 0,
        "why_records_ok": 0,
        "warnings": [],
    }

    if not args.skip_explain:
        if args.skip_export or not export_file.exists():
            explain_summary["status"] = "skipped_no_export"
            explain_summary["warnings"].append(
                "Explain skipped because export file is missing (export skipped or failed)."
            )
        else:
            explain_dir.mkdir(parents=True, exist_ok=True)
            explain_logs_dir.mkdir(parents=True, exist_ok=True)

            why_entity_available = command_available(project_setup_env, "sz_why_entity_by_record_id") or command_available(
                project_setup_env,
                "sz_why_record_in_entity",
            )
            why_records_available = command_available(project_setup_env, "sz_why_records")

            match_inputs_file.write_text(
                json.dumps(
                    {
                        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                        "matched_records_detected": len(matched_records),
                        "matched_pairs_detected": len(matched_pairs),
                        "matched_records": matched_records,
                        "matched_pairs": matched_pairs,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            explain_summary["status"] = "done"
            if len(matched_records) > args.max_explain_records:
                explain_summary["warnings"].append(
                    f"Matched records limited from {len(matched_records)} to {args.max_explain_records}."
                )
                matched_records = matched_records[: args.max_explain_records]
            if len(matched_pairs) > args.max_explain_pairs:
                explain_summary["warnings"].append(
                    f"Matched pairs limited from {len(matched_pairs)} to {args.max_explain_pairs}."
                )
                matched_pairs = matched_pairs[: args.max_explain_pairs]

            if why_entity_available:
                with why_entity_file.open("w", encoding="utf-8") as outfile:
                    for index, rec in enumerate(matched_records, start=1):
                        ds = rec["data_source"]
                        rid = rec["record_id"]
                        commands = make_why_entity_commands(project_setup_env, ds, rid)
                        step = run_shell_with_fallback(
                            step_name=f"why_entity_by_record_{index:04d}",
                            commands=commands,
                            log_path=explain_logs_dir / f"why_entity_{index:04d}.log",
                        )
                        steps.append(step)
                        explain_summary["why_entity_attempted"] += 1
                        if step["ok"]:
                            explain_summary["why_entity_ok"] += 1

                        stdout = step.get("stdout_full", "")
                        parsed = try_parse_json(stdout)
                        item = {
                            "index": index,
                            "input": rec,
                            "ok": step["ok"],
                            "command_used": step.get("command_used"),
                            "log_file": step.get("log_file"),
                            "output_json": parsed,
                            "output_text": None if parsed is not None else stdout.strip(),
                            "stderr": (step.get("stderr_full") or "").strip() or None,
                        }
                        why_entity_results.append(item)
                        outfile.write(json.dumps(item, ensure_ascii=False) + "\n")
            else:
                explain_summary["warnings"].append(
                    "Explain entity step skipped: no supported why-entity command found in this Senzing environment."
                )

            if why_records_available:
                with why_records_file.open("w", encoding="utf-8") as outfile:
                    for index, pair in enumerate(matched_pairs, start=1):
                        ds1 = pair["anchor_data_source"]
                        rid1 = pair["anchor_record_id"]
                        ds2 = pair["matched_data_source"]
                        rid2 = pair["matched_record_id"]
                        commands = make_why_records_commands(project_setup_env, ds1, rid1, ds2, rid2)
                        step = run_shell_with_fallback(
                            step_name=f"why_records_{index:04d}",
                            commands=commands,
                            log_path=explain_logs_dir / f"why_records_{index:04d}.log",
                        )
                        steps.append(step)
                        explain_summary["why_records_attempted"] += 1
                        if step["ok"]:
                            explain_summary["why_records_ok"] += 1

                        stdout = step.get("stdout_full", "")
                        parsed = try_parse_json(stdout)
                        item = {
                            "index": index,
                            "input": pair,
                            "ok": step["ok"],
                            "command_used": step.get("command_used"),
                            "log_file": step.get("log_file"),
                            "output_json": parsed,
                            "output_text": None if parsed is not None else stdout.strip(),
                            "stderr": (step.get("stderr_full") or "").strip() or None,
                        }
                        why_records_results.append(item)
                        outfile.write(json.dumps(item, ensure_ascii=False) + "\n")
            else:
                explain_summary["warnings"].append(
                    "Explain pair step skipped: sz_why_records not found in this Senzing environment."
                )

            if explain_summary["why_entity_attempted"] > 0 and explain_summary["why_entity_ok"] == 0:
                explain_summary["warnings"].append(
                    "No why-entity command succeeded. Check Senzing command availability in this environment."
                )
            if explain_summary["why_records_attempted"] > 0 and explain_summary["why_records_ok"] == 0:
                explain_summary["warnings"].append(
                    "No why-records command succeeded. Check Senzing command availability in this environment."
                )

    if export_rows:
        comparison_artifacts = make_comparison_outputs(
            run_dir=run_dir,
            export_rows=export_rows,
            matched_records=matched_records,
            matched_pairs=matched_pairs,
            why_entity_results=why_entity_results,
            why_records_results=why_records_results,
            records_input_count=len(records),
        )

    summary = {
        "overall_ok": True,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "input_file": str(input_path),
        "project_dir": str(project_dir),
        "project_setup_env": str(project_setup_env),
        "run_directory": str(run_dir),
        "records_input": len(records),
        "data_sources": data_sources,
        "artifacts": {
            "normalized_jsonl": str(normalized_jsonl),
            "config_scripts_dir": str(config_scripts_dir),
            "snapshot_json": str(snapshot_json) if snapshot_json.exists() else None,
            "export_file": str(export_file) if export_file.exists() else None,
            "explain_dir": str(explain_dir) if explain_dir.exists() else None,
            "match_inputs_file": str(match_inputs_file) if match_inputs_file.exists() else None,
            "why_entity_file": str(why_entity_file) if why_entity_file.exists() else None,
            "why_records_file": str(why_records_file) if why_records_file.exists() else None,
            "comparison_dir": comparison_artifacts.get("comparison_dir"),
            "entity_records_csv": comparison_artifacts.get("entity_records_csv"),
            "matched_pairs_csv": comparison_artifacts.get("matched_pairs_csv"),
            "match_stats_csv": comparison_artifacts.get("match_stats_csv"),
            "management_summary_json": comparison_artifacts.get("management_summary_json"),
            "management_summary_md": comparison_artifacts.get("management_summary_md"),
            "logs_dir": str(logs_dir),
        },
        "explain": explain_summary,
        "comparison": comparison_artifacts,
        "steps": steps,
    }
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Pipeline complete. Success=True")
    print(f"Summary: {summary_file}")
    print(f"Project: {project_dir}")
    print(f"Artifacts: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
