from discord.ext import commands
from db.db_interface import DB
from misc.constants import ADMIN_USER_IDS
import subprocess
import os
import sys

class CogManager(commands.Cog, name="Manager"):
    def __init__(self, bot: commands.Bot, db: DB):
        self.bot = bot
        self.db = db
        self.logger = bot.logger

    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.send("pong")

    @commands.command(name="load")
    @commands.check(lambda ctx: ctx.author.id in ADMIN_USER_IDS)
    async def load_cog(self, ctx, extension: str):
        """Loads a cog."""
        try:
            await self.bot.load_extension(f'cogs.{extension}')
            await ctx.send(f'Loaded {extension}.')
        except Exception as e:
            await ctx.send(f'Failed to load {extension}: {e}')

    @commands.command(name="unload")
    @commands.check(lambda ctx: ctx.author.id in ADMIN_USER_IDS)
    async def unload_cog(self, ctx, extension: str):
        """Unloads a cog."""
        try:
            await self.bot.unload_extension(f'cogs.{extension}')
            await ctx.send(f'Unloaded {extension}.')
        except Exception as e:
            await ctx.send(f'Failed to unload {extension}: {e}')

    @commands.command(name="reload")
    @commands.check(lambda ctx: ctx.author.id in ADMIN_USER_IDS)
    async def reload_cog(self, ctx, extension: str):
        """Reloads a cog."""
        try:
            await self.bot.reload_extension(f'cogs.{extension}')
            await ctx.send(f'Reloaded {extension}.')
        except Exception as e:
            await ctx.send(f'Failed to reload {extension}: {e}')

    @commands.command(name="git_pull")
    @commands.check(lambda ctx: ctx.author.id in ADMIN_USER_IDS)
    async def git_pull_reload(self, ctx):
        """Pulls latest code from Git and reloads all cogs."""
        try:
            result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            output = result.stdout or result.stderr
            await ctx.send(f"git pull:\n```\n{output}\n```")
        except Exception as e:
            await ctx.send(f"Git pull failed: {e}")
            return

        if "Already up to date." in output:
            return

        cogs = ['admin', 'database', 'kupong', 'mapping', 'cog_manager']
        reloaded = []
        failed = []

        for cog in cogs:
            try:
                await self.bot.reload_extension(f'cogs.{cog}')
                reloaded.append(cog)
            except Exception as e:
                failed.append((cog, str(e)))

        msg = f"Reloaded: {', '.join(reloaded)}"
        if failed:
            msg += "\nFailed:\n" + "\n".join([f"{c}: {e}" for c, e in failed])
        await ctx.send(msg)

    @commands.command(name="git_push")
    @commands.check(lambda ctx: ctx.author.id in ADMIN_USER_IDS)
    async def git_push(self, ctx):
        """Pushes changes to the Git repository."""
        try:
            subprocess.run(["git", "add", "."], check=True)
            commit = subprocess.run(
                ["git", "commit", "-m", "Automated commit from Discord bot"],
                capture_output=True, text=True
            )
            if commit.returncode != 0:
                await ctx.send("Nothing to commit.")
                return
            subprocess.run(["git", "push"], check=True)
            await ctx.send("Changes pushed to Git repository.")
        except subprocess.CalledProcessError as e:
            await ctx.send(f"Git command failed: {e}")

    @commands.command(name="reboot")
    @commands.check(lambda ctx: ctx.author.id in ADMIN_USER_IDS)
    async def reboot_bot(self, ctx):
        """Restarts the bot process."""
        await ctx.send("Rebooting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to use this command.")
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            await ctx.send(f"Error: {error}")
            self.logger.error(f"Command error: {error}")

async def setup(bot):
    await bot.add_cog(CogManager(bot, bot.db))
