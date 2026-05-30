"""Tests for result scoring rules."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from kupong.results import Results, world_cup_points_by_outcome
from misc.constants import LEAGUES
from misc.dataclasses import Prediction

ELITE_LEAGUE_ID = LEAGUES["ELITE"]["id"]
WORLD_CUP_LEAGUE_ID = LEAGUES["WORLD_CUP"]["id"]


def prediction(user_id, outcome):
    return Prediction(message_id=101, user_id=user_id, prediction=outcome)


def make_results(db, league_key):
    bot = SimpleNamespace(user=SimpleNamespace(id=999, name="Bot"))
    return Results(bot=bot, db=db, channel=MagicMock(), logger=MagicMock(), league_key=league_key)


class TestWorldCupPointsByOutcome:
    def test_popularity_points_for_three_distinct_counts(self):
        predictions = [
            prediction("h1", "H"),
            prediction("h2", "H"),
            prediction("h3", "H"),
            prediction("d1", "D"),
            prediction("d2", "D"),
            prediction("a1", "A"),
        ]

        assert world_cup_points_by_outcome(predictions) == {"H": 1, "D": 2, "A": 3}

    def test_tied_outcomes_share_points(self):
        predictions = [
            prediction("h1", "H"),
            prediction("h2", "H"),
            prediction("d1", "D"),
            prediction("d2", "D"),
            prediction("a1", "A"),
        ]

        assert world_cup_points_by_outcome(predictions) == {"H": 1, "D": 1, "A": 2}


class TestIncrementScore:
    def test_world_cup_scores_correct_rare_outcome_with_bonus_points(self, db):
        db.insert_match(1, 101, "Brazil", "Japan", "2026-06-11T18:00:00+00:00", WORLD_CUP_LEAGUE_ID)
        for user_id, outcome in [
            ("h1", "H"),
            ("h2", "H"),
            ("h3", "H"),
            ("d1", "D"),
            ("d2", "D"),
            ("a1", "A"),
        ]:
            db.insert_prediction(101, user_id, outcome)

        results = make_results(db, "WORLD_CUP")
        results._match_results = {1: "A"}
        results._increment_score()

        assert db.get_user_score("a1", WORLD_CUP_LEAGUE_ID).points == 3
        assert db.get_user_score("h1", WORLD_CUP_LEAGUE_ID) is None
        assert db.get_user_score("d1", WORLD_CUP_LEAGUE_ID) is None

    def test_normal_leagues_still_score_one_point(self, db):
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+00:00", ELITE_LEAGUE_ID)
        for user_id, outcome in [
            ("h1", "H"),
            ("h2", "H"),
            ("h3", "H"),
            ("d1", "D"),
            ("d2", "D"),
            ("a1", "A"),
        ]:
            db.insert_prediction(101, user_id, outcome)

        results = make_results(db, "ELITE")
        results._match_results = {1: "A"}
        results._increment_score()

        assert db.get_user_score("a1", ELITE_LEAGUE_ID).points == 1
