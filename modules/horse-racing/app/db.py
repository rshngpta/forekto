"""Persistence layer for predictions and their outcomes.

Every prediction the service makes can be stored, and later resolved with the
race's actual winner. The accuracy dashboard is computed from these rows.

Database is chosen by the DATABASE_URL env var:
  * unset            -> SQLite file at data/forekto.db (zero setup, local dev)
  * postgresql://... -> Postgres (production / RDS)

The same code works against both. Persistence is best-effort: if the DB is
unavailable, predictions still succeed (the API never fails because of logging).
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, Integer, String, Text, create_engine, select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SQLITE = "sqlite:///" + os.path.join(MODULE_ROOT, "data", "forekto.db")


class Base(DeclarativeBase):
    pass


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    sport: Mapped[str] = mapped_column(String(32), default="horse-racing")
    source: Mapped[str] = mapped_column(String(16), default="live")  # live | backtest

    race: Mapped[str] = mapped_column(Text)            # JSON
    n_runners: Mapped[int] = mapped_column(Integer)
    ranked: Mapped[str] = mapped_column(Text)          # JSON (full ranked field)

    predicted_winner: Mapped[str] = mapped_column(String(128))
    predicted_winner_prob: Mapped[float] = mapped_column(Float)
    favourite_pick: Mapped[str] = mapped_column(String(128))  # lowest-odds horse

    actual_winner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    favourite_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL", DEFAULT_SQLITE)
        if url.startswith("sqlite"):
            os.makedirs(os.path.join(MODULE_ROOT, "data"), exist_ok=True)
        _engine = create_engine(url, future=True)
        Base.metadata.create_all(_engine)
    return _engine


def reset_engine():
    """Test helper: drop the cached engine so a new DATABASE_URL takes effect."""
    global _engine
    _engine = None


def _favourite(ranked: list) -> str:
    """The lowest-odds runner's name (the market favourite)."""
    with_odds = [r for r in ranked if r.get("win_odds") is not None]
    if not with_odds:
        return ranked[0].get("name", "") if ranked else ""
    return min(with_odds, key=lambda r: r["win_odds"]).get("name", "")


def save_prediction(race: dict, ranked: list, source: str = "live",
                    actual_winner: str | None = None) -> int | None:
    """Store a prediction (best-effort). Returns the row id, or None on failure."""
    try:
        top = ranked[0]
        fav = _favourite(ranked)
        row = Prediction(
            sport="horse-racing",
            source=source,
            race=json.dumps(race),
            n_runners=len(ranked),
            ranked=json.dumps(ranked),
            predicted_winner=top.get("name", ""),
            predicted_winner_prob=float(top.get("win_probability", 0.0)),
            favourite_pick=fav,
        )
        if actual_winner is not None:
            row.actual_winner = actual_winner
            row.is_correct = (actual_winner == row.predicted_winner)
            row.favourite_correct = (actual_winner == fav)
        with Session(get_engine()) as s:
            s.add(row)
            s.commit()
            return row.id
    except Exception:
        return None


def set_outcome(prediction_id: int, actual_winner: str) -> bool:
    """Record the real winner for a stored prediction."""
    try:
        with Session(get_engine()) as s:
            row = s.get(Prediction, prediction_id)
            if row is None:
                return False
            row.actual_winner = actual_winner
            row.is_correct = (actual_winner == row.predicted_winner)
            row.favourite_correct = (actual_winner == row.favourite_pick)
            s.commit()
            return True
    except Exception:
        return False


def recent_predictions(limit: int = 20) -> list[dict]:
    try:
        with Session(get_engine()) as s:
            rows = s.scalars(
                select(Prediction).order_by(Prediction.id.desc()).limit(limit)
            ).all()
            return [_row_dict(r) for r in rows]
    except Exception:
        return []


def _row_dict(r: Prediction) -> dict:
    return {
        "id": r.id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "source": r.source,
        "n_runners": r.n_runners,
        "predicted_winner": r.predicted_winner,
        "predicted_winner_prob": r.predicted_winner_prob,
        "favourite_pick": r.favourite_pick,
        "actual_winner": r.actual_winner,
        "is_correct": r.is_correct,
    }


def compute_metrics() -> dict:
    """Aggregate accuracy stats for the dashboard."""
    try:
        with Session(get_engine()) as s:
            rows = s.scalars(select(Prediction)).all()
    except Exception:
        rows = []

    total = len(rows)
    resolved = [r for r in rows if r.is_correct is not None]
    n_resolved = len(resolved)
    model_hits = sum(1 for r in resolved if r.is_correct)
    fav_hits = sum(1 for r in resolved if r.favourite_correct)

    # Accuracy by week (for the trend).
    by_week = defaultdict(lambda: [0, 0])  # week -> [hits, total]
    for r in resolved:
        wk = r.created_at.strftime("%Y-W%W") if r.created_at else "n/a"
        by_week[wk][0] += 1 if r.is_correct else 0
        by_week[wk][1] += 1

    # Calibration: bin by the winner's predicted probability.
    bins = [(0.0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 1.01)]
    calib = []
    for lo, hi in bins:
        grp = [r for r in resolved if lo <= r.predicted_winner_prob < hi]
        if grp:
            obs = sum(1 for r in grp if r.is_correct) / len(grp)
            avg_pred = sum(r.predicted_winner_prob for r in grp) / len(grp)
            calib.append({
                "range": f"{int(lo*100)}–{int(hi*100)}%",
                "n": len(grp),
                "avg_predicted": round(avg_pred, 3),
                "observed": round(obs, 3),
            })

    return {
        "total_predictions": total,
        "resolved": n_resolved,
        "pending": total - n_resolved,
        "model_hit_rate": round(model_hits / n_resolved, 3) if n_resolved else None,
        "favourite_hit_rate": round(fav_hits / n_resolved, 3) if n_resolved else None,
        "model_vs_favourite": (
            round((model_hits - fav_hits) / n_resolved, 3) if n_resolved else None
        ),
        "accuracy_by_week": [
            {"week": wk, "hit_rate": round(h / t, 3), "n": t}
            for wk, (h, t) in sorted(by_week.items())
        ],
        "calibration": calib,
    }
