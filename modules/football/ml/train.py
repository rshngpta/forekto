"""Train the football 1X2 model from matches.csv.

Target is FTR in {H, D, A} — a 3-class classification. Draws are the hardest
class and the whole field is roughly balanced, so we report multiclass accuracy
and log loss, plus a top-1 outcome hit rate against the bookmaker-favourite
baseline (always backing the lowest-odds outcome). Split is by time (earlier
matches train, later matches test) to avoid leaking the future into the past.
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
from sklearn.metrics import accuracy_score, log_loss

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features import FEATURE_ORDER, build_feature_frame  # noqa: E402

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(MODULE_ROOT, "data")
MODEL_DIR = os.path.join(MODULE_ROOT, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "football_rf.pkl")


def favourite_hit_rate(df: pd.DataFrame) -> float:
    """Always back the lowest-odds outcome; how often is it right?"""
    hits = 0
    for _, r in df.iterrows():
        odds = {"H": r["home_odds"], "D": r["draw_odds"], "A": r["away_odds"]}
        pick = min(odds, key=odds.get)
        hits += 1 if pick == r["ftr"] else 0
    return hits / len(df) if len(df) else 0.0


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = pd.read_csv(os.path.join(DATA_DIR, "matches.csv"))
    df = df.sort_values("date").reset_index(drop=True)

    X = build_feature_frame(df)
    y = df["ftr"].astype(str)

    # Time-based split: first 80% train, last 20% test.
    cut = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:cut], X.iloc[cut:]
    y_train, y_test = y.iloc[:cut], y.iloc[cut:]
    test_df = df.iloc[cut:].copy()

    model = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=5,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)
    preds = model.predict(X_test)

    model_hits = (preds == y_test.to_numpy()).mean()
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "log_loss": round(float(log_loss(y_test, proba, labels=model.classes_)), 4),
        "model_top1_hit_rate": round(float(model_hits), 4),
        "favourite_top1_hit_rate": round(favourite_hit_rate(test_df), 4),
        "classes": list(model.classes_),
    }

    bundle = {
        "model": model,
        "feature_order": FEATURE_ORDER,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "metrics": metrics,
    }
    joblib.dump(bundle, MODEL_PATH)
    with open(os.path.join(MODEL_DIR, "metadata.json"), "w") as fh:
        json.dump({k: v for k, v in bundle.items() if k != "model"}, fh, indent=2)

    print("Saved model to", MODEL_PATH)
    print("Matches:", bundle["n_rows"])
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
