from discord.ext import commands
from db.db_interface import DB
import subprocess
import os
import sys

class CogManager(commands.Cog, name="Manager"):
    def __init__(self, bot: commands.bot, db: DB):
        self.bot = bot
        self.db = db
        self.logger = bot.logger

    @commands.command(name="load")
    @commands.is_owner()
    async def load_cog(self, extension: str):
        """Loads a cog."""
        self.logger.debug(f"Attempting to load cog: {extension}")
        try:
            await self.bot.load_extension(f'cogs.{extension}')
            self.logger.info(f'✅ Loaded `{extension}` successfully.')
        except Exception as e:
            self.logger.info(f'❌ Failed to load `{extension}`: {e}')

    @commands.command(name="unload")
    @commands.is_owner()
    async def unload_cog(self, extension: str):
        """Unloads a cog."""
        self.logger.debug(f"Attempting to unload cog: {extension}")
        try:
            await self.bot.unload_extension(f'cogs.{extension}')
            self.logger.info(f'✅ Unloaded `{extension}` successfully.')
        except Exception as e:
            self.logger.info(f'❌ Failed to unload `{extension}`: {e}')

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, extension: str):
        """Reloads a cog."""
        self.logger.debug(f"Attempting to reload cog: {extension}")
        try:
            await self.bot.reload_extension(f'cogs.{extension}')
            self.logger.info(f'🔄 Reloaded `{extension}` successfully.')
        except Exception as e:
            self.logger.info(f'❌ Failed to reload `{extension}`: {e}')

    @commands.command(name="git_pull")
    @commands.is_owner()
    async def git_pull_reload(self, ctx):
        """Pulls latest code from Git and reloads all cogs."""
        self.logger.debug("Attempting to pull latest code from Git and reload cogs.")
        try:
            result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            output = result.stdout or result.stderr
            self.logger.info(f"📥 `git pull` output:\n```\n{output}\n```")
        except Exception as e:
            self.logger.info(f"❌ Git pull failed: {e}")
            return
        
        if output.startswith("Already up to date."):
            self.logger.info("No new changes to pull.")
            return

        # Reload cogs
        cogs = ['admin', 'database', 'kupong', 'mapping', 'cog_manager']
        reloaded = []
        failed = []

        for cog in cogs:
            try:
                self.bot.reload_extension(f'cogs.{cog}')
                reloaded.append(cog)
            except Exception as e:
                failed.append((cog, str(e)))

        msg = f"✅ Reloaded cogs: {', '.join(reloaded)}\n"
        if failed:
            msg += f"❌ Failed reloads:\n" + "\n".join([f"`{c}`: {e}" for c, e in failed])
        self.logger.info(msg)


    @commands.command(name="git_push")
    @commands.is_owner()
    async def git_push(self, ctx):
        """Pushes changes to the Git repository."""
        self.logger.debug("Attempting to push changes to Git repository.")
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Automated commit from Discord bot"], check=True)
            subprocess.run(["git", "push"], check=True)
            self.logger.info("Changes pushed to Git repository.")
        except subprocess.CalledProcessError as e:
            self.logger.info(f"❌ Git command failed: {e}")
    
    @commands.command(name="reboot")
    @commands.is_owner()
    async def reboot_bot(self, ctx):
        """Restarts the bot process."""
        self.logger.info("Restarting bot process...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def setup(bot):
    await bot.add_cog(CogManager(bot))
