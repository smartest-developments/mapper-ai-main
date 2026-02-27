# MVP Pipeline (Flat)

Questa cartella e' completamente flat: solo file nella root, nessuna sottocartella.

## File inclusi

- `run_mvp_pipeline.py`: wrapper unico (mapping + run Senzing + comparison/report)
- `partner_json_to_senzing.py`: mapper JSON -> JSONL Senzing
- `run_senzing_end_to_end.py`: runner E2E Senzing
- `partner_input_realistic_500.json`: sample pronto (500 record)

## Prerequisiti

- Docker disponibile
- immagine Senzing: `mapper-senzing-poc:4.2.1`
- file input JSON reale (array oppure oggetto con array)

## Comando base

```bash
python3 run_mvp_pipeline.py --input-json /path/to/real_input.json
```

In ambiente Ubuntu con Senzing gia' installato (senza Docker), usa:

```bash
python3 run_mvp_pipeline.py --input-json /path/to/real_input.json --execution-mode local
```

Se ti serve forzare il setup base di Senzing:

```bash
python3 run_mvp_pipeline.py \
  --input-json /path/to/real_input.json \
  --execution-mode local \
  --senzing-env /opt/senzing/er/setupEnv
```

## Esempio con sample incluso

```bash
python3 run_mvp_pipeline.py --input-json partner_input_realistic_500.json
```

## Input annidato

Se il JSON e' del tipo `{"records":[...]}`:

```bash
python3 run_mvp_pipeline.py --input-json /path/to/input.json --input-array-key records
```

## WHY (opzionale)

Di default WHY e' disattivato per performance.  
Per abilitarlo:

```bash
python3 run_mvp_pipeline.py \
  --input-json /path/to/real_input.json \
  --with-why \
  --max-explain-records 0 \
  --max-explain-pairs 0
```

## Output (sempre flat in root)

Dopo ogni run trovi file timestampati, ad esempio:

- `mapped_output_<timestamp>.jsonl`
- `field_map_<timestamp>.json`
- `mapping_summary_<timestamp>.json`
- `run_summary_<timestamp>.json`
- `management_summary_<timestamp>.md`
- `ground_truth_match_quality_<timestamp>.md`
- `ground_truth_match_quality_<timestamp>.json`
- `execution_manifest_<timestamp>.json`
- `run_registry.csv`

## Runtime

Il wrapper usa una directory temporanea esterna a `MVP` per i file intermedi e poi copia gli artifact finali nella root di `MVP`.  
Per mantenere la directory runtime:

```bash
python3 run_mvp_pipeline.py --input-json /path/to/real_input.json --keep-runtime-dir
```

Nota: `--execution-mode auto` (default) usa Docker se disponibile, altrimenti passa automaticamente a `local`.
