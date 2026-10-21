"""Seed the dashboard with honest out-of-sample football predictions.

Replays the held-out test matches (same time-based split as training) through
the trained model, storing each prediction with the real full-time result.
Run after `make train`:
    python ml/seed_predictions.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features import CODE_TO_LABEL, FEATURE_ORDER, build_feature_frame, outcomes_from_proba  # noqa: E402,E501
from app import model as model_mod  # noqa: E402
from app import db                  # noqa: E402

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(MODULE_ROOT, "data")


def main():
    if not model_mod.model_exists():
        raise SystemExit("No trained model. Run `make train` first.")

    df = pd.read_csv(os.path.join(DATA_DIR, "matches.csv")).sort_values("date")
    df = df.reset_index(drop=True)
    cut = int(len(df) * 0.8)
    test = df.iloc[cut:]

    bundle = model_mod.load_model()
    model = bundle["model"]
    feats = build_feature_frame(test)

    stored = 0
    for idx, row in test.iterrows():
        match = row.to_dict()
        proba = model.predict_proba(feats.loc[[idx]][FEATURE_ORDER])[0]
        ranked = outcomes_from_proba(model.classes_, proba, match)
        actual = CODE_TO_LABEL.get(row["ftr"], row["ftr"])
        label = f"{row['home_team']} vs {row['away_team']}"
        race = {"match": label}
        db.save_prediction(race, ranked, source="backtest", actual_winner=actual)
        stored += 1

    print(f"Seeded {stored} out-of-sample matches into the dashboard.")
    m = db.compute_metrics()
    print(f"  model hit rate:     {m['model_hit_rate']}")
    print(f"  favourite hit rate: {m['favourite_hit_rate']}")


if __name__ == "__main__":
    main()
