"""
Walk-forward evaluation of MLPredictor vs current ensemble on 2024 and 2025
Eliteserien seasons.

Run from the project root:
    python -m scripts.eval_ml
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from collections import defaultdict
from datetime import datetime, timezone
from typing import List

from db.db_interface import DB
from misc.constants import LEAGUES
from misc.setup import setup_logging
from predictor import (
    from_fotmob, EloPredictor, FormPredictor, GoalsPredictor,
    MLPredictor, EnsemblePredictor, HistoricalMatch,
)
from predictor.calibration import calibrate_rho

EVAL_SEASONS   = [2024, 2025]
TRAIN_LEAGUE_KEYS = ["ELITE", "OBOS"]
DB_PATH        = "infobase.db"


def load_matches(db: DB) -> List[HistoricalMatch]:
    training_ids = {LEAGUES[k]["id"] for k in TRAIN_LEAGUE_KEYS}
    rows = db.get_historical_matches()
    raw = [
        {
            "match_id":   row["match_id"],
            "home_team":  row["home_team"],
            "away_team":  row["away_team"],
            "home_goals": row["home_goals"],
            "away_goals": row["away_goals"],
            "date":       datetime.fromisoformat(row["kick_off_time"]),
            "league_id":  row["league_id"],
            "home_xg":    row["home_xg"],
            "away_xg":    row["away_xg"],
        }
        for row in rows
        if row["league_id"] in training_ids
    ]
    return from_fotmob(raw)


def build_predictor(matches: List[HistoricalMatch], use_ml: bool) -> EnsemblePredictor:
    elo   = EloPredictor()
    form  = FormPredictor()
    goals = GoalsPredictor()
    components = [(elo, 0.30), (form, 0.05), (goals, 0.65)]
    if use_ml:
        ml = MLPredictor()
        components = [(elo, 0.20), (form, 0.05), (goals, 0.50), (ml, 0.25)]
    predictor = EnsemblePredictor(components)
    predictor.train(matches)

    if elo.league_avg_elos:
        max_elo = max(elo.league_avg_elos.values())
        quality = {lid: avg / max_elo for lid, avg in elo.league_avg_elos.items()}
        goals.set_league_quality(quality)

    goals._rho = calibrate_rho(goals, matches)
    return predictor


def evaluate(all_matches: List[HistoricalMatch], eval_seasons: List[int], use_ml: bool) -> dict:
    elite_id = LEAGUES["ELITE"]["id"]
    eval_matches = sorted(
        [m for m in all_matches if m.league_id == elite_id and m.date.year in eval_seasons],
        key=lambda m: m.date,
    )

    correct = defaultdict(int)
    total   = defaultdict(int)
    draw_predicted = draw_correct = 0

    # Group by date to avoid retraining per-match
    from itertools import groupby
    by_date = [(d, list(g)) for d, g in groupby(eval_matches, key=lambda m: m.date.date())]

    for i, (date, day_matches) in enumerate(by_date):
        train_cutoff = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
        train_data = [m for m in all_matches if m.date < train_cutoff]

        if not train_data:
            continue

        predictor = build_predictor(train_data, use_ml)

        for m in day_matches:
            pred = predictor.predict(m.home_team, m.away_team)
            if pred is None:
                continue

            year = str(m.date.year)
            total[year]   += 1
            total["all"]  += 1

            if pred.outcome == m.outcome:
                correct[year]  += 1
                correct["all"] += 1

            if pred.outcome == "D":
                draw_predicted += 1
                if m.outcome == "D":
                    draw_correct += 1

    return {
        "correct":        correct,
        "total":          total,
        "draw_predicted": draw_predicted,
        "draw_correct":   draw_correct,
    }


def fmt(correct, total, label=""):
    if total == 0:
        return f"{label}: N/A"
    return f"{label}: {correct}/{total} ({correct/total:.1%})"


if __name__ == "__main__":
    logger = setup_logging()
    db     = DB(DB_PATH)

    print("Loading matches from DB...")
    all_matches = load_matches(db)
    print(f"  {len(all_matches)} matches loaded\n")

    for use_ml in [False, True]:
        label = "Ensemble + ML" if use_ml else "Current ensemble"
        print(f"--- {label} ---")
        results = evaluate(all_matches, EVAL_SEASONS, use_ml)
        for year in [str(y) for y in EVAL_SEASONS] + ["all"]:
            print(f"  {fmt(results['correct'][year], results['total'][year], year)}")
        print(f"  Draws predicted: {results['draw_predicted']}  correct: {results['draw_correct']}")
        print()
