# Senzing Workflows (Organized)

This folder contains the three operational scripts separated by responsibility.

## Folders

- `mapper/`: Convert production JSON data into Senzing-ready JSONL.
- `e2e_runner/`: Create isolated Senzing project, load data, export, explain, comparison outputs.
- `testing/`: Run automated management test cases (10 tests) on one run directory.

## Typical End-to-End Usage

1. Build Senzing-ready JSONL:

```bash
python3 senzing/workflows/mapper/run_mapper_jsonl.py \
  /path/to/production_input.json \
  /path/to/production_output.jsonl \
  --data-source PARTNERS
```

2. Run Senzing project + export + comparison:

```bash
python3 senzing/workflows/e2e_runner/run_senzing_e2e.py \
  /path/to/production_output.jsonl
```

3. Run management tests on that run folder:

```bash
python3 senzing/workflows/testing/run_management_tests.py \
  /path/to/senzing_run_folder
```

Each subfolder has its own README with details.
