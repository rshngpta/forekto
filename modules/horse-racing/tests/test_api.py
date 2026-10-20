import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from app.features import FEATURE_ORDER, build_field_frame
from app.main import create_app
from app import model as model_mod

RACE = {"venue": "ST", "going": "GOOD", "distance": 1400}


def _field(n=10):
    return [
        {"draw": i + 1, "actual_weight": 120 + i, "declared_weight": 1100,
         "horse_age": 4, "win_odds": 2.0 + i, "horse_country": "AUS",
         "horse_type": "Gelding"}
        for i in range(n)
    ]


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Train a tiny model so the serving path is real, not mocked.
    rows, y = [], []
    for odds_winner in (1, 2, 3):  # three fake races
        field = _field(8)
        frame = build_field_frame(RACE, field)
        rows.append(frame)
        labels = np.zeros(len(field), dtype=int)
        labels[0] = 1  # lowest-odds horse wins
        y.append(labels)
    X = pd.concat(rows, ignore_index=True)
    y = np.concatenate(y)

    model = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    path = tmp_path / "horse_rf.pkl"
    joblib.dump({"model": model, "feature_order": FEATURE_ORDER}, path)

    monkeypatch.setattr(model_mod, "MODEL_PATH", str(path))
    model_mod.load_model.cache_clear()

    return create_app().test_client()


def test_health_ok(client):
    assert client.get("/health").status_code == 200


def test_ready_ok_when_model_present(client):
    assert client.get("/ready").status_code == 200


def test_predict_returns_ranked_field(client):
    resp = client.post("/api/predict", json={"race": RACE, "runners": _field(10)})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["field_size"] == 10
    ranked = data["ranked"]
    assert len(ranked) == 10
    # ranks are 1..n and probabilities are sorted descending
    assert [r["rank"] for r in ranked] == list(range(1, 11))
    probs = [r["win_probability"] for r in ranked]
    assert probs == sorted(probs, reverse=True)
    assert data["predicted_winner"] == ranked[0]


def test_predict_bad_body_is_400(client):
    resp = client.post("/api/predict", json={"race": RACE, "runners": []})
    assert resp.status_code == 400
