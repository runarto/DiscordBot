from discord.ext import commands
from db.db_interface import DB

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

# To add this Cog:
async def setup(bot):
    await bot.add_cog(CogManager(bot))
