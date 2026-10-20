"""Model loading and prediction for the horse-race module.

The trained model is a file on disk. This module loads it once (cached) and
exposes a small, stable interface the Flask app calls. Keeping load/predict
here means the web layer never touches scikit-learn directly.
"""
from __future__ import annotations

import os
from functools import lru_cache

import joblib
import numpy as np

from app.features import FEATURE_ORDER, build_field_frame

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(MODULE_ROOT, "model", "horse_rf.pkl")
MODEL_PATH = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)


def model_exists() -> bool:
    return os.path.exists(MODEL_PATH)


@lru_cache(maxsize=1)
def load_model():
    """Load and cache the model bundle (model + feature order + metadata)."""
    if not model_exists():
        raise FileNotFoundError(
            f"No model at {MODEL_PATH}. Run `make train` first."
        )
    return joblib.load(MODEL_PATH)


def predict_field(race: dict, runners: list) -> list:
    """Score a whole race and return runners ranked by win probability.

    Raw model scores are normalised across the field so they read as each
    horse's share of the win probability (they sum to ~1).
    """
    bundle = load_model()
    model = bundle["model"]

    frame = build_field_frame(race, runners)
    raw = model.predict_proba(frame[FEATURE_ORDER])[:, 1]

    total = float(np.sum(raw))
    norm = raw / total if total > 0 else np.full(len(raw), 1.0 / len(raw))

    ranked = []
    for runner, score, prob in zip(runners, raw, norm):
        ranked.append({
            **runner,
            "raw_score": round(float(score), 4),
            "win_probability": round(float(prob), 4),
        })
    ranked.sort(key=lambda r: r["win_probability"], reverse=True)
    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
    return ranked
