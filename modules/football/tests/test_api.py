import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from app.features import FEATURE_ORDER, build_feature_frame
from app.main import create_app
from app import model as model_mod


def _match():
    return dict(home_team="A", away_team="B",
                home_form_points=2.0, away_form_points=1.0,
                home_form_gf=1.8, home_form_ga=0.9,
                away_form_gf=1.0, away_form_ga=1.5,
                home_rank=3, away_rank=12,
                home_odds=1.9, draw_odds=3.5, away_odds=4.2)


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Train a tiny 3-class model so the serving path is real.
    rows = [_match() for _ in range(30)]
    df = pd.DataFrame(rows)
    X = build_feature_frame(df)
    y = np.array((["H"] * 14) + (["D"] * 8) + (["A"] * 8))
    model = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    path = tmp_path / "football_rf.pkl"
    joblib.dump({"model": model, "feature_order": FEATURE_ORDER}, path)

    monkeypatch.setattr(model_mod, "MODEL_PATH", str(path))
    model_mod.load_model.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "t.db"))
    from app import db
    db.reset_engine()
    return create_app().test_client()


def test_health_and_ready(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_predict_returns_three_ranked_outcomes(client):
    resp = client.post("/api/predict", json=_match())
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["ranked"]) == 3
    names = {o["name"] for o in data["ranked"]}
    assert names == {"Home win", "Draw", "Away win"}
    probs = [o["win_probability"] for o in data["ranked"]]
    assert probs == sorted(probs, reverse=True)
    assert data["predicted_outcome"] == data["ranked"][0]


def test_dashboard_renders(client):
    assert client.get("/dashboard").status_code == 200
