"""Flask application for the horse-race win predictor.

Routes:
  GET  /             small landing page describing the API
  POST /api/predict  score a race's field, return a ranked list
  GET  /health       liveness: the process is up
  GET  /ready        readiness: the model is loaded and servable
"""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from app.features import FeatureError
from app import model as model_mod


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

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
        return jsonify({
            "race": race,
            "field_size": len(ranked),
            "predicted_winner": ranked[0] if ranked else None,
            "ranked": ranked,
        })

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
