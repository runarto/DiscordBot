import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

from misc.setup import setup_logging, setup_bot, setup_scheduler
from db.db_interface import DB
from misc.utils import fetch_user_data, map_roles_to_emojis, map_teams_to_emojis
from logger.log import DiscordLogHandler
from commands.kupong import Kupong
from commands.results import Results

# Global constants
DB_PATH = "testbase.db"
CHANNEL_ID = 1094933846383923320
GUILD_ID = 1039825091430719559
ALLOWED_GUILDS = [GUILD_ID]
LOG_CHANNEL_ID = 1376622589488664816
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Load environment
load_dotenv()

# Setup logging
logger = setup_logging()

# Setup bot
bot = setup_bot()

#Setup scheduler

scheduler = setup_scheduler(db=DB(DB_PATH), channel=discord.Object(id=CHANNEL_ID), logger=logger)

# Create shared db instance
db = DB(DB_PATH)


@bot.event
async def on_ready():
    # Attach Discord logging first
    discord_handler = DiscordLogHandler(bot, LOG_CHANNEL_ID)
    discord_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(discord_handler)

    logger.debug(f"Bot started in {len(bot.guilds)} guild(s)")

    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILDS:
            logger.warning(f"Leaving unauthorized guild: {guild.name} ({guild.id})")
            await guild.leave()

    
    #bot.tree.clear_commands(guild=discord.Object(id=GUILD_ID))
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    logger.info(f"Commands synced to guild {GUILD_ID}")
    logger.debug(f"Logged in as {bot.user}")

    

@bot.tree.command(name='sync_db', description='Syncs the database with user data and emojis.')
@commands.has_permissions(manage_messages=True)
async def SyncDatabase(interaction: discord.Interaction):
    """
    Syncs the database with user data and emojis.
    """
    await interaction.response.defer(ephemeral=True)
    db = DB("infobase.db")
    logger.info("Syncing database with user data and emojis...")
    fetch_user_data(bot=bot, db=db)
    map_roles_to_emojis(bot=bot, db=db)
    map_teams_to_emojis(bot=bot, db=db, auth=os.getenv('API_TOKEN'))
    logger.info("Database sync complete.")
    await interaction.followup.send("Database has been synced with user data and emojis.", ephemeral=True)

@bot.tree.command(name='ukens_kupong', description='Send ukens kupong for de neste dagene.')
@commands.has_permissions(manage_messages=True)
async def SendUkensKupong(interaction: discord.Interaction, days: int, channel: discord.TextChannel):
    """
    Sends the weekly coupon for the next specified number of days to a given channel.
    """
    await interaction.response.defer(ephemeral=True)
    kup = Kupong(days=days, db=DB("infobase.db"), channel=channel, logger=logger)
    logger.info(f"Sending ukens kupong for the next {days} days to {channel.mention}.")
    await kup.send_msg()
    scheduler.start()
    logger.info(f"Ukens kupong for the next {days} days sent to {channel.mention}.")
    await interaction.followup.send(f"Ukens kupong for de neste {days} dagene er sendt til {channel.mention}.", ephemeral=True)

@bot.tree.command(name='ukens_resultater', description='Send ukens resultater for de siste kampene.')
@commands.has_permissions(manage_messages=True)
async def SendUkensResultater(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Sends the results of the matches for the week to a specified channel.
    """
    await interaction.response.defer(ephemeral=True)
    res = Results(db=DB("infobase.db"), channel=channel, logger=logger)
    logger.info(f"Sending ukens resultater to {channel.mention}.")
    await res.send()
    db.flush_table("matches")
    logger.info(f"Ukens resultater sent to {channel.mention}.")


@bot.tree.command(name='flush_matches', description='Flushes the matches table in the database.')
@commands.has_permissions(manage_messages=True)
async def FlushMatches(interaction: discord.Interaction):
    """
    Flushes the matches table in the database.
    """
    await interaction.response.defer(ephemeral=True)
    db.flush_table("matches")
    logger.info("Matches table flushed.")
    await interaction.followup.send("Matches table has been flushed.", ephemeral=True)



# TODO: Schedule task to scrape message reactions and store to predictions table

















        







bot.run(os.getenv('BOT_TOKEN'))




