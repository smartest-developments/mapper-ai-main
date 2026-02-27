# MVP Pipeline

Script e input restano nella root di `MVP`.  
Gli output finali vengono scritti in `output/<timestamp>/`.

## File inclusi

- `run_mvp_pipeline.py`: wrapper unico (mapping + run Senzing + comparison/report)
- `partner_json_to_senzing.py`: mapper JSON -> JSONL Senzing
- `run_senzing_end_to_end.py`: runner E2E Senzing
- `build_management_dashboard.py`: builds dashboard data from all `output/<timestamp>/` runs
- `management_dashboard.html`: local dashboard UI for management
- `management_dashboard.js`: dashboard logic
- `management_dashboard.css`: dashboard styling
- `tabler.min.css`, `tabler.min.js`, `chart.umd.js`: local dashboard assets (no CDN)
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

Dentro `output/<timestamp>/` (management-friendly) trovi:

- `input_source.json` (exact source JSON used for that run)
- `management_summary.md`
- `ground_truth_match_quality.md`

Dentro `output/<timestamp>/technical output/` trovi gli artifact tecnici:

- `mapped_output.jsonl`
- `field_map.json`
- `mapping_summary.json`
- `run_summary.json`
- `input_normalized.jsonl` (exact JSONL consumed by Senzing in that run)
- `management_summary.json`
- `ground_truth_match_quality.json`
- `matched_pairs.csv`
- `match_stats.csv`
- `entity_records.csv`
- `run_registry.csv` (snapshot della registry del run)

## Runtime

Il wrapper usa una directory temporanea esterna a `MVP` per i file intermedi e poi copia gli artifact finali in `output/<timestamp>/`.  
Per mantenere la directory runtime:

```bash
python3 run_mvp_pipeline.py --input-json /path/to/real_input.json --keep-runtime-dir
```

Nota: `--execution-mode auto` (default) usa Docker se disponibile, altrimenti passa automaticamente a `local`.

## Management dashboard (local, offline)

The dashboard is fully local (no CDN).

- It reads only local artifacts generated in `output/<timestamp>/`.
- It is published in `output/dashboard/` (all dashboard files are there).
- It is refreshed automatically after each `run_mvp_pipeline.py` execution.

You can also rebuild it manually:

```bash
python3 build_management_dashboard.py
```

Open dashboard:

```bash
python3 -m http.server 8080
```

Then browse:

- `http://localhost:8080/output/dashboard/management_dashboard.html`

Third-party assets included locally:

- `tabler.min.css`, `tabler.min.js` from `@tabler/core@1.4.0`
- `chart.umd.js` from `chart.js@4.4.1`
