# =============================================================================
# cogs/admin.py - Administrative commands
import discord
from discord.ext import commands
from discord import app_commands
import os
import glob
import shutil
from db.db_interface import DB

class AdminCog(commands.Cog, name="Admin"):
    """Administrative commands for bot management"""
    
    def __init__(self, bot: commands.Bot, db: DB):
        self.bot = bot
        self.db = db
        self.logger = bot.logger

    @app_commands.command(name='send_msg', description='Sends a message to a specific channel.')
    @app_commands.default_permissions(manage_messages=True)
    async def send_message(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command send_message called by {interaction.user.name} in {channel.mention}.")
        try:
            await channel.send(message)
            self.logger.info(f"Message sent to {channel.mention}: {message}")
            await interaction.followup.send(f"Message sent to {channel.mention}.", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Failed to send message to {channel.mention}: {e}")
            await interaction.followup.send(f"Failed to send message to {channel.mention}.", ephemeral=True)


    @app_commands.command(name='restore_db', description='Restores the main database from the newest backup.')
    @app_commands.default_permissions(manage_messages=True)
    async def restore_db(self, interaction: discord.Interaction):
        
        await interaction.response.defer(ephemeral=True)
        self.logger.debug(f"Command restore_db called by {interaction.user.name} in {interaction.channel.mention}.")

        backup_dir = "./backups"
        backups = glob.glob(os.path.join(backup_dir, "backup_*.db"))

        if not backups:
            await interaction.followup.send("❌ No backups found.", ephemeral=True)
            return

        latest_backup = max(backups, key=os.path.getmtime)
        shutil.copyfile(latest_backup, self.db_path)
        self.logger.warning(f"Database restored from backup: {os.path.basename(latest_backup)}")
        await interaction.followup.send(f"✅ Database restored from `{os.path.basename(latest_backup)}`.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))