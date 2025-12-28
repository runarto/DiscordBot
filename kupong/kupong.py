from api.rapid_sports import get_fixtures
import os
import logging
import discord
from db.db_interface import DB
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
        self._fixtures = get_fixtures(self._auth, days, self._league_id, self._season)['response']

    def _add_fixture(self, fixture, msg_id):
        self._logger.debug(f"Adding fixture: {fixture['fixture']['id']} with message ID: {msg_id}")
        match_id = fixture['fixture']['id']
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        kick_off_time = fixture['fixture']['date']
        self._db.insert_match(match_id, msg_id, home_team, away_team, kick_off_time, self._league_id)
        self._logger.debug(f"Inserted match: {home_team} vs {away_team} with ID: {match_id}")

    def _get_team_display(self, team_name_api: str, is_home: bool) -> tuple[str, str]:
        """Get team display name and emoji, with fallback to defaults."""
        team = self._db.get_team(team_name_api, self._league_id)
        if team:
            return team.team_name_norsk, team.team_emoji
        else:
            # Fallback: use API name and default emoji
            default_emoji = DEFAULT_HOME_EMOJI if is_home else DEFAULT_AWAY_EMOJI
            return team_name_api, default_emoji

    async def _message(self, fixture) -> int:
        """Sends a message for a fixture and returns the message ID."""

        if fixture['fixture']['status']['short'] == 'PST':
            raise ValueError("Fixture is postponed, cannot send message.")

        home_name_api = fixture['teams']['home']['name']
        away_name_api = fixture['teams']['away']['name']

        home_name, home_emoji = self._get_team_display(home_name_api, is_home=True)
        away_name, away_emoji = self._get_team_display(away_name_api, is_home=False)

        msg = f"{home_emoji} {home_name} vs {away_name} {away_emoji}\n"

        self._logger.debug(f"Sending message for fixture: {home_name} vs {away_name}")

        sent_msg = await self._channel.send(msg)
        for reaction in (home_emoji, '🇺', away_emoji):
            await sent_msg.add_reaction(reaction)

        self._logger.debug(f"Message sent with ID: {sent_msg.id} for fixture: {home_name} vs {away_name}")

        return sent_msg.id

    async def send_kupong(self):
        league_name = self._league_config["name"]
        await self._channel.send(f"Ukens kupong ({league_name}):")
        for fixture in self._fixtures:
            try:
                msg_id = await self._message(fixture)
                self._add_fixture(fixture, msg_id)
            except ValueError as e:
                self._logger.warning(f"Skipping fixture {fixture['fixture']['id']} due to error: {e}")






        


    