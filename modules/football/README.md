# Forekto — Football module

The second sport module: a **1X2 match predictor** (Home win / Draw / Away win).
It mirrors the horse-racing module exactly — same structure, same Flask/Docker
pattern, and it reuses the **same database and accuracy dashboard**, because a
football prediction is just a ranked set of outcomes (like a ranked race field).

## What it predicts

Given a match's recent form, league positions and market odds, it returns the
three outcomes ranked by probability, and stores each prediction so the
dashboard can track accuracy against the bookmaker-favourite baseline.

## Quick start

```bash
cd modules/football
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
make install
make sample-data    # synthetic league (or drop a real matches.csv into data/)
make train          # trains the 3-class model, prints metrics
make seed           # populates the dashboard with held-out matches
make test
make run            # http://localhost:8081   (dashboard at /dashboard)
```

## Using real data

Public football results (e.g. football-data.co.uk per-league CSVs) carry
`HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR` (H/D/A) and odds columns. Compute
rolling form + rank columns to match `FEATURE_ORDER` in `app/features.py`, save
as `data/matches.csv`, and re-run `make train`.

## Notes

- Target is `ftr` (H/D/A) — a 3-class problem; metrics are accuracy, log loss,
  and top-1 outcome hit rate vs the market favourite.
- `features.py` is shared by training and serving — no training/serving skew.
- Predictions are a machine-learning demonstration, **not betting advice**.
