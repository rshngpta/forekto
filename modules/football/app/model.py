"""Model loading and prediction for the football module."""
from __future__ import annotations

import os
from functools import lru_cache

import joblib

from app.features import FEATURE_ORDER, build_match_frame, outcomes_from_proba

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(MODULE_ROOT, "model", "football_rf.pkl")
MODEL_PATH = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)


def model_exists() -> bool:
    return os.path.exists(MODEL_PATH)


@lru_cache(maxsize=1)
def load_model():
    if not model_exists():
        raise FileNotFoundError(f"No model at {MODEL_PATH}. Run `make train` first.")
    return joblib.load(MODEL_PATH)


def predict_match(match: dict) -> list:
    """Return the three outcomes (Home/Draw/Away) ranked by probability."""
    bundle = load_model()
    model = bundle["model"]
    frame = build_match_frame(match)
    proba = model.predict_proba(frame[FEATURE_ORDER])[0]
    return outcomes_from_proba(model.classes_, proba, match)
