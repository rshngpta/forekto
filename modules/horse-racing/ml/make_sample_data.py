"""Generate a synthetic HK-racing-style dataset so the pipeline runs without
the Kaggle download.

It writes two CSVs matching the shape of the real `gdaley/hkracing` data:
  data/races.csv  one row per race  (race_id, date, venue, going, distance)
  data/runs.csv   one row per horse per race

A latent "strength" per horse drives the finishing order, and the market
odds are derived from that strength (favourites win more often), so the model
has real signal to learn. Replace these two files with the real Kaggle CSVs
and everything downstream works unchanged.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(MODULE_ROOT, "data")

N_RACES = 800
SEED = 42

VENUES = ["ST", "HV"]
GOINGS = ["GOOD", "GOOD TO FIRM", "GOOD TO YIELDING", "YIELDING", "WET SLOW"]
DISTANCES = [1000, 1200, 1400, 1600, 1650, 1800, 2000, 2200]
COUNTRIES = ["AUS", "NZ", "IRE", "GB", "USA", "SAF", "FR"]
TYPES = ["Gelding", "Horse", "Mare", "Rig", "Colt", "Filly"]


def _softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()


def main():
    rng = np.random.default_rng(SEED)
    os.makedirs(DATA_DIR, exist_ok=True)

    race_rows = []
    run_rows = []

    for race_id in range(1, N_RACES + 1):
        field = int(rng.integers(8, 15))  # 8..14 runners
        venue = rng.choice(VENUES)
        going = rng.choice(GOINGS)
        distance = int(rng.choice(DISTANCES))
        day = pd.Timestamp("2015-01-01") + pd.Timedelta(days=int(race_id))

        race_rows.append({
            "race_id": race_id,
            "date": day.strftime("%Y-%m-%d"),
            "venue": venue,
            "going": going,
            "distance": distance,
        })

        draws = rng.permutation(np.arange(1, field + 1))
        # Latent ability, with a mild low-draw advantage.
        strength = rng.normal(0, 1, size=field)
        strength += (field / 2.0 - draws) * 0.03
        probs = _softmax(strength * 1.15)
        winner_idx = rng.choice(field, p=probs)

        # Market odds reflect ability (favourites short), with noise + overround.
        implied = probs * 0.82
        implied = np.clip(implied, 0.01, 0.95)
        win_odds = np.clip(1.0 / implied * rng.normal(1.0, 0.12, size=field),
                           1.1, 99.0)

        for i in range(field):
            run_rows.append({
                "race_id": race_id,
                "horse_no": i + 1,
                "horse_id": int(rng.integers(1, 4000)),
                "draw": int(draws[i]),
                "horse_age": int(rng.integers(2, 8)),
                "horse_country": rng.choice(COUNTRIES,
                                            p=[0.45, 0.2, 0.1, 0.1, 0.05, 0.05, 0.05]),
                "horse_type": rng.choice(TYPES,
                                         p=[0.6, 0.1, 0.1, 0.05, 0.075, 0.075]),
                "actual_weight": int(rng.integers(113, 134)),
                "declared_weight": int(rng.normal(1100, 40)),
                "win_odds": round(float(win_odds[i]), 1),
                "result": 0,  # filled below
                "won": 1 if i == winner_idx else 0,
            })

    races = pd.DataFrame(race_rows)
    runs = pd.DataFrame(run_rows)

    # Assign plausible finishing positions: winner first, rest by odds + noise.
    runs["_rand"] = np.random.default_rng(SEED + 1).normal(0, 1, len(runs))
    ordered = []
    for rid, grp in runs.groupby("race_id"):
        grp = grp.copy()
        grp["_key"] = grp["win_odds"] + grp["_rand"]
        grp.loc[grp["won"] == 1, "_key"] = -1e9  # winner first
        grp = grp.sort_values("_key")
        grp["result"] = range(1, len(grp) + 1)
        ordered.append(grp.drop(columns=["_key"]))
    runs = pd.concat(ordered).drop(columns=["_rand"]).sort_values(
        ["race_id", "horse_no"]).reset_index(drop=True)

    races.to_csv(os.path.join(DATA_DIR, "races.csv"), index=False)
    runs.to_csv(os.path.join(DATA_DIR, "runs.csv"), index=False)
    print(f"Wrote {len(races)} races and {len(runs)} runs to {DATA_DIR}")


if __name__ == "__main__":
    main()
