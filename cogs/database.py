# =============================================================================
# cogs/database.py - Database management commands
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from db.db_interface import DB 
import misc.utils as utils

class DatabaseCog(commands.Cog, name="Database"):
    """Database synchronization and management commands"""
    
    def __init__(self, bot: commands.Bot, db: DB):
        self.bot = bot
        self.db = db
        self.logger = bot.logger

    @app_commands.command(name='flush_table', description='Flush a table in the database.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.choices(table=[
        app_commands.Choice(name='matches', value='matches'),
        app_commands.Choice(name='predictions', value='predictions'),
        app_commands.Choice(name='users', value='users'),
    ])
    async def flush_table(self, interaction: discord.Interaction, table: app_commands.Choice[str]):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command flush_table called by {interaction.user.name} for table {table.value}.")
        self.db.flush_table(table.value)
        self.logger.info(f"{table.value.capitalize()} table flushed.")
        await interaction.followup.send(f"**{table.value}** table has been flushed.", ephemeral=True)


    @app_commands.command(name='add_team_emoji', description='Maps a team role to an emoji.')
    @app_commands.default_permissions(manage_messages=True)
    async def add_team_emoji(self, interaction: discord.Interaction, role: discord.Role, emoji: str):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command add_team_emoji called by {interaction.user.name} for role {role.name} with emoji {emoji}.")
        self.db.insert_team_emoji(role.name, emoji)
        self.logger.info("Team emoji added for role: {role.name} with emoji: {emoji}")
        await interaction.followup.send("Team emojis have been mapped successfully.", ephemeral=True)

    
    @app_commands.command(name='update_user_emoji', description='Update the emoji for a user.')
    @app_commands.default_permissions(manage_messages=True)
    async def update_user_emoji(self, interaction: discord.Interaction, user: discord.User, emoji: str):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command update_user_emoji called by {interaction.user.name} for user {user.name} with emoji {emoji}.")
        self.db.insert_user(user.id, user.name, user.display_name, emoji)
        self.logger.info(f"Updated emoji for {user.mention} to {emoji}.")
        await interaction.followup.send(f"Emoji for {user.mention} has been updated to {emoji}.", ephemeral=True)


    @app_commands.command(name='get_prediction', description='Check predictions based on user and/or message ID.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(
        user="User to fetch predictions for",
        content="Message to inspect predictions for"
    )
    async def get_prediction(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        user: Optional[discord.User] = None,
        content: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command get_prediction called by {interaction.user.name} in {channel.mention} for user {user} and content '{content}'.")

        if not user and not content:
            await interaction.followup.send("You must specify at least one of `user` or `message_id`.", ephemeral=True)
            return
        
        
        message = await utils.get_message(self.db, channel, content)

        if not message:
            await interaction.followup.send(f"No message found with content: `{content}`.", ephemeral=True)
            return

        # Case 1: Both user and message_id provided
        if user and content:
            prediction = self.db.get_prediction(message.id, user.id)
            if not prediction:
                await interaction.followup.send(f"{user.mention} has no prediction for message ID {message.id}.", ephemeral=True)
                return

            match = self.db.get_match_by_id(message_id=prediction.message_id)
            if match:
                await interaction.followup.send(
                    f"{user.mention}'s prediction for {match.home_team} vs {match.away_team}: `{prediction.prediction}`",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(f"Prediction found, but no match info available.", ephemeral=True)

        # Case 2: Only user provided
        elif user:
            predictions = self.db.get_predictions_for_user(user.id)
            if not predictions:
                await interaction.followup.send(f"No predictions found for {user.mention}.", ephemeral=True)
                return

            lines = [f"Predictions for {user.mention}:"]
            for p in predictions:
                match = self.db.get_match_by_id(p.match_id)
                if match:
                    lines.append(f"{match.home_team} vs {match.away_team}: `{p.prediction}`")
            await interaction.followup.send("\n".join(lines), ephemeral=True)

        # Case 3: Only message_id provided
        elif content:
            all_preds = self.db.get_all_predictions_for_match(message.id)
            if not all_preds:
                await interaction.followup.send(f"No predictions found for message ID {message.id}.", ephemeral=True)
                return

            # Count how many of each prediction
            counts = {}
            for p in all_preds:
                counts[p.prediction] = counts.get(p.prediction, 0) + 1

            match = self.db.get_match_by_id(message_id=message.id)  # assumes match_id == message_id
            header = f"Predictions for {match.home_team} vs {match.away_team}:" if match else f"Predictions for message ID {message.id}:"
            lines = [header]
            for pred, count in counts.items():
                lines.append(f"- `{pred}`: {count} vote(s)")

            await interaction.followup.send("\n".join(lines), ephemeral=True)


    @app_commands.command(name='adjust_score', description='Manually adjust a user\'s score and wins.')
    @app_commands.default_permissions(manage_messages=True)
    async def adjust_score(self, interaction: discord.Interaction, user: discord.User, points: int = 0, wins: int = 0):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command adjust_score called by {interaction.user.name} for user {user.name} with points {points} and wins {wins}.")
        self.db.upsert_score(user_id=user.id, points_delta=points, win_delta=wins)
        self.logger.info(f"Adjusted score for {user.mention}: {points} points, {wins} wins.")
        await interaction.followup.send(f"Adjusted {user.mention}'s score by {points} points and {wins} wins.", ephemeral=True)


        

async def setup(bot):
    await bot.add_cog(DatabaseCog(bot))