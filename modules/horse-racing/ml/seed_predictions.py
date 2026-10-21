"""Populate the dashboard with honest, out-of-sample accuracy.

Re-creates the exact train/test split used in training, then replays every
TEST race through the trained model, storing each prediction together with the
race's real winner. The dashboard then shows genuine held-out performance — the
model never saw these races during training.

Run after `make train`:
    python ml/seed_predictions.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features import build_feature_frame  # noqa: E402
from app import model as model_mod             # noqa: E402
from app import db                             # noqa: E402

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(MODULE_ROOT, "data")


def load_merged() -> pd.DataFrame:
    races = pd.read_csv(os.path.join(DATA_DIR, "races.csv"))
    runs = pd.read_csv(os.path.join(DATA_DIR, "runs.csv"))
    return runs.merge(races, on="race_id", how="left", suffixes=("", "_race"))


def main():
    if not model_mod.model_exists():
        raise SystemExit("No trained model. Run `make train` first.")

    merged = load_merged()
    X = build_feature_frame(merged)
    y = merged["won"].astype(int).to_numpy()
    groups = merged["race_id"].to_numpy()

    # Same split as training -> these are genuinely held-out races.
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    _, test_idx = next(splitter.split(X, y, groups))
    test = merged.iloc[test_idx]

    bundle = model_mod.load_model()
    model = bundle["model"]

    stored = 0
    for race_id, grp in test.groupby("race_id"):
        race = {
            "venue": grp["venue"].iloc[0] if "venue" in grp else "ST",
            "going": grp["going"].iloc[0] if "going" in grp else "GOOD",
            "distance": int(grp["distance"].iloc[0]) if "distance" in grp else 1400,
        }
        runners = []
        for _, row in grp.iterrows():
            runners.append({
                "name": f"Horse {int(row.get('horse_no', 0))}",
                "draw": row.get("draw"),
                "actual_weight": row.get("actual_weight"),
                "declared_weight": row.get("declared_weight"),
                "horse_age": row.get("horse_age"),
                "win_odds": row.get("win_odds"),
                "horse_country": row.get("horse_country"),
                "horse_type": row.get("horse_type"),
            })
        feats = build_feature_frame(grp)
        proba = model.predict_proba(feats)[:, 1]
        total = float(proba.sum()) or 1.0
        ranked = []
        for runner, p in zip(runners, proba):
            ranked.append({**runner, "win_probability": round(float(p) / total, 4)})
        ranked.sort(key=lambda r: r["win_probability"], reverse=True)
        for i, r in enumerate(ranked, 1):
            r["rank"] = i

        winner_row = grp[grp["won"] == 1]
        if winner_row.empty:
            continue
        actual = f"Horse {int(winner_row['horse_no'].iloc[0])}"

        db.save_prediction(race, ranked, source="backtest", actual_winner=actual)
        stored += 1

    print(f"Seeded {stored} out-of-sample races into the dashboard.")
    m = db.compute_metrics()
    print(f"  model hit rate:      {m['model_hit_rate']}")
    print(f"  favourite hit rate:  {m['favourite_hit_rate']}")


if __name__ == "__main__":
    main()
