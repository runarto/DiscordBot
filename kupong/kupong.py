from api.fotmob import get_fixtures
import os
import logging
import discord
from db.db_interface import DB
from misc.dataclasses import Match
from misc.constants import LEAGUES, DEFAULT_HOME_EMOJI, DEFAULT_AWAY_EMOJI

class Kupong:
    """
    Handles the weekly coupon for matches, fetching fixtures and sending messages to a Discord channel.
    """
    def __init__(self, days: int, db: DB, channel: discord.TextChannel, logger: logging.Logger, league_key: str):
        self._auth = os.getenv('API_TOKEN')
        self._db = db
        self._channel = channel
        self._logger = logger
        self._league_key = league_key
        self._league_config = LEAGUES[league_key]
        self._league_id = self._league_config["id"]
        self._season = self._league_config["season"]
        self._fixtures = get_fixtures(x_days=days, league_id=self._league_id, slug=self._league_config["slug"])

    def _add_fixture(self, fixture: Match, msg_id: int):
        self._logger.debug(f"Adding fixture: {fixture.match_id} with message ID: {msg_id}")
        self._db.insert_match(fixture.match_id, msg_id, fixture.home_team, fixture.away_team, fixture.kick_off_time, self._league_id, fixture.cancelled)
        self._logger.debug(f"Inserted match: {fixture.home_team} vs {fixture.away_team} with ID: {fixture.match_id}")

    def _get_team_display(self, team_name: str, is_home: bool) -> tuple[str, str]:
        """Get team display name and emoji, with fallback to defaults."""
        team = self._db.get_team(team_name, self._league_id)
        if team:
            return team.team_name, team.team_emoji
        else:
            default_emoji = DEFAULT_HOME_EMOJI if is_home else DEFAULT_AWAY_EMOJI
            return team_name, default_emoji

    async def _message(self, fixture: Match) -> int:
        """Sends a message for a fixture and returns the message ID."""

        if fixture.cancelled:
            raise ValueError("Fixture is postponed, cannot send message.")

        home_name, home_emoji = self._get_team_display(fixture.home_team, is_home=True)
        away_name, away_emoji = self._get_team_display(fixture.away_team, is_home=False)

        msg = f"{home_emoji} {home_name} vs {away_name} {away_emoji}\n"

        self._logger.debug(f"Sending message for fixture: {home_name} vs {away_name}")

        sent_msg = await self._channel.send(msg)
        for reaction in (home_emoji, '🇺', away_emoji):
            await sent_msg.add_reaction(reaction)

        self._logger.debug(f"Message sent with ID: {sent_msg.id} for fixture: {home_name} vs {away_name}")

        return sent_msg.id

    async def send_kupong(self):
        await self._channel.send("Ukens kupong:")

        if not self._fixtures:
            self._logger.warning(f"No fixtures found for league {self._league_key} in the given date range.")

        for fixture in self._fixtures:
            try:
                msg_id = await self._message(fixture)
                self._add_fixture(fixture, msg_id)
            except ValueError as e:
                self._logger.warning(f"Skipping fixture {fixture.match_id}: {e}")
            except Exception as e:
                self._logger.error(f"Failed to send fixture {fixture.match_id}: {e}", exc_info=True)
