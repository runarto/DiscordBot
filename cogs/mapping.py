# =============================================================================
# cogs/mapping.py - Role and emoji mapping commands
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import api.discord as discord_api
import misc.utils as utils
from db.db_interface import DB
from misc.constants import LEAGUES, DEFAULT_LEAGUE
from misc.checks import is_admin

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
    @is_admin()
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
    @is_admin()
    @app_commands.choices(league=LEAGUE_CHOICES)
    async def map_teams(self, interaction: discord.Interaction, league: str = DEFAULT_LEAGUE):

        await interaction.response.defer()
        league_config = LEAGUES[league]
        league_id = league_config["id"]

        matches = self.db.get_matches_by_league(league_id)
        if not matches:
            await interaction.followup.send(f"No matches found for {league_config['name']}. Send a kupong first.")
            return

        all_team_names = {m.home_team for m in matches} | {m.away_team for m in matches}
        already_mapped = {t.team_name for t in self.db.get_teams_by_league(league_id)}
        unmapped = sorted(all_team_names - already_mapped)

        if not unmapped:
            await interaction.followup.send(f"All teams for {league_config['name']} are already mapped.")
            return

        emojis = discord_api.get_emojis(self.bot)
        await interaction.followup.send(f"Mapping {len(unmapped)} teams for **{league_config['name']}**. Type `stop` at any time to quit.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        for team_name in unmapped:

            # Find best emoji match by name similarity
            best_emoji, best_ratio = None, 0
            for emoji in emojis:
                ratio = utils.check_similarity(emoji.name.lower(), team_name.lower())
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_emoji = f"<:{emoji.name}:{emoji.id}>"

            if best_emoji:
                await interaction.followup.send(f"**{team_name}**\nBest emoji match: {best_emoji}\nType `yes` to confirm, send a different emoji, or `pass`/`stop`:")
            else:
                await interaction.followup.send(f"**{team_name}**\nNo emoji match found. Please send an emoji (or `pass`/`stop`):")

            try:
                emoji_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Timed out — mapping stopped.")
                return

            if emoji_msg.content.lower() == 'stop':
                await interaction.followup.send("Mapping stopped.")
                return
            if emoji_msg.content.lower() == 'pass':
                await emoji_msg.add_reaction('⏭️')
                continue

            team_emoji = best_emoji if emoji_msg.content.lower() == 'yes' else emoji_msg.content.strip()
            self.db.insert_team(team_name, league_id, team_emoji)
            await emoji_msg.add_reaction('✅')
            self.logger.debug(f"Mapped team: {team_name} → {team_emoji}")

        await interaction.followup.send(f"✅ Team mapping complete for **{league_config['name']}**.")


    @app_commands.command(name='fetch_users', description='Populates the users table.')
    @is_admin()
    async def map_users(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)
        self.logger.debug("Mapping users to their main emoji...")
        utils.map_users(self.bot, self.db)
        self.logger.info("User fetch complete.")
        await interaction.followup.send("User fetch has been completed.", ephemeral=True)



async def setup(bot):
    await bot.add_cog(MappingCog(bot))