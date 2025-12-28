# =============================================================================
# cogs/kupong.py - Kupong and results commands
import discord
from discord.ext import commands
from discord import app_commands
from kupong.kupong import Kupong
from kupong.results import Results
import misc.utils as utils
from db.db_interface import DB
from misc.constants import LEAGUES, DEFAULT_LEAGUE

# League choices for command autocomplete
LEAGUE_CHOICES = [
    app_commands.Choice(name=config["name"], value=key)
    for key, config in LEAGUES.items()
]

class KupongCog(commands.Cog, name="Kupong"):
    """Commands for managing kuponger and results"""

    def __init__(self, bot: commands.Bot, db: DB):
        self.db_path = bot.db_path
        self.bot = bot
        self.db = db
        self.logger = bot.logger


    @app_commands.command(name='send_kupong', description='Send ukens kupong for de neste dagene.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.choices(league=LEAGUE_CHOICES)
    async def send_ukens_kupong(self, interaction: discord.Interaction, days: int, channel: discord.TextChannel, league: str = DEFAULT_LEAGUE):

        await interaction.response.defer(ephemeral=True)
        league_name = LEAGUES[league]["name"]
        self.logger.debug(f"Command send_ukens_kupong called by {interaction.user.name} in {channel.mention} for {league_name}.")
        kup = Kupong(days=days, db=self.db, channel=channel, logger=self.logger, league_key=league)
        await kup.send_kupong()
        if self.bot.scheduler.running():
            self.bot.scheduler.shutdown(wait=True)
        self.bot.scheduler.start()
        self.logger.info(f"Ukens kupong ({league_name}) for the next {days} days sent to {channel.mention}.")
        await interaction.followup.send(f"Ukens kupong ({league_name}) for de neste {days} dagene er sendt til {channel.mention}.", ephemeral=True)


    @app_commands.command(name='send_resultater', description='Send ukens resultater for de siste kampene.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.choices(league=LEAGUE_CHOICES)
    async def send_ukens_resultater(self, interaction: discord.Interaction, channel: discord.TextChannel, league: str = DEFAULT_LEAGUE):

        await interaction.response.defer(ephemeral=True)
        await utils.backup_database(self.db_path)
        league_name = LEAGUES[league]["name"]
        self.logger.debug(f"Command send_ukens_resultater called by {interaction.user.name} in {channel.mention} for {league_name}.")
        res = Results(bot=self.bot, db=self.db, channel=channel, logger=self.logger, league_key=league)
        await res.send_results()
        self.logger.info(f"Ukens resultater ({league_name}) sent to {channel.mention}.")
        await interaction.followup.send(f"Ukens resultater ({league_name}) har blitt sendt til {channel.mention}.", ephemeral=True)


    @app_commands.command(name='send_leaderboard', description='Send the total leaderboard.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.choices(league=LEAGUE_CHOICES)
    async def send_leaderboard(self, interaction: discord.Interaction, channel: discord.TextChannel, league: str = DEFAULT_LEAGUE):

        await interaction.response.defer(ephemeral=True)
        league_name = LEAGUES[league]["name"]
        self.logger.debug(f"Command send_leaderboard called by {interaction.user.name} in {channel.mention} for {league_name}.")
        res = Results(bot=self.bot, db=self.db, channel=channel, logger=self.logger, league_key=league)
        await res.send_leaderboard()
        self.logger.info(f"Leaderboard ({league_name}) sent to {channel.mention}.")
        await interaction.followup.send(f"Leaderboard ({league_name}) has been sent to {channel.mention}.", ephemeral=True)


    @app_commands.command(name='store_predictions', description='Store predictions for a specific match.')
    @app_commands.default_permissions(manage_messages=True)
    async def store_predictions(self, interaction: discord.Interaction, content: str, channel: discord.TextChannel):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command store_predictions called by {interaction.user.name} in {channel.mention}.")
        target_message = await utils.get_message(self.db, channel, content)
        if not target_message:
            await interaction.followup.send("No match found with the specified content.", ephemeral=True)
            return
        
        await utils.backup_database(self.db_path)
        await utils.store_predictions(target_message, self.logger, self.db)
        self.logger.info(f"Stored predictions for message {target_message.id}.")
        await interaction.followup.send(f"Predictions for message {target_message.id} have been stored.", ephemeral=True)


    @app_commands.command(name='delete_messages', description='Delete the match messages for a specific league.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.choices(league=LEAGUE_CHOICES)
    async def delete_match_messages(self, interaction: discord.Interaction, channel: discord.TextChannel, league: str = DEFAULT_LEAGUE):

        await interaction.response.defer(ephemeral=True)
        league_name = LEAGUES[league]["name"]
        league_id = LEAGUES[league]["id"]
        self.logger.debug(f"Command delete_match_messages called by {interaction.user.name} in {channel.mention} for {league_name}.")
        matches = self.db.get_matches_by_league(league_id)
        message_ids = [match.message_id for match in matches]

        deleted_count = 0
        for msg_id in message_ids:
            try:
                message = await channel.fetch_message(msg_id)
                await message.delete()
                deleted_count += 1
            except discord.NotFound:
                self.logger.warning(f"Message {msg_id} not found, skipping.")

        # Delete matches for this league from DB
        self.db.delete_matches_by_league(league_id)

        self.logger.info(f"{deleted_count} match messages ({league_name}) deleted in {channel.mention}.")
        await interaction.followup.send(f"{deleted_count} kampmeldinger ({league_name}) har blitt slettet i {channel.mention}.", ephemeral=True)


    @app_commands.command(name='find_cheaters', description='Finds users who reacted after start time for a given game.')
    @app_commands.default_permissions(manage_messages=True)
    async def find_cheaters(self, interaction: discord.Interaction, message_channel: discord.TextChannel, target_channel: discord.TextChannel, content: str = None):

        await interaction.response.defer(ephemeral=True)
        reports = await utils.format_cheater_report_for_matches(db=self.db, message_channel=message_channel, content=content)
        print(f"DEBUG: reports = {reports}")
        if reports == []: 
            await interaction.followup.send("No cheaters found for the specified match.", ephemeral=True)
            return
        #await target_channel.send(f"🚨 **Juksere avslørt:**")

        for report in reports:
            await target_channel.send(f"{report}")

        await interaction.followup.send("✅ Cheater report sent.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(KupongCog(bot))