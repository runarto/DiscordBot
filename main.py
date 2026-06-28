
# main.py - Clean main file
import logging
import os
import asyncio
from dotenv import load_dotenv
import discord

from misc.setup import setup_logging, setup_bot, setup_scheduler, setup_predictor
from db.db_interface import DB
from logger.log import DiscordLogHandler

# Global constants
DB_PATH = "infobase.db"
TIPPEKUPONG_CHANNEL_ID = 1094933846383923320
GUILD_ID = 1039825091430719559
ALLOWED_GUILDS = [GUILD_ID]
LOG_CHANNEL_ID = 1376622589488664816

# Create shared instances
db = DB(DB_PATH)
load_dotenv()
logger = setup_logging()
bot = setup_bot()

# Attach shared instances to bot for cogs to access
bot.logger = logger
bot.db_path = DB_PATH
bot.db = db

from cogs.admin import AdminCog
from cogs.database import DatabaseCog
from cogs.kupong import KupongCog
from cogs.mapping import MappingCog
from cogs.cog_manager import CogManager
from cogs.predictor import PredictorCog

async def load_cogs():
    await bot.add_cog(CogManager(bot, db))
    await bot.add_cog(AdminCog(bot, db))
    await bot.add_cog(DatabaseCog(bot, db))
    await bot.add_cog(KupongCog(bot, db))
    await bot.add_cog(MappingCog(bot, db))
    await bot.add_cog(PredictorCog(bot))

@bot.event
async def on_ready():
    logger.debug(f"on_ready fired — logged in as {bot.user}")

    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILDS:
            logger.warning(f"Leaving unauthorized guild: {guild.name} ({guild.id})")
            await guild.leave()

    # Guard: only run first-time setup once, even if on_ready fires again on reconnect
    if getattr(bot, '_initialized', False):
        logger.info("Reconnected to Discord — rescheduling missed jobs.")
        bot.scheduler.reschedule()
        return

    bot._initialized = True

    discord_handler = DiscordLogHandler(bot, LOG_CHANNEL_ID)
    discord_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(discord_handler)

    logger.debug(f"Commands in tree: {[cmd.name for cmd in bot.tree.get_commands()]}")
    guild_obj = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild_obj)
    synced = await bot.tree.sync(guild=guild_obj)
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    logger.debug(f"Synced {len(synced)} commands to the tree.")

    scheduler = await setup_scheduler(bot=bot, db=db, channel_id=TIPPEKUPONG_CHANNEL_ID, logger=logger)
    bot.scheduler = scheduler
    bot.scheduler.start()

    bot.predictor = setup_predictor(logger=logger, db=db)

async def main():
    await load_cogs()
    await bot.start(os.getenv('BOT_TOKEN'))


if __name__ == "__main__":
    asyncio.run(main())
