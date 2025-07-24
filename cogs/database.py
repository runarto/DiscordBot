# =============================================================================
# cogs/database.py - Database management commands
import discord
from discord.ext import commands
from discord import app_commands
from misc.utils import map_users, map_teams_to_emojis

class DatabaseCog(commands.Cog, name="Database"):
    """Database synchronization and management commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='flush_table', description='Flush a table in the database.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.choices(table=[
        app_commands.Choice(name='matches', value='matches'),
        app_commands.Choice(name='predictions', value='predictions'),
        app_commands.Choice(name='users', value='users'),
    ])
    async def flush_table(self, interaction: discord.Interaction, table: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        self.bot.db.flush_table(table.value)
        self.bot.logger.info(f"{table.value.capitalize()} table flushed.")
        await interaction.followup.send(f"**{table.value}** table has been flushed.", ephemeral=True)

    @app_commands.command(name='add_team_emoji', description='Maps users to their main emoji.')
    @app_commands.default_permissions(manage_messages=True)
    async def add_team_emoji(self, interaction: discord.Interaction, role: discord.Role, emoji: str):
        await interaction.response.defer(ephemeral=True)
        self.db.insert_team_emoji(role.name, emoji)
        self.bot.logger.info("Team emoji added for role: {role.name} with emoji: {emoji}")
        await interaction.followup.send("Team emojis have been mapped successfully.", ephemeral=True)

    
    @app_commands.command(name='update_user_emoji', description='Update the emoji for a user.')
    @app_commands.default_permissions(manage_messages=True)
    async def update_user_emoji(self, interaction: discord.Interaction, user: discord.User, emoji: str):
        await interaction.response.defer(ephemeral=True)
        self.bot.db.insert_user(user.id, user.name, user.display_name, emoji)
        self.bot.logger.info(f"Updated emoji for {user.mention} to {emoji}.")
        await interaction.followup.send(f"Emoji for {user.mention} has been updated to {emoji}.", ephemeral=True)
        

async def setup(bot):
    await bot.add_cog(DatabaseCog(bot))