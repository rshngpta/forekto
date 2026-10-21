"""Flask application for the football 1X2 predictor.

Mirrors the horse-racing module's shape: a prediction is a ranked set of
outcomes (Home / Draw / Away), so it reuses the same persistence layer and
accuracy dashboard.
"""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from app.features import FeatureError
from app import model as model_mod
from app import db


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.post("/api/predict")
    def predict():
        if not model_mod.model_exists():
            return jsonify({"error": "model not ready"}), 503
        match = request.get_json(silent=True)
        if not isinstance(match, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400
        try:
            ranked = model_mod.predict_match(match)
        except FeatureError as exc:
            return jsonify({"error": str(exc)}), 400

        label = f"{match.get('home_team', 'Home')} vs {match.get('away_team', 'Away')}"
        race = {"match": label, **{k: match.get(k) for k in
                ("home_team", "away_team", "home_odds", "draw_odds", "away_odds")}}
        prediction_id = db.save_prediction(race, ranked, source="live")

        return jsonify({
            "prediction_id": prediction_id,
            "match": label,
            "predicted_outcome": ranked[0] if ranked else None,
            "ranked": ranked,
        })

    @app.post("/api/outcome/<int:prediction_id>")
    def outcome(prediction_id: int):
        payload = request.get_json(silent=True) or {}
        actual = payload.get("actual_winner") or payload.get("actual_outcome")
        if not actual:
            return jsonify({"error": "actual_outcome is required"}), 400
        if db.set_outcome(prediction_id, actual):
            return jsonify({"status": "recorded", "prediction_id": prediction_id})
        return jsonify({"error": "prediction not found"}), 404

    @app.get("/api/metrics")
    def metrics():
        return jsonify(db.compute_metrics())

    @app.get("/api/predictions")
    def predictions():
        limit = request.args.get("limit", default=20, type=int)
        return jsonify({"predictions": db.recent_predictions(limit)})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/ready")
    def ready():
        if model_mod.model_exists():
            return jsonify({"status": "ready"})
        return jsonify({"status": "no model"}), 503

    @app.errorhandler(FeatureError)
    def handle_feature_error(exc):
        return jsonify({"error": str(exc)}), 400

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8081, debug=True)
