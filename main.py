
# main.py - Clean main file
import logging
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from misc.setup import setup_logging, setup_bot, setup_scheduler
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
scheduler = setup_scheduler(bot=bot, db=db, channel_id=TIPPEKUPONG_CHANNEL_ID, logger=logger)

# Attach shared instances to bot for cogs to access
bot.logger = logger
bot.scheduler = scheduler
bot.db_path = DB_PATH

from cogs.admin import AdminCog
from cogs.database import DatabaseCog
from cogs.kupong import KupongCog
from cogs.mapping import MappingCog
from cogs.cog_manager import CogManager

async def load_cogs():
    await bot.add_cog(CogManager(bot, db))
    await bot.add_cog(AdminCog(bot, db))
    await bot.add_cog(DatabaseCog(bot, db))
    await bot.add_cog(KupongCog(bot, db))
    await bot.add_cog(MappingCog(bot, db))

@bot.event
async def on_ready():
    discord_handler = DiscordLogHandler(bot, LOG_CHANNEL_ID)
    discord_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(discord_handler)

    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILDS:
            logger.warning(f"Leaving unauthorized guild: {guild.name} ({guild.id})")
            await guild.leave()

    logger.debug(f"Commands in tree: {[cmd.name for cmd in bot.tree.get_commands()]}")
  
    synced = await bot.tree.sync()
    logger.debug(f"Synced {len(synced)} commands to the tree.")

    logger.debug(f"Logged in as {bot.user}")
    scheduler.start()

async def main():
    await load_cogs()
    await bot.start(os.getenv('BOT_TOKEN'))


if __name__ == "__main__":
    asyncio.run(main())