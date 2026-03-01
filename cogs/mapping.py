# =============================================================================
# cogs/mapping.py - Role and emoji mapping commands
import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import api.discord as discord_api
import api.rapid_sports as sports_api
import misc.utils as utils
from db.db_interface import DB
from misc.constants import LEAGUES, DEFAULT_LEAGUE

LEAGUE_CHOICES = [
    app_commands.Choice(name=config["name"], value=key)
    for key, config in LEAGUES.items()
]

class MappingCog(commands.Cog, name="Mapping"):
    """Commands for mapping roles to emojis and managing user data"""
    
    def __init__(self, bot: commands.Bot, db: DB):
        self.bot = bot
        self.db = db
        self.logger = bot.logger


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
    

    @app_commands.command(name='map_teams', description='Map teams to Norwegian names and emojis for a league.')
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.choices(league=LEAGUE_CHOICES)
    async def map_teams(self, interaction: discord.Interaction, league: str = DEFAULT_LEAGUE):

        await interaction.response.defer()
        league_config = LEAGUES[league]
        league_id = league_config["id"]
        season = league_config["season"]

        teams = sports_api.get_teams(os.getenv("API_TOKEN"), league_id, season)['response']
        emojis = discord_api.get_emojis(self.bot)
        already_mapped = {t.team_name_api for t in self.db.get_teams_by_league(league_id)}
        unmapped = [t for t in teams if t['team']['name'] not in already_mapped]

        if not unmapped:
            await interaction.followup.send(f"All teams for {league_config['name']} are already mapped.")
            return

        await interaction.followup.send(f"Mapping {len(unmapped)} teams for **{league_config['name']}**. Type `stop` at any time to quit.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        for team in unmapped:
            team_name_api = team['team']['name']

            # Step 1: ask for Norwegian name
            await interaction.followup.send(f"**{team_name_api}**\nEnter Norwegian name (or `pass` to skip, `stop` to quit):")
            try:
                name_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Timed out — mapping stopped.")
                return

            if name_msg.content.lower() == 'stop':
                await interaction.followup.send("Mapping stopped.")
                return
            if name_msg.content.lower() == 'pass':
                await name_msg.add_reaction('⏭️')
                continue

            team_name_norsk = name_msg.content.strip()

            # Step 2: find best emoji match by name similarity
            best_emoji, best_ratio = None, 0
            for emoji in emojis:
                ratio = utils.check_similarity(emoji.name.lower(), team_name_norsk.lower())
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_emoji = f"<:{emoji.name}:{emoji.id}>"

            if best_emoji:
                await interaction.followup.send(f"Best emoji match: {best_emoji}\nType `yes` to confirm or send a different emoji:")
            else:
                await interaction.followup.send("No emoji match found. Please send an emoji:")

            try:
                emoji_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Timed out — mapping stopped.")
                return

            if emoji_msg.content.lower() == 'stop':
                await interaction.followup.send("Mapping stopped.")
                return

            team_emoji = best_emoji if emoji_msg.content.lower() == 'yes' else emoji_msg.content.strip()
            self.db.insert_team(team_name_api, league_id, team_name_norsk, team_emoji)
            await emoji_msg.add_reaction('✅')
            self.logger.debug(f"Mapped team: {team_name_api} → {team_name_norsk} {team_emoji}")

        await interaction.followup.send(f"✅ Team mapping complete for **{league_config['name']}**.")


    @app_commands.command(name='fetch_users', description='Populates the users table.')
    @app_commands.default_permissions(manage_messages=True)
    async def map_users(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug("Mapping users to their main emoji...")
        utils.map_users(self.bot, self.db)
        self.logger.info("User fetch complete.")
        await interaction.followup.send("User fetch has been completed.", ephemeral=True)



async def setup(bot):
    await bot.add_cog(MappingCog(bot))