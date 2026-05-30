"""Tests for Kupong helper methods that do not interact with Discord.

`Kupong.__init__` calls `get_fixtures` from the API, so it is patched in every
fixture to return an empty list, preventing any real network calls.
`_message` and `send_kupong` are excluded because they require a live Discord
channel object.
"""

import pytest
from unittest.mock import patch, MagicMock

from kupong.kupong import Kupong
from misc.constants import COUNTRY_FLAGS, COUNTRY_NORWEGIAN_NAMES, DEFAULT_HOME_EMOJI, DEFAULT_AWAY_EMOJI, LEAGUES
from conftest import ELITE_LEAGUE_ID, OBOS_LEAGUE_ID

WORLD_CUP_LEAGUE_ID = LEAGUES["WORLD_CUP"]["id"]


def make_kupong(db, league_key="ELITE"):
    """Helper: construct a Kupong with the API call patched out."""
    with patch("kupong.kupong.get_fixtures") as mock_gf:
        mock_gf.return_value = []
        return Kupong(
            days=7,
            db=db,
            channel=MagicMock(),
            logger=MagicMock(),
            league_key=league_key,
        )


def sample_fixture(fixture_id=12345, home="Brann", away="Rosenborg"):
    from misc.dataclasses import Match
    return Match(
        match_id=fixture_id,
        message_id=0,
        home_team=home,
        away_team=away,
        kick_off_time="2026-04-05T15:00:00+02:00",
        cancelled=False,
        league_id=ELITE_LEAGUE_ID,
    )


# ---------------------------------------------------------------------------
# _get_team_display
# ---------------------------------------------------------------------------

class TestGetTeamDisplay:
    def test_returns_name_and_emoji_when_team_in_db(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "<:Brann:1039844066487185429>")
        kupong = make_kupong(db)
        name, emoji = kupong._get_team_display("Brann", is_home=True)
        assert name == "Brann"
        assert emoji == "<:Brann:1039844066487185429>"

    def test_falls_back_to_name_when_not_in_db(self, db):
        kupong = make_kupong(db)
        name, emoji = kupong._get_team_display("Unknown FC", is_home=True)
        assert name == "Unknown FC"
        assert emoji == DEFAULT_HOME_EMOJI

    def test_fallback_uses_away_emoji_for_away_team(self, db):
        kupong = make_kupong(db)
        _, emoji = kupong._get_team_display("Unknown FC", is_home=False)
        assert emoji == DEFAULT_AWAY_EMOJI

    def test_team_in_different_league_is_not_found(self, db):
        db.insert_team("TeamA", OBOS_LEAGUE_ID, "<:A:1>")
        kupong = make_kupong(db, league_key="ELITE")
        name, emoji = kupong._get_team_display("TeamA", is_home=True)
        assert name == "TeamA"  # fallback
        assert emoji == DEFAULT_HOME_EMOJI

    def test_home_and_away_team_emojis_differ(self, db):
        db.insert_team("Brann", ELITE_LEAGUE_ID, "<:Brann:1>")
        db.insert_team("Molde", ELITE_LEAGUE_ID, "<:Molde:2>")
        kupong = make_kupong(db)
        _, home_emoji = kupong._get_team_display("Brann", is_home=True)
        _, away_emoji = kupong._get_team_display("Molde", is_home=False)
        assert home_emoji != away_emoji

    def test_world_cup_uses_country_flag_fallback(self, db):
        kupong = make_kupong(db, league_key="WORLD_CUP")
        name, emoji = kupong._get_team_display("Brazil", is_home=True)
        assert name == "Brasil"
        assert emoji == "🇧🇷"

    def test_world_cup_db_mapping_overrides_country_flag(self, db):
        db.insert_team("Brazil", WORLD_CUP_LEAGUE_ID, "<:Brazil:1>")
        kupong = make_kupong(db, league_key="WORLD_CUP")
        name, emoji = kupong._get_team_display("Brazil", is_home=True)
        assert name == "Brazil"
        assert emoji == "<:Brazil:1>"

    def test_world_cup_unknown_team_uses_home_away_fallback(self, db):
        kupong = make_kupong(db, league_key="WORLD_CUP")
        _, home_emoji = kupong._get_team_display("Unknown FC", is_home=True)
        _, away_emoji = kupong._get_team_display("Unknown FC", is_home=False)
        assert home_emoji == DEFAULT_HOME_EMOJI
        assert away_emoji == DEFAULT_AWAY_EMOJI

    def test_world_cup_country_flags_include_subdivision_flags(self):
        assert COUNTRY_FLAGS["England"].startswith("🏴")
        assert COUNTRY_FLAGS["Scotland"].startswith("🏴")
        assert COUNTRY_FLAGS["Wales"].startswith("🏴")

    def test_world_cup_uses_fotmob_name_translations(self, db):
        kupong = make_kupong(db, league_key="WORLD_CUP")
        assert kupong._get_team_display("DR Congo", is_home=True) == ("DR Kongo", "🇨🇩")
        assert kupong._get_team_display("Turkiye", is_home=True) == ("Tyrkia", "🇹🇷")
        assert kupong._get_team_display("South Korea", is_home=True) == ("Sør-Korea", "🇰🇷")

    def test_world_cup_translation_map_covers_flag_map(self):
        missing = sorted(set(COUNTRY_FLAGS) - set(COUNTRY_NORWEGIAN_NAMES))
        assert missing == []


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

    def test_uses_league_id(self, db):
        kupong = make_kupong(db, league_key="ELITE")
        kupong._add_fixture(sample_fixture(fixture_id=1), msg_id=10)
        assert db.get_match_by_id(match_id=1).league_id == ELITE_LEAGUE_ID

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
# Kupong construction
# ---------------------------------------------------------------------------

class TestKupongInit:
    def test_fixtures_loaded(self, db):
        fixtures = [sample_fixture(1), sample_fixture(2)]
        with patch("kupong.kupong.get_fixtures") as mock_gf:
            mock_gf.return_value = fixtures
            kupong = Kupong(days=7, db=db, channel=MagicMock(), logger=MagicMock(), league_key="ELITE")
        assert len(kupong._fixtures) == 2

    def test_api_called_once(self, db):
        with patch("kupong.kupong.get_fixtures") as mock_gf:
            mock_gf.return_value = []
            Kupong(days=7, db=db, channel=MagicMock(), logger=MagicMock(), league_key="ELITE")
        assert mock_gf.call_count == 1

    def test_world_cup_uses_fotmob_id_and_slug(self, db):
        with patch("kupong.kupong.get_fixtures") as mock_gf:
            mock_gf.return_value = []
            Kupong(days=7, db=db, channel=MagicMock(), logger=MagicMock(), league_key="WORLD_CUP")
        mock_gf.assert_called_once_with(x_days=7, league_id=77, slug="world-cup")

    def test_world_cup_disables_predictor(self, db):
        with patch("kupong.kupong.get_fixtures") as mock_gf:
            mock_gf.return_value = []
            kupong = Kupong(
                days=7,
                db=db,
                channel=MagicMock(),
                logger=MagicMock(),
                league_key="WORLD_CUP",
                predictor=MagicMock(),
            )
        assert kupong._predictor is None
