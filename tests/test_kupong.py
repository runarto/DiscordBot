"""Tests for Kupong helper methods that do not interact with Discord.

`Kupong.__init__` calls `get_fixtures` from the API, so it is patched in every
fixture to return an empty response list, preventing any real network calls.
`_message` and `send_kupong` are excluded because they require a live Discord
channel object.
"""

import pytest
from unittest.mock import patch, MagicMock

from kupong.kupong import Kupong
from misc.constants import DEFAULT_HOME_EMOJI, DEFAULT_AWAY_EMOJI
from conftest import ELITE_LEAGUE_ID, OBOS_LEAGUE_ID


def make_kupong(db, league_key="ELITE", secondary_league_key=None):
    """Helper: construct a Kupong with the API call patched out."""
    with patch("kupong.kupong.get_fixtures") as mock_gf:
        mock_gf.return_value = {"response": []}
        return Kupong(
            days=7,
            db=db,
            channel=MagicMock(),
            logger=MagicMock(),
            league_key=league_key,
            secondary_league_key=secondary_league_key,
        )


def sample_fixture(fixture_id=12345, home="Brann", away="Rosenborg", status="NS"):
    return {
        "fixture": {
            "id": fixture_id,
            "date": "2026-04-05T15:00:00+02:00",
            "status": {"short": status},
        },
        "teams": {
            "home": {"name": home},
            "away": {"name": away},
        },
    }


# ---------------------------------------------------------------------------
# _get_team_display
# ---------------------------------------------------------------------------

class TestGetTeamDisplay:
    def test_returns_norsk_name_and_emoji_when_team_in_db(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "Brann", "<:Brann:1039844066487185429>")
        kupong = make_kupong(db)
        name, emoji = kupong._get_team_display("Brann", is_home=True)
        assert name == "Brann"
        assert emoji == "<:Brann:1039844066487185429>"

    def test_falls_back_to_api_name_when_not_in_db(self, db):
        kupong = make_kupong(db)
        name, emoji = kupong._get_team_display("Unknown FC", is_home=True)
        assert name == "Unknown FC"
        assert emoji == DEFAULT_HOME_EMOJI

    def test_fallback_uses_away_emoji_for_away_team(self, db):
        kupong = make_kupong(db)
        _, emoji = kupong._get_team_display("Unknown FC", is_home=False)
        assert emoji == DEFAULT_AWAY_EMOJI

    def test_uses_primary_league_id_by_default(self, db):
        # Team exists in OBOS but not ELITE — should fall back
        db.insert_team("TeamA", OBOS_LEAGUE_ID, "TeamA Norsk", "<:A:1>")
        kupong = make_kupong(db, league_key="ELITE")
        name, _ = kupong._get_team_display("TeamA", is_home=True)
        assert name == "TeamA"  # fallback, not "TeamA Norsk"

    def test_uses_explicit_league_id_when_provided(self, db):
        db.insert_team("TeamA", OBOS_LEAGUE_ID, "TeamA Norsk", "<:A:1>")
        kupong = make_kupong(db, league_key="ELITE")
        name, emoji = kupong._get_team_display("TeamA", is_home=True, league_id=OBOS_LEAGUE_ID)
        assert name == "TeamA Norsk"
        assert emoji == "<:A:1>"

    def test_home_and_away_team_emojis_differ(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "Brann", "<:Brann:1>")
        db.insert_team("Molde", ELITE_LEAGUE_ID, "Molde", "<:Molde:2>")
        kupong = make_kupong(db)
        _, home_emoji = kupong._get_team_display("Brann", is_home=True)
        _, away_emoji = kupong._get_team_display("Molde", is_home=False)
        assert home_emoji != away_emoji


# ---------------------------------------------------------------------------
# _add_fixture
# ---------------------------------------------------------------------------

class TestAddFixture:
    def test_inserts_match_with_correct_fields(self, db):
        kupong = make_kupong(db)
        fixture = sample_fixture(fixture_id=12345, home="Brann", away="Rosenborg")
        kupong._add_fixture(fixture, msg_id=101)
        match = db.get_match_by_id(match_id=12345)
        assert match is not None
        assert match.home_team == "Brann"
        assert match.away_team == "Rosenborg"
        assert match.message_id == 101
        assert match.kick_off_time == "2026-04-05T15:00:00+02:00"

    def test_uses_primary_league_id_by_default(self, db):
        kupong = make_kupong(db, league_key="ELITE")
        fixture = sample_fixture(fixture_id=1)
        kupong._add_fixture(fixture, msg_id=10)
        match = db.get_match_by_id(match_id=1)
        assert match.league_id == ELITE_LEAGUE_ID

    def test_uses_explicit_league_id_when_provided(self, db):
        kupong = make_kupong(db, league_key="ELITE")
        fixture = sample_fixture(fixture_id=2)
        kupong._add_fixture(fixture, msg_id=20, league_id=OBOS_LEAGUE_ID)
        match = db.get_match_by_id(match_id=2)
        assert match.league_id == OBOS_LEAGUE_ID

    def test_multiple_fixtures_are_all_inserted(self, db):
        kupong = make_kupong(db)
        for i in range(3):
            kupong._add_fixture(sample_fixture(fixture_id=i + 1, home=f"Home{i}", away=f"Away{i}"), msg_id=100 + i)
        assert len(db.get_all_matches()) == 3

    def test_reinserting_same_match_id_replaces_entry(self, db):
        kupong = make_kupong(db)
        kupong._add_fixture(sample_fixture(fixture_id=1), msg_id=101)
        kupong._add_fixture(sample_fixture(fixture_id=1), msg_id=999)
        assert db.get_match_by_id(match_id=1).message_id == 999


# ---------------------------------------------------------------------------
# Kupong construction / secondary league
# ---------------------------------------------------------------------------

class TestKupongInit:
    def test_primary_fixtures_loaded(self, db):
        primary = [sample_fixture(1), sample_fixture(2)]
        with patch("kupong.kupong.get_fixtures") as mock_gf:
            mock_gf.return_value = {"response": primary}
            kupong = Kupong(days=7, db=db, channel=MagicMock(), logger=MagicMock(), league_key="ELITE")
        assert len(kupong._fixtures) == 2

    def test_no_secondary_league_by_default(self, db):
        kupong = make_kupong(db)
        assert kupong._secondary_fixtures == []
        assert kupong._secondary_league_config is None

    def test_secondary_fixtures_loaded_when_provided(self, db):
        secondary = [sample_fixture(99)]
        with patch("kupong.kupong.get_fixtures") as mock_gf:
            mock_gf.side_effect = [
                {"response": []},       # primary
                {"response": secondary}, # secondary
            ]
            kupong = Kupong(
                days=7, db=db, channel=MagicMock(), logger=MagicMock(),
                league_key="ELITE", secondary_league_key="OBOS"
            )
        assert len(kupong._secondary_fixtures) == 1
        assert kupong._secondary_league_config["id"] == OBOS_LEAGUE_ID

    def test_api_called_twice_when_secondary_league_set(self, db):
        with patch("kupong.kupong.get_fixtures") as mock_gf:
            mock_gf.return_value = {"response": []}
            Kupong(days=7, db=db, channel=MagicMock(), logger=MagicMock(),
                   league_key="ELITE", secondary_league_key="OBOS")
        assert mock_gf.call_count == 2
