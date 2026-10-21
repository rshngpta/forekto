"""Flask application for the horse-race win predictor.

Routes:
  GET  /                  prediction UI
  GET  /dashboard         accuracy dashboard
  POST /api/predict       score a race's field, return a ranked list (and store it)
  POST /api/outcome/<id>  record the actual winner for a stored prediction
  GET  /api/metrics       accuracy stats for the dashboard
  GET  /api/predictions   recent predictions
  GET  /health            liveness
  GET  /ready             readiness (model loaded)
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
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400
        race = payload.get("race", {})
        runners = payload.get("runners")
        try:
            ranked = model_mod.predict_field(race, runners)
        except FeatureError as exc:
            return jsonify({"error": str(exc)}), 400

        # Best-effort: store the prediction so the dashboard can track accuracy.
        prediction_id = db.save_prediction(race, ranked, source="live")

        return jsonify({
            "prediction_id": prediction_id,
            "race": race,
            "field_size": len(ranked),
            "predicted_winner": ranked[0] if ranked else None,
            "ranked": ranked,
        })

    @app.post("/api/outcome/<int:prediction_id>")
    def outcome(prediction_id: int):
        payload = request.get_json(silent=True) or {}
        actual = payload.get("actual_winner")
        if not actual:
            return jsonify({"error": "actual_winner is required"}), 400
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
    create_app().run(host="0.0.0.0", port=8080, debug=True)
