# mapper toolkit

Toolkit for mapping source data to Senzing entity-resolution JSON format.

> Note: this toolkit is intended for development and validation workflows.

## What's Included

```text
senzing/
├── prompts/
│   └── senzing_mapping_assistant.md
├── reference/
│   ├── senzing_entity_specification.md
│   ├── senzing_mapping_examples.md
│   ├── identifier_crosswalk.json
│   └── usage_type_crosswalk.json
├── tools/
│   ├── sz_schema_generator.py
│   ├── lint_senzing_json.py
│   ├── sz_json_analyzer.py
│   ├── partner_json_to_senzing.py
│   └── run_partner_mapping_pipeline.py
├── all_in_one/
│   └── run_senzing_end_to_end.py
└── workflows/
    ├── mapper/
    ├── e2e_runner/
    └── testing/
```

## Main Workflows

1. Build Senzing-ready JSONL from source data:

```bash
python3 senzing/workflows/mapper/run_mapper_jsonl.py \
  /path/to/input.json \
  /path/to/output.jsonl \
  --data-source PARTNERS
```

2. Run Senzing end-to-end (project creation, load, export, explain, comparison):

```bash
python3 senzing/workflows/e2e_runner/run_senzing_e2e.py \
  /path/to/output.jsonl
```

3. Run automated management test cases on one run folder:

```bash
python3 senzing/workflows/testing/run_management_tests.py \
  /path/to/senzing_run_folder
```

## Documentation

- `senzing/senzing_tools_reference.md`
- `docs/partner_json_to_senzing.md`
- `senzing/workflows/README.md`

## Environment Setup

- Python 3.10+
- Access to Senzing CLI tools for load/export steps
- Git + SSH configuration for repository sync
