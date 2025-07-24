# =============================================================================
# cogs/kupong.py - Kupong and results commands
import discord
from discord.ext import commands
from discord import app_commands
from commands.kupong import Kupong
from commands.results import Results
from misc.utils import store_predictions, backup_database

class KupongCog(commands.Cog, name="Kupong"):
    """Commands for managing kuponger and results"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='ukens_kupong', description='Send ukens kupong for de neste dagene.')
    @app_commands.default_permissions(manage_messages=True)
    async def send_ukens_kupong(self, interaction: discord.Interaction, days: int, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        kup = Kupong(days=days, db=self.bot.db, channel=channel, logger=self.bot.logger)
        self.db.flush_table("matches")
        await kup.send_msg()
        self.bot.scheduler.start()
        self.bot.logger.info(f"Ukens kupong for the next {days} days sent to {channel.mention}.")
        await interaction.followup.send(f"Ukens kupong for de neste {days} dagene er sendt til {channel.mention}.", ephemeral=True)


    @app_commands.command(name='ukens_resultater', description='Send ukens resultater for de siste kampene.')
    @app_commands.default_permissions(manage_messages=True)
    async def send_ukens_resultater(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        backup_database(self.bot.db_path)
        res = Results(db=self.bot.db, channel=channel, logger=self.bot.logger)
        await res.send_results()
        self.bot.logger.info(f"Ukens resultater sent to {channel.mention}.")
        await interaction.followup.send(f"Ukens resultater har blitt sendt til {channel.mention}.", ephemeral=True)


    @app_commands.command(name='leaderboard', description='Send the total leaderboard.')
    @app_commands.default_permissions(manage_messages=True)
    async def send_leaderboard(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        res = Results(db=self.bot.db, channel=channel, logger=self.bot.logger)
        await res.send_leaderboard()
        self.bot.logger.info(f"Leaderboard sent to {channel.mention}.")
        await interaction.followup.send(f"Leaderboard has been sent to {channel.mention}.", ephemeral=True)


    @app_commands.command(name='store_predictions', description='Store predictions for a specific match.')
    @app_commands.default_permissions(manage_messages=True)
    async def store_predictions(self, interaction: discord.Interaction, message_id: str, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        try:
            message = await channel.fetch_message(message_id)
            backup_database(self.bot.db_path)
            await store_predictions(message, self.bot.logger, self.bot.db)
            self.bot.logger.debug(f"Stored predictions for message {message_id}.")
            await interaction.followup.send(f"Predictions for message {message_id} have been stored.", ephemeral=True)
        except Exception as e:
            self.bot.logger.debug(f"Failed to store predictions for message {message_id}: {e}")
            await interaction.followup.send(f"Failed to store predictions for message {message_id}.", ephemeral=True)


    @app_commands.command(name='delete_messages', description='Delete the match messages.')
    @app_commands.default_permissions(manage_messages=True)
    async def delete_match_messages(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Delete all match messages in the specified channel. Also flushes the matches table."""
        await interaction.response.defer(ephemeral=True)
        info = self.bot.db.get_all_matches()
        message_ids = [match.message_id for match in info]

        for msg_id in message_ids:
            message = await channel.fetch_message(msg_id)
            await message.delete()

        self.bot.db.flush_table("matches")
        
        self.bot.logger.info(f"All match messages deleted in {channel.mention}. Table 'matches' flushed.")
        await interaction.followup.send(f"All match messages have been deleted in {channel.mention}.", ephemeral=True)


    @app_commands.command(name='adjust_score', description='Manually adjust a user\'s score and wins.')
    @app_commands.default_permissions(manage_messages=True)
    async def adjust_score(self, interaction: discord.Interaction, user: discord.User, points: int = 0, wins: int = 0):
        await interaction.response.defer(ephemeral=True)
        self.bot.db.upsert_score(user_id=user.id, points_delta=points, win_delta=wins)
        self.bot.logger.info(f"Adjusted score for {user.mention}: {points} points, {wins} wins.")
        await interaction.followup.send(f"Adjusted {user.mention}'s score by {points} points and {wins} wins.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(KupongCog(bot))