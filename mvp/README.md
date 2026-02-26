# MVP Execution Folder

This folder contains the minimum setup to run Senzing end-to-end in one place.

## Contents

- `run_e2e_mvp.py`: single launcher script
- `input/sample_senzing_ready.jsonl`: ready-to-run sample input
- `runs/`: run artifacts (auto-generated)
- `projects/`: isolated Senzing projects (auto-generated)

## Run (sample)

From repository root:

```bash
python3 mvp/run_e2e_mvp.py
```

Or with explicit input:

```bash
python3 mvp/run_e2e_mvp.py mvp/input/sample_senzing_ready.jsonl
```

## Outputs

All outputs stay inside `mvp/`:

- `mvp/runs/run_<timestamp>/...`
- `mvp/projects/project_<timestamp>/...`

Main file to check after execution:

- `mvp/runs/run_<timestamp>/run_summary.json`
