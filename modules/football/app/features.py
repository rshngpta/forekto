"""Feature engineering for the football match predictor.

Predicts the 1X2 outcome of a match (Home win / Draw / Away win) from each
side's recent form, league position, and the market odds. As with the
horse-racing module, this file is the single source of truth for the feature
columns and is imported by both the training script and the live app, so
training and serving can never disagree.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class FeatureError(ValueError):
    """Raised when incoming data cannot be turned into a feature row."""


FEATURE_ORDER = [
    "home_form_points",   # avg points/game, last 5
    "away_form_points",
    "home_form_gf",       # avg goals for, last 5
    "home_form_ga",       # avg goals against, last 5
    "away_form_gf",
    "away_form_ga",
    "home_rank",          # league position (1 = top)
    "away_rank",
    "rank_diff",          # away_rank - home_rank (positive => home higher)
    "home_odds",
    "draw_odds",
    "away_odds",
]

DEFAULTS = {
    "home_form_points": 1.3, "away_form_points": 1.3,
    "home_form_gf": 1.3, "home_form_ga": 1.3,
    "away_form_gf": 1.3, "away_form_ga": 1.3,
    "home_rank": 10.0, "away_rank": 10.0,
    "home_odds": 2.6, "draw_odds": 3.3, "away_odds": 2.9,
}

# Outcome label <-> model class code.
CODE_TO_LABEL = {"H": "Home win", "D": "Draw", "A": "Away win"}
LABEL_TO_CODE = {v: k for k, v in CODE_TO_LABEL.items()}


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Turn a dataframe of matches into the model feature matrix."""
    df = df.copy()
    out = pd.DataFrame(index=df.index)
    for col in FEATURE_ORDER:
        if col == "rank_diff":
            continue
        series = pd.to_numeric(df.get(col), errors="coerce")
        out[col] = series.fillna(DEFAULTS[col])
    out["rank_diff"] = out["away_rank"] - out["home_rank"]
    return out[FEATURE_ORDER]


def build_match_frame(match: dict) -> pd.DataFrame:
    """Build the single-row feature matrix for one match (serving path)."""
    if not isinstance(match, dict):
        raise FeatureError("`match` must be an object")
    for odds_key in ("home_odds", "draw_odds", "away_odds"):
        v = match.get(odds_key)
        if v is not None and (not isinstance(v, (int, float)) or v < 1):
            raise FeatureError(f"{odds_key} must be a number >= 1")
    return build_feature_frame(pd.DataFrame([match]))


def outcomes_from_proba(classes: np.ndarray, proba: np.ndarray, match: dict) -> list:
    """Turn model probabilities into a ranked list of the three outcomes."""
    odds_for = {
        "H": match.get("home_odds"),
        "D": match.get("draw_odds"),
        "A": match.get("away_odds"),
    }
    ranked = []
    for code, p in zip(classes, proba):
        ranked.append({
            "name": CODE_TO_LABEL.get(code, code),
            "outcome": code,
            "win_odds": odds_for.get(code),
            "win_probability": round(float(p), 4),
        })
    ranked.sort(key=lambda r: r["win_probability"], reverse=True)
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return ranked
