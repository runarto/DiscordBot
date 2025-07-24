from api.rapid_sports import get_fixtures
import os
import discord

class Kupong:
    def __init__(self, days, db, channel: discord.TextChannel):
        self.auth = os.getenv('API_TOKEN')
        self._db = db
        self._channel = channel
        self._fixtures = get_fixtures(self.auth, days)['response']['fixtures']

    def _add_fixture(self, fixture, msg_id):
        match_id = fixture['fixture']['id']
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        kick_off_time = fixture['fixture']['date']
        self.db.insert_match(match_id, msg_id, home_team, away_team, kick_off_time)

    async def _message(self, fixture) -> tuple[str, str, str]:
        """Sends a message for a fixture and returns the message ID."""

        home_team = self._db.get_team(fixture['teams']['home']['name'])
        away_team = self._db.get_team(fixture['teams']['away']['name'])

        msg = f"{home_team.team_emoji} {home_team.team_name_norsk} vs {away_team.team_name_norsk} {away_team.team_emoji}\n"
        sent_msg = await self._channel.send(msg)
        for reaction in (home_team.team_emoji, '🇺', away_team.team_emoji):
            await sent_msg.add_reaction(reaction)

        return sent_msg.id

    async def send(self):
        self.channel.send("Ukens kupong:")
        for fixture in self._fixtures:
            msg_id = self._message(fixture)
            self._add_fixture(fixture, msg_id)






        


    