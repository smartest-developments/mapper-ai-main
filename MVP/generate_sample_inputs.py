#!/usr/bin/env python3
"""Generate curated MVP sample_input JSON files (all 500 records, with top-level comment metadata)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROFILES: list[dict[str, Any]] = [
    {
        "filename": "sample_01_legacy_baseline_500.json",
        "description": "Legacy baseline sample kept for continuity with previous MVP runs.",
        "features": [
            "original 500-record baseline",
            "mixed PERSON/ORGANIZATION",
            "default sparsity pattern",
        ],
        "source": "legacy",
    },
    {
        "filename": "sample_02_balanced_baseline_500.json",
        "description": "Balanced baseline with default realism and moderate IPG coverage.",
        "features": ["balanced person/org split", "moderate missing fields", "standard noise"],
        "seed": 2027101,
        "person_ratio": 0.70,
        "ipg_rate": 0.35,
        "mutations": [],
    },
    {
        "filename": "sample_03_sparse_fields_500.json",
        "description": "High sparsity scenario with many optional fields missing.",
        "features": ["aggressive null optional fields", "harder matching due to low completeness"],
        "seed": 2027102,
        "person_ratio": 0.70,
        "ipg_rate": 0.30,
        "mutations": ["sparse"],
    },
    {
        "filename": "sample_04_name_noise_500.json",
        "description": "Name formatting noise (case/punctuation/spacing variations).",
        "features": ["name normalization stress", "formatting inconsistencies"],
        "seed": 2027103,
        "person_ratio": 0.72,
        "ipg_rate": 0.35,
        "mutations": ["name_noise"],
    },
    {
        "filename": "sample_05_taxid_noise_500.json",
        "description": "Tax ID quality issues with malformed identifiers on a subset of records.",
        "features": ["identifier quality degradation", "weaker deterministic signals"],
        "seed": 2027104,
        "person_ratio": 0.68,
        "ipg_rate": 0.35,
        "mutations": ["tax_noise"],
    },
    {
        "filename": "sample_06_address_noise_500.json",
        "description": "Address inconsistencies and partial address drops.",
        "features": ["address quality stress", "missing residence/street/postal values"],
        "seed": 2027105,
        "person_ratio": 0.70,
        "ipg_rate": 0.35,
        "mutations": ["address_noise"],
    },
    {
        "filename": "sample_07_duplicate_pressure_500.json",
        "description": "Higher duplicate pressure by making subsets look near-identical.",
        "features": ["larger ambiguous clusters", "false positive/negative pressure"],
        "seed": 2027106,
        "person_ratio": 0.70,
        "ipg_rate": 0.35,
        "mutations": ["duplicate_pressure"],
    },
    {
        "filename": "sample_08_organization_heavy_500.json",
        "description": "Organization-heavy dataset with more corporate records than persons.",
        "features": ["organization-heavy", "different identifier mix"],
        "seed": 2027107,
        "person_ratio": 0.40,
        "ipg_rate": 0.32,
        "mutations": [],
    },
    {
        "filename": "sample_09_person_heavy_low_ipg_500.json",
        "description": "Person-heavy dataset with low SOURCE IPG labeling coverage.",
        "features": ["person-heavy", "low IPG labels"],
        "seed": 2027108,
        "person_ratio": 0.88,
        "ipg_rate": 0.15,
        "mutations": [],
    },
    {
        "filename": "sample_10_high_ipg_coverage_500.json",
        "description": "High SOURCE IPG coverage for comparison against lower-labeling scenarios.",
        "features": ["high IPG labels", "quality evaluation easier"],
        "seed": 2027109,
        "person_ratio": 0.70,
        "ipg_rate": 0.65,
        "mutations": [],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate curated sample_input files for MVP")
    parser.add_argument("--records", type=int, default=500, help="Records per sample (default: 500)")
    parser.add_argument("--sample-dir", default="sample_input", help="Sample input directory under MVP")
    parser.add_argument("--output-dir", default="output", help="Output directory for generator metadata")
    return parser.parse_args()


def run_generator(repo_root: Path, sample_dir_arg: str, output_dir_arg: str, records: int, seed: int, person_ratio: float, ipg_rate: float) -> Path:
    cmd = [
        sys.executable,
        str(repo_root / "senzing/tools/generate_realistic_partner_dataset.py"),
        "--records",
        str(records),
        "--seed",
        str(seed),
        "--person-ratio",
        str(person_ratio),
        "--ipg-rate",
        str(ipg_rate),
        "--sample-dir",
        sample_dir_arg,
        "--output-dir",
        output_dir_arg,
        "--skip-mapper",
    ]
    before = {p for p in (repo_root / sample_dir_arg).glob(f"partner_input_realistic_{records}_*.json")}
    subprocess.run(cmd, cwd=str(repo_root), check=True)
    after = {p for p in (repo_root / sample_dir_arg).glob(f"partner_input_realistic_{records}_*.json")}
    created = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if not created:
        # fallback: pick most recent matching file
        candidates = sorted(after, key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError("No generated sample file found")
        return candidates[0]
    return created[0]


def maybe(rng: random.Random, probability: float) -> bool:
    return rng.random() < probability


def apply_sparse(records: list[dict[str, Any]], rng: random.Random) -> None:
    optional_fields = [
        "legal_first_name",
        "additional_name",
        "birth_or_foundation_date",
        "prime_nationality_country_code",
        "address_street_name",
        "address_residence_identifier",
        "address_postal_code",
        "address_postal_city_name",
        "lei",
        "lem_id",
        "crn",
        "tax_id",
        "id_document_number",
        "electronic_address",
    ]
    for record in records:
        for key in optional_fields:
            if key in record and maybe(rng, 0.30):
                record[key] = None


def apply_name_noise(records: list[dict[str, Any]], rng: random.Random) -> None:
    for record in records:
        name = record.get("partner_name")
        if not isinstance(name, str) or not name.strip() or not maybe(rng, 0.35):
            continue
        variant = rng.choice([
            name.upper(),
            name.lower(),
            f" {name} ",
            name.replace(" ", "  "),
            name.replace(",", "").replace(".", ""),
        ])
        record["partner_name"] = variant


def apply_tax_noise(records: list[dict[str, Any]], rng: random.Random) -> None:
    for record in records:
        if not maybe(rng, 0.22):
            continue
        tax_id = record.get("tax_id")
        if not tax_id:
            continue
        if maybe(rng, 0.50):
            record["tax_id"] = str(tax_id).replace("-", "").replace(" ", "")[:6]
        else:
            record["tax_id"] = f"BAD-{rng.randint(100,999)}"


def apply_address_noise(records: list[dict[str, Any]], rng: random.Random) -> None:
    for record in records:
        if maybe(rng, 0.30):
            record["address_street_name"] = None
        if maybe(rng, 0.28):
            record["address_postal_city_name"] = None
        if maybe(rng, 0.24):
            record["address_postal_code"] = None
        if isinstance(record.get("address_residence_identifier"), str) and maybe(rng, 0.20):
            record["address_residence_identifier"] = f" {record['address_residence_identifier']} "


def apply_duplicate_pressure(records: list[dict[str, Any]], rng: random.Random) -> None:
    if len(records) < 60:
        return
    indices = list(range(len(records)))
    rng.shuffle(indices)
    targets = indices[:60]
    sources = indices[60:120]
    if len(sources) < len(targets):
        sources = (sources * ((len(targets) // max(1, len(sources))) + 1))[: len(targets)]
    for target_idx, source_idx in zip(targets, sources):
        source = records[source_idx]
        target = records[target_idx]
        # Keep business IDs untouched, overwrite match-relevant content.
        for key in [
            "partner_name",
            "legal_first_name",
            "additional_name",
            "birth_or_foundation_date",
            "address_street_name",
            "address_residence_identifier",
            "address_postal_code",
            "address_postal_city_name",
            "tax_id",
            "id_document_number",
            "electronic_address",
            "prime_nationality_country_code",
            "lei",
            "lem_id",
            "crn",
        ]:
            target[key] = source.get(key)
        if isinstance(target.get("partner_name"), str) and maybe(rng, 0.60):
            target["partner_name"] = target["partner_name"].replace("  ", " ").strip()


MUTATORS = {
    "sparse": apply_sparse,
    "name_noise": apply_name_noise,
    "tax_noise": apply_tax_noise,
    "address_noise": apply_address_noise,
    "duplicate_pressure": apply_duplicate_pressure,
}


def ensure_array(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise TypeError("Expected array JSON payload")
    if not all(isinstance(item, dict) for item in payload):
        raise TypeError("Expected array of object records")
    return payload


def load_existing_legacy_records(sample_dir: Path, expected_count: int) -> list[dict[str, Any]] | None:
    legacy_path = sample_dir / "sample_01_legacy_baseline_500.json"
    if not legacy_path.exists():
        return None
    try:
        payload = json.loads(legacy_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if isinstance(payload, list):
        records = ensure_array(payload)
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        records = ensure_array(payload["records"])
    else:
        return None

    if len(records) != expected_count:
        return None
    return records


def wrap_sample(filename: str, description: str, features: list[str], records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "_sample_name": filename.removesuffix(".json"),
        "_sample_comment": description,
        "_sample_special_features": features,
        "_records_count": len(records),
        "_generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "records": records,
    }


def write_catalog(sample_dir: Path, profiles: list[dict[str, Any]]) -> None:
    lines = ["# Sample Input Catalog", "", "All files contain 500 records in JSON format with top-level metadata and `records` array.", ""]
    for idx, profile in enumerate(profiles, start=1):
        lines.append(f"{idx}. `{profile['filename']}`")
        lines.append(f"   - {profile['description']}")
        lines.append(f"   - Features: {', '.join(profile['features'])}")
    (sample_dir / "SAMPLE_CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.records <= 0:
        print("ERROR: --records must be > 0", file=sys.stderr)
        return 2

    mvp_root = Path(__file__).resolve().parent
    repo_root = mvp_root.parent
    sample_dir = (mvp_root / args.sample_dir).resolve()
    sample_dir.mkdir(parents=True, exist_ok=True)

    legacy_records = load_existing_legacy_records(sample_dir, args.records)

    # Keep only current curated artifacts in sample_input.
    for path in sorted(sample_dir.glob("*.json")):
        path.unlink(missing_ok=True)
    for archive_dir in sorted(sample_dir.glob("archive_raw_*")):
        if archive_dir.is_dir():
            shutil.rmtree(archive_dir)

    temp_sample_arg = f"{mvp_root.relative_to(repo_root)}/sample_input"
    output_arg = f"{mvp_root.relative_to(repo_root)}/{args.output_dir}"

    generated_files: list[Path] = []

    for profile in PROFILES:
        filename = profile["filename"]

        if profile.get("source") == "legacy":
            if legacy_records is None:
                print("WARNING: legacy baseline not found; generating fresh baseline for sample_01")
                generated = run_generator(
                    repo_root=repo_root,
                    sample_dir_arg=temp_sample_arg,
                    output_dir_arg=output_arg,
                    records=args.records,
                    seed=2027100,
                    person_ratio=0.70,
                    ipg_rate=0.35,
                )
                array_data = ensure_array(json.loads(generated.read_text(encoding="utf-8")))
            else:
                array_data = legacy_records
        else:
            generated = run_generator(
                repo_root=repo_root,
                sample_dir_arg=temp_sample_arg,
                output_dir_arg=output_arg,
                records=args.records,
                seed=int(profile["seed"]),
                person_ratio=float(profile["person_ratio"]),
                ipg_rate=float(profile["ipg_rate"]),
            )
            array_data = ensure_array(json.loads(generated.read_text(encoding="utf-8")))

        if len(array_data) != args.records:
            raise ValueError(f"Sample {filename} has {len(array_data)} records, expected {args.records}")

        rng = random.Random(int(profile.get("seed", 2027000)))
        for mutation_name in profile.get("mutations", []):
            mutator = MUTATORS.get(mutation_name)
            if mutator is None:
                raise KeyError(f"Unknown mutation: {mutation_name}")
            mutator(array_data, rng)

        wrapped = wrap_sample(
            filename=filename,
            description=profile["description"],
            features=profile["features"],
            records=array_data,
        )

        target = sample_dir / filename
        target.write_text(json.dumps(wrapped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        generated_files.append(target)

    write_catalog(sample_dir, PROFILES)

    # Remove raw temporary generator outputs.
    for raw_path in sorted(sample_dir.glob("partner_input_realistic_*.json")):
        raw_path.unlink(missing_ok=True)

    print(f"Generated curated samples: {len(generated_files)}")
    for path in generated_files:
        print(f"- {path}")
    print(f"Catalog: {sample_dir / 'SAMPLE_CATALOG.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
