# Senzing E2E Runner

## Purpose

Run Senzing from A to Z for one JSONL input:

- create isolated project,
- configure data source,
- load records,
- snapshot,
- export (`sz_export`),
- explain on matched records,
- comparison artifacts for analytics.

## Script

- `run_senzing_e2e.py` (wrapper)
- Delegates to: `/Users/simones/Developer/mapper-ai-main/senzing/all_in_one/run_senzing_end_to_end.py`

## Command

```bash
python3 /Users/simones/Developer/mapper-ai-main/senzing/workflows/e2e_runner/run_senzing_e2e.py \
  /path/to/input_senzing_ready.jsonl
```

## Main Artifacts

Inside the generated run folder:

- `entity_export.csv`
- `explain/why_entity_by_record.jsonl`
- `explain/why_records_pairs.jsonl`
- `comparison/entity_records.csv`
- `comparison/matched_pairs.csv`
- `comparison/management_summary.md`
- `run_summary.json`
