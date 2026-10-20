# Forekto — Horse Racing module

The first sport module for Forekto: a win predictor for horse races. It takes a
race's field of runners and returns a ranked list of win probabilities, served
over a small Flask API.

## Layout

```
app/        Flask app + model serving
  features.py   FEATURE_ORDER + feature engineering (shared by train & serve)
  model.py      load the trained model (cached) + predict a field
  main.py       Flask routes: /api/predict, /health, /ready
  wsgi.py       gunicorn entrypoint
ml/
  make_sample_data.py   generate a synthetic dataset (dev, no Kaggle needed)
  train.py              train the model from data/races.csv + data/runs.csv
tests/      unit tests for features and the API
data/       CSVs live here (gitignored) — drop the real Kaggle files in
model/      trained model artifact (gitignored)
```

## Quick start

```bash
cd modules/horse-racing
python3 -m venv .venv && source .venv/bin/activate
make install
make sample-data   # writes data/races.csv + data/runs.csv (synthetic)
make train         # trains and prints metrics; saves model/horse_rf.pkl
make test          # runs the test suite
make run           # serves at http://localhost:8080
```

Example request:

```bash
curl -s localhost:8080/api/predict -H 'Content-Type: application/json' -d '{
  "race": {"venue": "ST", "going": "GOOD", "distance": 1400},
  "runners": [
    {"draw": 1, "actual_weight": 126, "horse_age": 4, "win_odds": 3.5, "horse_country": "AUS", "horse_type": "Gelding"},
    {"draw": 7, "actual_weight": 120, "horse_age": 5, "win_odds": 12.0, "horse_country": "NZ", "horse_type": "Mare"}
  ]
}'
```

## Using the real data

Download the Kaggle dataset `gdaley/hkracing` and place its `races.csv` and
`runs.csv` in `data/`, replacing the synthetic files, then re-run `make train`.
The feature builder is defensive about extra/missing columns.

## Notes

* Target is `won` (1 = winner). Winners are ~8% of rows, so training uses
  `class_weight="balanced"` and reports **PR-AUC** and a race-level **top-1 hit
  rate** (how often the top-ranked horse actually won), not plain accuracy.
* `features.py` is imported by both `train.py` and the serving app, so the
  columns match exactly at train and serve time — no training/serving skew.
* These predictions are an ML/engineering exercise, not betting advice.
