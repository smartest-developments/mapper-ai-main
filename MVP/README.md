# MVP Pipeline (Portable)

Questa cartella e' pensata per essere copiata "as is" in produzione insieme al tuo file JSON reale.

## Cosa contiene

- `run_mvp_pipeline.py`: wrapper unico (mapping + run Senzing + comparison/report)
- `senzing/tools/partner_json_to_senzing.py`: mapper JSON -> JSONL Senzing
- `senzing/all_in_one/run_senzing_end_to_end.py`: esecuzione E2E Senzing con output di comparison/management

## Prerequisiti

- Docker disponibile
- immagine Senzing gia' pronta: `mapper-senzing-poc:4.2.1`
- file input JSON reale

## Comando base

```bash
python3 run_mvp_pipeline.py --input-json /path/to/real_input.json
```

## Sample incluso (500 record)

Dentro `MVP/sample/` trovi una copia pronta:

- `partner_input_realistic_500.json`

Esecuzione rapida:

```bash
python3 run_mvp_pipeline.py --input-json sample/partner_input_realistic_500.json
```

## Input con array annidato

Se il root JSON e' un oggetto con array interno (es. `{"records": [...]}`):

```bash
python3 run_mvp_pipeline.py \
  --input-json /path/to/real_input.json \
  --input-array-key records
```

## WHY (opzionale)

Per performance, di default WHY/explain e' disattivato.
Se vuoi i file WHY:

```bash
python3 run_mvp_pipeline.py \
  --input-json /path/to/real_input.json \
  --with-why \
  --max-explain-records 0 \
  --max-explain-pairs 0
```

## Dove trovi i file

- Mapping output: `output/`
  - `partner_output_senzing_from_input_<timestamp>.jsonl`
  - `field_map_from_input_<timestamp>.json`
  - `mapping_summary_from_input_<timestamp>.json`
  - `run_registry.csv`
- Esecuzioni: `runs/<run_name>_<timestamp>/`
  - `run_summary.json`
  - `comparison/management_summary.md`
  - `comparison/ground_truth_match_quality.md`
  - `comparison/ground_truth_match_quality.json`
- Progetti Senzing locali: `projects/`

## Note performance (dataset grandi)

- Il wrapper usa `--use-input-jsonl-directly` per evitare copie inutili del JSONL.
- Tieni WHY disattivato sui run grandi, salvo analisi specifiche.
