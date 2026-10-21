from app.main import create_app
from app import db


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "test.db"))
    db.reset_engine()
    return create_app().test_client()


def test_metrics_empty(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    m = c.get("/api/metrics").get_json()
    assert m["total_predictions"] == 0
    assert m["model_hit_rate"] is None


def test_save_and_resolve_outcome(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + str(tmp_path / "test.db"))
    db.reset_engine()
    ranked = [
        {"name": "Alpha", "win_odds": 2.0, "win_probability": 0.5, "rank": 1},
        {"name": "Bravo", "win_odds": 5.0, "win_probability": 0.3, "rank": 2},
    ]
    pid = db.save_prediction({"venue": "ST"}, ranked, source="live")
    assert pid is not None

    assert db.set_outcome(pid, "Alpha") is True
    m = db.compute_metrics()
    assert m["resolved"] == 1
    assert m["model_hit_rate"] == 1.0          # predicted Alpha, Alpha won
    assert m["favourite_hit_rate"] == 1.0      # Alpha was also lowest odds


def test_dashboard_page_renders(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    resp = c.get("/dashboard")
    assert resp.status_code == 200
    assert b"Accuracy Dashboard" in resp.data


def test_outcome_missing_prediction_is_404(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    resp = c.post("/api/outcome/999", json={"actual_winner": "X"})
    assert resp.status_code == 404
