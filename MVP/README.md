# MVP Pipeline

Script e input restano nella root di `MVP`.  
Gli output finali vengono scritti in `output/<timestamp>/`.

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

## Output

Ogni esecuzione crea una cartella dedicata:

- `output/<timestamp>/`

Dentro trovi:

- `mapped_output.jsonl`
- `field_map.json`
- `mapping_summary.json`
- `run_summary.json`
- `management_summary.md`
- `management_summary.json`
- `ground_truth_match_quality.md`
- `ground_truth_match_quality.json`
- `matched_pairs.csv`
- `match_stats.csv`
- `entity_records.csv`
- `execution_manifest.json`
- `run_registry.csv` (snapshot della registry del run)

## Runtime

Il wrapper usa una directory temporanea esterna a `MVP` per i file intermedi e poi copia gli artifact finali in `output/<timestamp>/`.  
Per mantenere la directory runtime:

```bash
python3 run_mvp_pipeline.py --input-json /path/to/real_input.json --keep-runtime-dir
```

Nota: `--execution-mode auto` (default) usa Docker se disponibile, altrimenti passa automaticamente a `local`.
