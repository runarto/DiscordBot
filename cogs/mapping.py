# =============================================================================
# cogs/mapping.py - Role and emoji mapping commands
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import api.discord as discord_api
import misc.utils as utils
from db.db_interface import DB

class MappingCog(commands.Cog, name="Mapping"):
    """Commands for mapping roles to emojis and managing user data"""
    
    def __init__(self, bot: commands.Bot, db: DB):
        self.bot = bot
        self.db = db


    @app_commands.command(name='map_emoji', description='Map roles to emojis one by one.')
    @app_commands.default_permissions(manage_messages=True)
    async def map_emoji(self, interaction: discord.Interaction):

        await interaction.response.defer()
        all_roles = discord_api.get_roles(self.bot)
        db_role_names = {role.role_name for role in self.db.get_team_emojis()}
        
        # Filter out roles that already have emojis mapped
        unmapped_roles = [role for role in all_roles if role.name not in db_role_names]
        
        if not unmapped_roles:
            await interaction.followup.send("All roles already have emojis mapped!")
            return
        
        for role in unmapped_roles:
            await interaction.followup.send(f"**{role.name}**\nProvide an emoji for this role (or type 'pass' to skip):")
            
            def check(message):
                return message.author == interaction.user and message.channel == interaction.channel
            
            try:
                message = await self.bot.wait_for('message', timeout=30.0, check=check)
                
                if message.content.lower() == 'pass':
                    await message.add_reaction('⏭️')
                    continue
                
                emoji = message.content.strip()
                self.db.insert_team_emoji(role.name, emoji)
                await message.add_reaction('✅')
                
            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Timeout - moving to next role")
                continue
        
        await interaction.followup.send("🎉 Emoji mapping complete!")
    

    @app_commands.command(name='fetch_users', description='Populates the users table.')
    @app_commands.default_permissions(manage_messages=True)
    async def map_users(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)
        self.bot.logger.debug("Mapping users to their main emoji...")
        utils.map_users(self.bot, self.db)
        self.bot.logger.info("User fetch complete.")
        await interaction.followup.send("User fetch has been completed.", ephemeral=True)



async def setup(bot):
    await bot.add_cog(MappingCog(bot))