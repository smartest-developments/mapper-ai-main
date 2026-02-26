# MVP Execution Folder

This folder contains the minimum setup to run Senzing end-to-end in one place.

## Contents

- `run_e2e_mvp.py`: single launcher script
- `run_senzing_end_to_end.py`: local core runner used by MVP launcher
- `sample_senzing_ready.jsonl`: ready-to-run sample input

## Run (sample)

From repository root:

```bash
python3 mvp/run_e2e_mvp.py
```

Or with explicit input file:

```bash
python3 mvp/run_e2e_mvp.py mvp/sample_senzing_ready.jsonl
```

## Outputs

By default, outputs are written outside `mvp/`:

- runs: `/mnt/senzing_runs/run_<timestamp>/...`
- projects: `/mnt/project_<timestamp>/...`

Main file to check after execution:

- `/mnt/senzing_runs/run_<timestamp>/run_summary.json`

You can override output locations:

```bash
python3 mvp/run_e2e_mvp.py \
  --output-root /custom/runs \
  --project-parent-dir /custom/projects
```
