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

## Run In Docker (Debian + Senzing v4)

From repository root:

```bash
docker run --rm --platform linux/amd64 \
  -v "$PWD":/workspace \
  -w /workspace \
  mapper-senzing-poc:4.2.1 \
  bash -lc 'python3 senzing/all_in_one/run_senzing_end_to_end.py \
    mvp/sample_senzing_ready.jsonl \
    --output-root /workspace/.senzing_runs_test \
    --project-parent-dir /workspace/.senzing_projects_test \
    --run-name-prefix run_docker_e2e \
    --load-threads 4 \
    --load-fallback-threads 1 \
    --snapshot-threads 4 \
    --snapshot-fallback-threads 1 \
    --step-timeout-seconds 1800'
```

This command keeps all artifacts in the local repository under:

- `.senzing_runs_test/`
- `.senzing_projects_test/`

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
