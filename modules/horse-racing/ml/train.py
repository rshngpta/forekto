"""Train the horse-race win model from races.csv + runs.csv.

Key choices (these are the interview talking points):
  * Split by RACE (GroupShuffleSplit) so no race leaks across train/test.
  * Class imbalance (~8% winners) -> class_weight="balanced"; we report
    PR-AUC and a race-level top-1 hit rate, not plain accuracy.
  * The model + the exact FEATURE_ORDER + metadata are saved together, so
    serving can never drift from training.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features import FEATURE_ORDER, build_feature_frame  # noqa: E402

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(MODULE_ROOT, "data")
MODEL_DIR = os.path.join(MODULE_ROOT, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "horse_rf.pkl")


def load_data() -> pd.DataFrame:
    races = pd.read_csv(os.path.join(DATA_DIR, "races.csv"))
    runs = pd.read_csv(os.path.join(DATA_DIR, "runs.csv"))
    merged = runs.merge(races, on="race_id", how="left", suffixes=("", "_race"))
    if "won" not in merged.columns:
        raise SystemExit("runs.csv must contain a `won` column (1 = winner)")
    return merged


def top1_hit_rate(df: pd.DataFrame, score_col: str) -> float:
    """Fraction of races where the highest-scored horse actually won."""
    hits, total = 0, 0
    for _, grp in df.groupby("race_id"):
        total += 1
        pick = grp.loc[grp[score_col].idxmax()]
        if pick["won"] == 1:
            hits += 1
    return hits / total if total else 0.0


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    merged = load_data()

    X = build_feature_frame(merged)
    y = merged["won"].astype(int).to_numpy()
    groups = merged["race_id"].to_numpy()

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=3,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]

    test_df = merged.iloc[test_idx].copy()
    test_df["proba"] = proba

    metrics = {
        "pr_auc": round(float(average_precision_score(y_test, proba)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "model_top1_hit_rate": round(top1_hit_rate(test_df, "proba"), 4),
    }
    # Baselines for honest comparison.
    if "win_odds" in test_df.columns:
        test_df["neg_odds"] = -test_df["win_odds"]  # favourite = highest score
        metrics["favourite_top1_hit_rate"] = round(
            top1_hit_rate(test_df, "neg_odds"), 4)
    avg_field = test_df.groupby("race_id").size().mean()
    metrics["random_top1_hit_rate"] = round(float(1.0 / avg_field), 4)

    bundle = {
        "model": model,
        "feature_order": FEATURE_ORDER,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(merged)),
        "n_races": int(merged["race_id"].nunique()),
        "metrics": metrics,
    }
    joblib.dump(bundle, MODEL_PATH)
    with open(os.path.join(MODEL_DIR, "metadata.json"), "w") as fh:
        json.dump({k: v for k, v in bundle.items() if k != "model"}, fh, indent=2)

    print("Saved model to", MODEL_PATH)
    print("Rows:", bundle["n_rows"], "| Races:", bundle["n_races"])
    print("Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
