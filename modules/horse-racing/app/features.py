"""Feature engineering for the horse-race win predictor.

This module is the single source of truth for how raw race data becomes the
numeric feature matrix the model sees. Both the training script and the live
API import FEATURE_ORDER and build_feature_frame from here, so the columns at
training time and serving time are guaranteed identical (no training/serving
skew).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class FeatureError(ValueError):
    """Raised when incoming data cannot be turned into a feature row."""


# --- Numeric features -------------------------------------------------------
NUMERIC_FEATURES = [
    "draw",             # starting gate
    "actual_weight",    # weight carried (lbs)
    "declared_weight",  # horse + gear declared weight
    "horse_age",
    "win_odds",         # market odds — a strong signal
    "distance",         # race distance (m)
    "field_size",       # number of runners in the race
    "draw_pct",         # draw normalised by field size
]

NUMERIC_DEFAULTS = {
    "draw": 7.0,
    "actual_weight": 123.0,
    "declared_weight": 1100.0,
    "horse_age": 4.0,
    "win_odds": 15.0,
    "distance": 1400.0,
    "field_size": 12.0,
    "draw_pct": 0.5,
}

# --- Categorical features (fixed vocabularies, unknown -> OTHER) ------------
# Fixing the vocabulary here is what keeps the one-hot columns deterministic.
CATEGORICAL_VOCAB = {
    "venue": ["ST", "HV", "OTHER"],
    "going": [
        "GOOD", "GOOD TO FIRM", "GOOD TO YIELDING", "YIELDING",
        "FAST", "WET SLOW", "SOFT", "OTHER",
    ],
    "horse_country": ["AUS", "NZ", "IRE", "GB", "USA", "SAF", "FR", "JPN", "OTHER"],
    "horse_type": ["Gelding", "Horse", "Mare", "Rig", "Colt", "Filly", "OTHER"],
}


def _one_hot_columns():
    cols = []
    for col, cats in CATEGORICAL_VOCAB.items():
        for cat in cats:
            cols.append(f"{col}__{cat}")
    return cols


FEATURE_ORDER = NUMERIC_FEATURES + _one_hot_columns()


def _canon(value, cats):
    """Map a raw categorical value onto the fixed vocabulary (else OTHER)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "OTHER"
    v = str(value).strip().upper()
    for cat in cats:
        if cat.upper() == v:
            return cat
    return "OTHER"


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Turn a dataframe of runs (with race context) into the model matrix.

    Expected columns (missing ones are filled with defaults): draw,
    actual_weight, declared_weight, horse_age, win_odds, distance, venue,
    going, horse_country, horse_type, and race_id (used to derive field_size
    when it is not supplied).
    """
    df = df.copy()

    for col in ["draw", "actual_weight", "declared_weight", "horse_age",
                "win_odds", "distance"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")

    if "field_size" not in df.columns:
        if "race_id" not in df.columns:
            raise FeatureError("need either field_size or race_id to build features")
        df["field_size"] = df.groupby("race_id")["race_id"].transform("size")
    df["field_size"] = pd.to_numeric(df["field_size"], errors="coerce")
    df["draw_pct"] = df["draw"] / df["field_size"].replace(0, np.nan)

    out = pd.DataFrame(index=df.index)
    for col in NUMERIC_FEATURES:
        out[col] = df[col].fillna(NUMERIC_DEFAULTS[col])

    for col, cats in CATEGORICAL_VOCAB.items():
        canon = df.get(col, pd.Series([None] * len(df), index=df.index))
        canon = canon.apply(lambda v: _canon(v, cats))
        for cat in cats:
            out[f"{col}__{cat}"] = (canon == cat).astype(int)

    return out[FEATURE_ORDER]


def build_field_frame(race: dict, runners: list) -> pd.DataFrame:
    """Build the feature matrix for one race's whole field (serving path)."""
    if not isinstance(runners, list) or not runners:
        raise FeatureError("`runners` must be a non-empty list")
    if not isinstance(race, dict):
        raise FeatureError("`race` must be an object")

    rows = []
    for i, runner in enumerate(runners):
        if not isinstance(runner, dict):
            raise FeatureError(f"runner at index {i} must be an object")
        rows.append({**race, **runner})

    df = pd.DataFrame(rows)
    df["race_id"] = "request"
    df["field_size"] = len(runners)
    return build_feature_frame(df)
