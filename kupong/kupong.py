from api.rapid_sports import get_fixtures
import os
import logging
import discord
from db.db_interface import DB

class Kupong:
    """
    Handles the weekly coupon for matches, fetching fixtures and sending messages to a Discord channel.
    """
    def __init__(self, days: int, db: DB, channel: discord.TextChannel, logger: logging.Logger):
        self._auth = os.getenv('API_TOKEN')
        self._db = db
        self._channel = channel
        self._logger = logger
        self._fixtures = get_fixtures(self._auth, days)['response']

    def _add_fixture(self, fixture, msg_id):
        self._logger.debug(f"Adding fixture: {fixture['fixture']['id']} with message ID: {msg_id}")
        match_id = fixture['fixture']['id']
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        kick_off_time = fixture['fixture']['date']
        self._db.insert_match(match_id, msg_id, home_team, away_team, kick_off_time)
        self._logger.debug(f"Inserted match: {home_team} vs {away_team} with ID: {match_id}")

    async def _message(self, fixture) -> tuple[str, str, str]:
        """Sends a message for a fixture and returns the message ID."""
        home_team = self._db.get_team(fixture['teams']['home']['name'])
        away_team = self._db.get_team(fixture['teams']['away']['name'])

        msg = f"{home_team.team_emoji} {home_team.team_name_norsk} vs {away_team.team_name_norsk} {away_team.team_emoji}\n"

        self._logger.debug(f"Sending message for fixture: {home_team.team_name_norsk} vs {away_team.team_name_norsk}")
    
        sent_msg = await self._channel.send(msg)
        for reaction in (home_team.team_emoji, '🇺', away_team.team_emoji):
            await sent_msg.add_reaction(reaction)

        self._logger.debug(f"Message sent with ID: {sent_msg.id} for fixture: {home_team.team_name_norsk} vs {away_team.team_name_norsk}")

        return sent_msg.id

    async def send_kupong(self):
        await self._channel.send("Ukens kupong:")
        for fixture in self._fixtures:
            msg_id = await self._message(fixture)
            self._add_fixture(fixture, msg_id)






        


    