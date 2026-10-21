import pytest

from app.features import (
    CODE_TO_LABEL,
    FEATURE_ORDER,
    FeatureError,
    build_match_frame,
    outcomes_from_proba,
)
import numpy as np


def _match(**over):
    base = dict(home_team="A", away_team="B",
                home_form_points=2.0, away_form_points=1.0,
                home_form_gf=1.8, home_form_ga=0.9,
                away_form_gf=1.0, away_form_ga=1.5,
                home_rank=3, away_rank=12,
                home_odds=1.9, draw_odds=3.5, away_odds=4.2)
    base.update(over)
    return base


def test_feature_order_has_rank_diff_and_odds():
    assert "rank_diff" in FEATURE_ORDER
    assert "home_odds" in FEATURE_ORDER
    assert len(FEATURE_ORDER) == len(set(FEATURE_ORDER))


def test_match_frame_columns_and_rank_diff():
    frame = build_match_frame(_match())
    assert list(frame.columns) == FEATURE_ORDER
    # rank_diff = away_rank - home_rank = 12 - 3 = 9
    assert frame["rank_diff"].iloc[0] == 9


def test_bad_odds_raise():
    with pytest.raises(FeatureError):
        build_match_frame(_match(home_odds=0.5))


def test_outcomes_ranked_and_labelled():
    classes = np.array(["A", "D", "H"])
    proba = np.array([0.2, 0.3, 0.5])  # Home most likely
    ranked = outcomes_from_proba(classes, proba, _match())
    assert ranked[0]["name"] == CODE_TO_LABEL["H"]
    assert [r["rank"] for r in ranked] == [1, 2, 3]
    probs = [r["win_probability"] for r in ranked]
    assert probs == sorted(probs, reverse=True)
    # odds attached to the right outcome
    assert ranked[0]["win_odds"] == 1.9
