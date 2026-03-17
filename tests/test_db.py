"""Tests for all DB read/write operations using an in-memory SQLite database.

The `db` fixture is defined in conftest.py and provides a fresh DB(:memory:)
instance for every test so there is no state leakage between tests.
"""

import pytest
from conftest import ELITE_LEAGUE_ID, OBOS_LEAGUE_ID


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

class TestMatches:
    def test_insert_and_retrieve_by_match_id(self, db):
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        match = db.get_match_by_id(match_id=1)
        assert match is not None
        assert match.home_team == "Brann"
        assert match.away_team == "Rosenborg"
        assert match.league_id == ELITE_LEAGUE_ID

    def test_retrieve_by_message_id(self, db):
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        match = db.get_match_by_id(message_id=101)
        assert match is not None
        assert match.match_id == 1

    def test_get_all_matches_empty(self, db):
        assert db.get_all_matches() == []

    def test_get_all_matches_returns_all(self, db):
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        db.insert_match(2, 102, "Molde", "Viking", "2026-04-06T15:00:00+02:00", ELITE_LEAGUE_ID)
        assert len(db.get_all_matches()) == 2

    def test_get_matches_by_league_filters_correctly(self, db):
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        db.insert_match(2, 102, "TeamA", "TeamB", "2026-04-06T15:00:00+02:00", OBOS_LEAGUE_ID)
        matches = db.get_matches_by_league(ELITE_LEAGUE_ID)
        assert len(matches) == 1
        assert matches[0].home_team == "Brann"

    def test_insert_replaces_existing_match_id(self, db):
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        db.insert_match(1, 999, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        match = db.get_match_by_id(match_id=1)
        assert match.message_id == 999

    def test_get_nonexistent_match_returns_none(self, db):
        assert db.get_match_by_id(match_id=999) is None

    def test_delete_matches_by_league(self, db):
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        db.insert_match(2, 102, "TeamA", "TeamB", "2026-04-06T15:00:00+02:00", OBOS_LEAGUE_ID)
        db.delete_matches_by_league(ELITE_LEAGUE_ID)
        assert db.get_matches_by_league(ELITE_LEAGUE_ID) == []
        assert len(db.get_matches_by_league(OBOS_LEAGUE_ID)) == 1

    def test_matches_ordered_by_kick_off_time(self, db):
        db.insert_match(2, 102, "Molde", "Viking", "2026-04-06T15:00:00+02:00", ELITE_LEAGUE_ID)
        db.insert_match(1, 101, "Brann", "Rosenborg", "2026-04-05T15:00:00+02:00", ELITE_LEAGUE_ID)
        matches = db.get_all_matches()
        assert matches[0].match_id == 1
        assert matches[1].match_id == 2


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

class TestPredictions:
    def test_insert_and_retrieve_prediction(self, db):
        db.insert_prediction(101, "user1", "H")
        pred = db.get_prediction(101, "user1")
        assert pred is not None
        assert pred.prediction == "H"

    def test_get_prediction_not_found(self, db):
        assert db.get_prediction(999, "user1") is None

    def test_get_all_predictions_for_match(self, db):
        db.insert_prediction(101, "user1", "H")
        db.insert_prediction(101, "user2", "D")
        db.insert_prediction(101, "user3", "A")
        preds = db.get_all_predictions_for_match(101)
        assert len(preds) == 3

    def test_predictions_isolated_per_match(self, db):
        db.insert_prediction(101, "user1", "H")
        db.insert_prediction(102, "user1", "A")
        assert len(db.get_all_predictions_for_match(101)) == 1
        assert len(db.get_all_predictions_for_match(102)) == 1

    def test_get_predictions_for_user_across_matches(self, db):
        db.insert_prediction(101, "user1", "H")
        db.insert_prediction(102, "user1", "A")
        preds = db.get_predictions_for_user("user1")
        assert len(preds) == 2

    def test_insert_replaces_existing_prediction(self, db):
        db.insert_prediction(101, "user1", "H")
        db.insert_prediction(101, "user1", "A")
        pred = db.get_prediction(101, "user1")
        assert pred.prediction == "A"

    def test_no_predictions_for_match_returns_empty(self, db):
        assert db.get_all_predictions_for_match(999) == []

    def test_flush_predictions_table(self, db):
        db.insert_prediction(101, "user1", "H")
        db.flush_table("predictions")
        assert db.get_all_predictions_for_match(101) == []


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------

class TestScores:
    def test_upsert_creates_new_score(self, db):
        db.upsert_score("user1", ELITE_LEAGUE_ID, points_delta=3)
        score = db.get_user_score("user1", ELITE_LEAGUE_ID)
        assert score is not None
        assert score.points == 3

    def test_upsert_accumulates_points(self, db):
        db.upsert_score("user1", ELITE_LEAGUE_ID, points_delta=3)
        db.upsert_score("user1", ELITE_LEAGUE_ID, points_delta=1)
        assert db.get_user_score("user1", ELITE_LEAGUE_ID).points == 4

    def test_upsert_accumulates_weekly_wins(self, db):
        db.upsert_score("user1", ELITE_LEAGUE_ID, win_delta=1)
        db.upsert_score("user1", ELITE_LEAGUE_ID, win_delta=1)
        assert db.get_user_score("user1", ELITE_LEAGUE_ID).weekly_wins == 2

    def test_score_isolated_per_league(self, db):
        db.upsert_score("user1", ELITE_LEAGUE_ID, points_delta=5)
        db.upsert_score("user1", OBOS_LEAGUE_ID, points_delta=2)
        assert db.get_user_score("user1", ELITE_LEAGUE_ID).points == 5
        assert db.get_user_score("user1", OBOS_LEAGUE_ID).points == 2

    def test_get_scores_by_league_filters_correctly(self, db):
        db.upsert_score("user1", ELITE_LEAGUE_ID, points_delta=5)
        db.upsert_score("user2", OBOS_LEAGUE_ID, points_delta=3)
        scores = db.get_scores_by_league(ELITE_LEAGUE_ID)
        assert len(scores) == 1
        assert scores[0].user_id == "user1"

    def test_scores_ordered_by_points_descending(self, db):
        db.upsert_score("user1", ELITE_LEAGUE_ID, points_delta=1)
        db.upsert_score("user2", ELITE_LEAGUE_ID, points_delta=5)
        scores = db.get_scores_by_league(ELITE_LEAGUE_ID)
        assert scores[0].user_id == "user2"

    def test_get_score_not_found_returns_none(self, db):
        assert db.get_user_score("ghost", ELITE_LEAGUE_ID) is None

    def test_get_all_scores_returns_all(self, db):
        db.upsert_score("user1", ELITE_LEAGUE_ID, points_delta=3)
        db.upsert_score("user2", OBOS_LEAGUE_ID, points_delta=2)
        assert len(db.get_all_scores()) == 2


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class TestUsers:
    def test_insert_and_retrieve_user(self, db):
        db.insert_user("123", "testuser", "Test User", "🔥")
        user = db.get_user("123")
        assert user is not None
        assert user.user_name == "testuser"
        assert user.user_display_name == "Test User"
        assert user.user_emoji == "🔥"

    def test_insert_user_without_emoji(self, db):
        db.insert_user("123", "testuser", "Test User")
        assert db.get_user("123").user_emoji is None

    def test_get_user_not_found_returns_none(self, db):
        assert db.get_user("999") is None

    def test_insert_replaces_existing_user(self, db):
        db.insert_user("123", "old_name", "Old Name")
        db.insert_user("123", "new_name", "New Name")
        assert db.get_user("123").user_name == "new_name"

    def test_get_all_users(self, db):
        db.insert_user("1", "user1", "User One")
        db.insert_user("2", "user2", "User Two")
        assert len(db.get_all_users()) == 2

    def test_get_all_users_empty(self, db):
        assert db.get_all_users() == []


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TestTeams:
    def test_insert_and_retrieve_team(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "<:Brann:1039844066487185429>")
        team = db.get_team("Brann", ELITE_LEAGUE_ID)
        assert team is not None
        assert team.team_name == "Brann"
        assert team.team_emoji == "<:Brann:1039844066487185429>"

    def test_get_team_not_found_returns_none(self, db):
        assert db.get_team("Unknown FC", ELITE_LEAGUE_ID) is None

    def test_get_teams_by_league_filters_correctly(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "<:Brann:123>")
        db.insert_team("Molde", ELITE_LEAGUE_ID, "<:Molde:456>")
        db.insert_team("TeamA", OBOS_LEAGUE_ID, "🏠")
        assert len(db.get_teams_by_league(ELITE_LEAGUE_ID)) == 2

    def test_same_team_name_different_leagues_are_separate(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "<:BrannE:1>")
        db.insert_team("Brann", OBOS_LEAGUE_ID, "<:BrannO:2>")
        assert db.get_team("Brann", ELITE_LEAGUE_ID).team_emoji == "<:BrannE:1>"
        assert db.get_team("Brann", OBOS_LEAGUE_ID).team_emoji == "<:BrannO:2>"

    def test_insert_replaces_existing_team(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "<:Old:1>")
        db.insert_team("Brann", ELITE_LEAGUE_ID, "<:New:2>")
        assert db.get_team("Brann", ELITE_LEAGUE_ID).team_emoji == "<:New:2>"
