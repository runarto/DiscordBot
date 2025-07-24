
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
DB_PATH = "testbase.db"
TIPPEKUPONG_CHANNEL_ID = 1094933846383923320
GUILD_ID = 1039825091430719559
ALLOWED_GUILDS = [GUILD_ID]
LOG_CHANNEL_ID = 1376622589488664816

# Create shared instances
db = DB(DB_PATH)
load_dotenv()
logger = setup_logging()
bot = setup_bot()
scheduler = setup_scheduler(db=db, channel=discord.Object(id=TIPPEKUPONG_CHANNEL_ID), logger=logger)

# Attach shared instances to bot for cogs to access
bot.db = db
bot.logger = logger
bot.scheduler = scheduler
bot.db_path = DB_PATH

async def load_cogs():
    """Load all cogs"""
    cogs = [
        'cogs.manager'
        'cogs.admin',
        'cogs.database', 
        'cogs.kupong',
        'cogs.mapping'
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded: {cog}")
        except Exception as e:
            logger.error(f"Failed to load {cog}: {e}")

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
    
    bot.tree.clear_commands(guild=discord.Object(id=GUILD_ID))
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    logger.debug(f"Synced {len(synced)} commands to the tree.")

    logger.debug(f"Logged in as {bot.user}")
    scheduler.start()

async def main():
    await load_cogs()
    await bot.start(os.getenv('BOT_TOKEN'))

match_messages = [
    [
        "1396970978310881321",
        1342301
    ],
    [
        "1396970988557832416",
        1342303
    ],
    [
        "1396970998540275864",
        1342302
    ],
    [
        "1396971009588072649",
        1342305
    ],
    [
        "1396971018681319768",
        1342299
    ],
    [
        "1396971028772818985",
        1342304
    ],
    [
        "1396971037240983595",
        1342300
    ]
]

from api.rapid_sports import get_fixture

auth = os.getenv('API_TOKEN')

for entry in match_messages:
    message_id, match_id = entry
    fixture = get_fixture(auth, match_id)['response'][0]
    db.insert_match(match_id, message_id, fixture['teams']['home']['name'], fixture['teams']['away']['name'], fixture['fixture']['date'])


if __name__ == "__main__":
    asyncio.run(main())