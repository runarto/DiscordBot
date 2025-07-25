from discord.ext import commands
from db.db_interface import DB
import subprocess

class CogManager(commands.Cog, name="Manager"):
    def __init__(self, bot: commands.bot, db: DB):
        self.bot = bot
        self.db = db

    @commands.command(name="load")
    @commands.is_owner()
    async def load_cog(self, ctx, extension: str):
        """Loads a cog."""
        try:
            await self.bot.load_extension(f'cogs.{extension}')
            await ctx.send(f'✅ Loaded `{extension}` successfully.')
        except Exception as e:
            await ctx.send(f'❌ Failed to load `{extension}`: {e}')

    @commands.command(name="unload")
    @commands.is_owner()
    async def unload_cog(self, ctx, extension: str):
        """Unloads a cog."""
        try:
            await self.bot.unload_extension(f'cogs.{extension}')
            await ctx.send(f'✅ Unloaded `{extension}` successfully.')
        except Exception as e:
            await ctx.send(f'❌ Failed to unload `{extension}`: {e}')

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx, extension: str):
        """Reloads a cog."""
        try:
            await self.bot.reload_extension(f'cogs.{extension}')
            await ctx.send(f'🔄 Reloaded `{extension}` successfully.')
        except Exception as e:
            await ctx.send(f'❌ Failed to reload `{extension}`: {e}')

    @commands.command(name="git_pull")
    @commands.is_owner()
    async def git_pull_reload(self, ctx):
        """Pulls latest code from Git and reloads all cogs."""

        try:
            result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            output = result.stdout or result.stderr
            await ctx.send(f"📥 `git pull` output:\n```\n{output}\n```")
        except Exception as e:
            await ctx.send(f"❌ Git pull failed: {e}")
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
        await ctx.send(msg)


    @commands.command(name="git_push")
    @commands.is_owner()
    async def git_push(self, ctx):
        """Pushes changes to the Git repository."""
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Automated commit from Discord bot"], check=True)
            subprocess.run(["git", "push"], check=True)
            await ctx.send("✅ Changes pushed to git repository.")
        except subprocess.CalledProcessError as e:
            await ctx.send(f"❌ Git command failed: {e}")


# To add this Cog:
async def setup(bot):
    await bot.add_cog(CogManager(bot))
