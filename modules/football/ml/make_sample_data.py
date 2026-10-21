"""Generate a synthetic football-season dataset so the pipeline runs without a
download. Matches the shape of real results data (e.g. football-data.co.uk):

  data/matches.csv  one row per match, with team form, ranks, odds and FTR.

Each team has a latent strength; goals are drawn from Poisson distributions
around that strength (plus home advantage), the full-time result (FTR) is H/D/A,
and the market odds are derived from the true outcome probabilities. Rolling
form and league rank are computed from matches already played, so they carry
real predictive signal. Replace this file with real CSVs and retrain.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict, deque

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(MODULE_ROOT, "data")

N_TEAMS = 16
N_SEASONS = 3
SEED = 42
HOME_ADV = 0.35


def _odds_from_probs(p_h, p_d, p_a, rng):
    # Add a bookmaker margin and noise, then invert to decimal odds.
    probs = np.array([p_h, p_d, p_a]) * rng.normal(1.0, 0.05, 3)
    probs = np.clip(probs, 0.02, 0.95)
    probs = probs / probs.sum() * 1.06  # ~6% overround
    return [round(float(1.0 / x), 2) for x in probs]


def main():
    rng = np.random.default_rng(SEED)
    os.makedirs(DATA_DIR, exist_ok=True)
    teams = [f"Team {chr(65 + i)}" for i in range(N_TEAMS)]
    strength = {t: rng.normal(0, 0.6, None) for t in teams}

    rows = []
    match_day = pd.Timestamp("2023-08-01")

    for season in range(N_SEASONS):
        points = defaultdict(int)
        form = {t: deque(maxlen=5) for t in teams}  # each item: (pts, gf, ga)
        # Double round-robin fixture list.
        fixtures = [(h, a) for h in teams for a in teams if h != a]
        rng.shuffle(fixtures)

        for home, away in fixtures:
            match_day = match_day + pd.Timedelta(days=1)

            def form_stats(t):
                games = form[t]
                if not games:
                    return (1.3, 1.3, 1.3)
                pts = np.mean([g[0] for g in games])
                gf = np.mean([g[1] for g in games])
                ga = np.mean([g[2] for g in games])
                return (pts, gf, ga)

            hp, hgf, hga = form_stats(home)
            ap, agf, aga = form_stats(away)

            # League rank so far (1 = most points).
            standings = sorted(teams, key=lambda t: points[t], reverse=True)
            home_rank = standings.index(home) + 1
            away_rank = standings.index(away) + 1

            # True outcome probabilities from strengths.
            d = strength[home] - strength[away] + HOME_ADV
            lam_h = np.exp(0.2 + 0.6 * d)
            lam_a = np.exp(0.2 - 0.6 * d)
            fthg = rng.poisson(max(0.15, lam_h))
            ftag = rng.poisson(max(0.15, lam_a))
            ftr = "H" if fthg > ftag else ("A" if ftag > fthg else "D")

            # Rough pre-match probs for the odds (expectation-based).
            p_h = 1 / (1 + np.exp(-1.1 * d))
            p_a = 1 / (1 + np.exp(1.1 * d))
            p_d = max(0.12, 1 - p_h - p_a + 0.15)
            s = p_h + p_d + p_a
            p_h, p_d, p_a = p_h / s, p_d / s, p_a / s
            home_odds, draw_odds, away_odds = _odds_from_probs(p_h, p_d, p_a, rng)

            rows.append({
                "date": match_day.strftime("%Y-%m-%d"),
                "season": season + 1,
                "home_team": home, "away_team": away,
                "home_form_points": round(hp, 3), "away_form_points": round(ap, 3),
                "home_form_gf": round(hgf, 3), "home_form_ga": round(hga, 3),
                "away_form_gf": round(agf, 3), "away_form_ga": round(aga, 3),
                "home_rank": home_rank, "away_rank": away_rank,
                "home_odds": home_odds, "draw_odds": draw_odds, "away_odds": away_odds,
                "fthg": int(fthg), "ftag": int(ftag), "ftr": ftr,
            })

            # Update points + form AFTER the match.
            if ftr == "H":
                points[home] += 3
                hpts, apts = 3, 0
            elif ftr == "A":
                points[away] += 3
                hpts, apts = 0, 3
            else:
                points[home] += 1
                points[away] += 1
                hpts, apts = 1, 1
            form[home].append((hpts, fthg, ftag))
            form[away].append((apts, ftag, fthg))

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA_DIR, "matches.csv"), index=False)
    print(f"Wrote {len(df)} matches to {DATA_DIR}")
    print("Outcome mix:", df["ftr"].value_counts().to_dict())


if __name__ == "__main__":
    main()
