from app.features import (
    CATEGORICAL_VOCAB,
    FEATURE_ORDER,
    FeatureError,
    build_field_frame,
)

import pytest


def _runner(**over):
    base = dict(draw=3, actual_weight=125, declared_weight=1100, horse_age=4,
                win_odds=5.5, horse_country="AUS", horse_type="Gelding")
    base.update(over)
    return base


RACE = {"venue": "ST", "going": "GOOD", "distance": 1400}


def test_feature_order_is_stable_and_nonempty():
    assert len(FEATURE_ORDER) == len(set(FEATURE_ORDER))
    assert "win_odds" in FEATURE_ORDER
    # every categorical vocab member has a one-hot column
    for col, cats in CATEGORICAL_VOCAB.items():
        for cat in cats:
            assert f"{col}__{cat}" in FEATURE_ORDER


def test_field_frame_has_exact_columns():
    frame = build_field_frame(RACE, [_runner(), _runner(draw=7)])
    assert list(frame.columns) == FEATURE_ORDER
    assert len(frame) == 2
    # field_size and draw_pct are derived
    assert frame["field_size"].iloc[0] == 2
    assert abs(frame["draw_pct"].iloc[0] - 3 / 2) < 1e-9


def test_unknown_category_falls_back_to_other():
    frame = build_field_frame(RACE, [_runner(horse_country="MARS")])
    assert frame["horse_country__OTHER"].iloc[0] == 1
    assert frame["horse_country__AUS"].iloc[0] == 0


def test_missing_numeric_is_filled_not_crashing():
    frame = build_field_frame(RACE, [{"horse_type": "Mare"}])
    assert list(frame.columns) == FEATURE_ORDER
    assert frame.notna().all().all()


def test_empty_runners_raises():
    with pytest.raises(FeatureError):
        build_field_frame(RACE, [])
