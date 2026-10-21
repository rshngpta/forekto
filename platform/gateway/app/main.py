"""Forekto platform gateway.

Serves one web page with a sport switch (Horse Racing / Football) and proxies
API calls to the two backend module services. Users see a single site; each
sport remains its own independent service behind the gateway.

Backends are configured by env vars (defaults suit local dev):
  HORSE_URL     (default http://localhost:8080)
  FOOTBALL_URL  (default http://localhost:8081)

In Kubernetes these become the in-cluster service names, e.g.
  HORSE_URL=http://horse-racing   FOOTBALL_URL=http://football
"""
from __future__ import annotations

import os

import requests
from flask import Flask, Response, jsonify, render_template, request

BACKENDS = {
    "horse": os.environ.get("HORSE_URL", "http://localhost:8080"),
    "football": os.environ.get("FOOTBALL_URL", "http://localhost:8081"),
}
TIMEOUT = 10


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    # Proxy: /api/<sport>/<subpath> -> <backend>/api/<subpath>
    @app.route("/api/<sport>/<path:subpath>", methods=["GET", "POST"])
    def proxy(sport: str, subpath: str):
        base = BACKENDS.get(sport)
        if base is None:
            return jsonify({"error": f"unknown sport '{sport}'"}), 404
        url = f"{base}/api/{subpath}"
        try:
            if request.method == "POST":
                r = requests.post(url, json=request.get_json(silent=True), timeout=TIMEOUT)
            else:
                r = requests.get(url, params=request.args, timeout=TIMEOUT)
        except requests.RequestException as exc:
            return jsonify({"error": f"{sport} service unavailable: {exc}"}), 502
        ctype = r.headers.get("Content-Type", "application/json")
        return Response(r.content, status=r.status_code, content_type=ctype)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/ready")
    def ready():
        """Ready when at least one backend answers its health check."""
        up = {}
        for sport, base in BACKENDS.items():
            try:
                up[sport] = requests.get(f"{base}/health", timeout=3).ok
            except requests.RequestException:
                up[sport] = False
        code = 200 if any(up.values()) else 503
        return jsonify({"backends": up}), code

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8000, debug=True)
