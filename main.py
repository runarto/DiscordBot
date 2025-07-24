import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import glob
import shutil

from misc.setup import setup_logging, setup_bot, setup_scheduler
from db.db_interface import DB
from misc.utils import fetch_user_data, map_roles_to_emojis, map_teams_to_emojis
from logger.log import DiscordLogHandler
from commands.kupong import Kupong
from commands.results import Results
from misc.utils import store_predictions, backup_database



# Global constants
DB_PATH = "testbase.db"
CHANNEL_ID = 1094933846383923320
GUILD_ID = 1039825091430719559
ALLOWED_GUILDS = [GUILD_ID]
LOG_CHANNEL_ID = 1376622589488664816
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Create shared db instance
db = DB(DB_PATH)

# Load environment
load_dotenv()

# Setup logging
logger = setup_logging()

# Setup bot
bot = setup_bot()

#Setup scheduler
scheduler = setup_scheduler(db=db, channel=discord.Object(id=CHANNEL_ID), logger=logger)


@bot.event
async def on_ready():
    # Attach Discord logging first
    discord_handler = DiscordLogHandler(bot, LOG_CHANNEL_ID)
    discord_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(discord_handler)

    logger.debug(f"Bot started in {len(bot.guilds)} guild(s)")
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))

    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILDS:
            logger.warning(f"Leaving unauthorized guild: {guild.name} ({guild.id})")
            await guild.leave()

    
    #bot.tree.clear_commands(guild=discord.Object(id=GUILD_ID))
    logger.debug(f"Commands synced to guild {GUILD_ID}")
    logger.debug(f"Logged in as {bot.user}")

    scheduler.start()

@bot.tree.command(name='sync_db', description='Syncs the database with user data and emojis.')
@commands.has_permissions(manage_messages=True)
async def SyncDatabase(interaction: discord.Interaction, sync_teams: bool = False):
    """
    Syncs the database with user data and emojis.
    """
    await interaction.response.defer(ephemeral=True)
    await logger.info("Syncing database with user data and emojis...")
    await fetch_user_data(bot=bot, db=db)
    await map_roles_to_emojis(bot=bot, db=db)
    if sync_teams:
        await map_teams_to_emojis(bot=bot, db=db, auth=os.getenv('API_TOKEN'))
    await logger.info("Database sync complete.")
    await interaction.followup.send("Database has been synced with user data and emojis.", ephemeral=True)

@bot.tree.command(name='ukens_kupong', description='Send ukens kupong for de neste dagene.')
@commands.has_permissions(manage_messages=True)
async def SendUkensKupong(interaction: discord.Interaction, days: int, channel: discord.TextChannel):
    """
    Sends the weekly coupon for the next specified number of days to a given channel.
    """
    await interaction.response.defer(ephemeral=True)
    kup = Kupong(days=days, db=DB("infobase.db"), channel=channel, logger=logger)
    await logger.info(f"Sending ukens kupong for the next {days} days to {channel.mention}.")
    await kup.send_msg()
    await scheduler.start()
    await logger.info(f"Ukens kupong for the next {days} days sent to {channel.mention}.")
    await interaction.followup.send(f"Ukens kupong for de neste {days} dagene er sendt til {channel.mention}.", ephemeral=True)

@bot.tree.command(name='ukens_resultater', description='Send ukens resultater for de siste kampene.')
@commands.has_permissions(manage_messages=True)
async def SendUkensResultater(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Sends the results of the matches for the week to a specified channel.
    """
    await interaction.response.defer(ephemeral=True)
    backup_database(DB_PATH)  # Backup the database before sending results
    res = Results(db=DB("infobase.db"), channel=channel, logger=logger)
    await logger.info(f"Sending ukens resultater to {channel.mention}.")
    await res.send()
    await db.flush_table("matches")
    await logger.info(f"Ukens resultater sent to {channel.mention}.")
    await interaction.followup.send(f"Ukens resultater har blitt sendt til {channel.mention}.", ephemeral=True)

@bot.tree.command(name='flush_table', description='Flush a table in the database.')
@commands.has_permissions(manage_messages=True)
@app_commands.describe(
    table='Which table to flush?'
)
@app_commands.choices(table=[
    app_commands.Choice(name='matches', value='matches'),
    app_commands.Choice(name='predictions', value='predictions'),
])
async def FlushTable(interaction: discord.Interaction, table: app_commands.Choice[str]):
    """
    Flushes the selected table in the database.
    """
    await interaction.response.defer(ephemeral=True)
    db.flush_table(table.value)
    logger.info(f"{table.value.capitalize()} table flushed.")
    await interaction.followup.send(f"**{table.value}** table has been flushed.", ephemeral=True)


@bot.tree.command(name='leaderboard', description='Send the total leaderboard.')
@commands.has_permissions(manage_messages=True)
async def SendLeaderboard(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Sends the total leaderboard to a specified channel.
    """
    await interaction.response.defer(ephemeral=True)
    res = Results(db=db, channel=channel, logger=logger)
    await logger.info(f"Sending leaderboard to {channel.mention}.")
    await res.send_leaderboard()
    await logger.info(f"Leaderboard sent to {channel.mention}.")
    await interaction.followup.send(f"Leaderboard has been sent to {channel.mention}.", ephemeral=True)

@bot.tree.command(name='store_predictions', description='Store predictions for a specific match.')
@commands.has_permissions(manage_messages=True)
async def StorePredictions(interaction: discord.Interaction, message_id: int):
    """
    Stores predictions for a specific match based on the message ID.
    """
    await interaction.response.defer(ephemeral=True)
    try:
        message = await interaction.channel.fetch_message(message_id)
        await backup_database(DB_PATH)
        await store_predictions(message, logger, db)
        await logger.debug(f"Stored predictions for message {message_id}.")
        await interaction.followup.send(f"Predictions for message {message_id} have been stored.", ephemeral=True)
    except Exception as e:
        await logger.debug(f"Failed to store predictions for message {message_id}: {e}")
        await interaction.followup.send(f"Failed to store predictions for message {message_id}.", ephemeral=True)

@bot.tree.command(name='delete_messages', description='Delete the match messages.')
@commands.has_permissions(manage_messages=True)
async def DeleteMatchMessages(interaction: discord.Interaction):
    """
    Deletes all match messages in the channel.
    """
    await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    info = db.get_all_matches()
    message_ids = [match.message_id for match in info]

    for msg_id in message_ids:
        message = await channel.fetch_message(msg_id)
        await message.delete()
    
    await logger.info(f"All match messages deleted in {channel.mention}.")
    await interaction.followup.send(f"All match messages have been deleted in {channel.mention}.", ephemeral=True)

@bot.tree.command(name='adjust_score', description='Manually adjust a user\'s score and wins.')
@commands.has_permissions(manage_messages=True)
async def AdjustScore(interaction: discord.Interaction, user: discord.User, points: int = 0, wins: int = 0):
    await interaction.response.defer(ephemeral=True)
    db.upsert_score(user_id=user.id, points_delta=points, win_delta=wins)
    await interaction.followup.send(f"Adjusted {user.mention}'s score by {points} points and {wins} wins.", ephemeral=True)

@bot.tree.command(name='restore_db', description='Restores the main database from the newest backup.')
@commands.has_permissions(manage_messages=True)
async def RestoreDB(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    backup_dir = "./backups"
    backups = glob.glob(os.path.join(backup_dir, "backup_*.db"))

    if not backups:
        await interaction.followup.send("❌ No backups found.", ephemeral=True)
        return

    # Sort backups by last modified time (newest first)
    latest_backup = max(backups, key=os.path.getmtime)

    shutil.copyfile(latest_backup, DB_PATH)
    logger.warning(f"Database restored from backup: {os.path.basename(latest_backup)}")
    await interaction.followup.send(f"✅ Database restored from `{os.path.basename(latest_backup)}`.", ephemeral=True)


bot.run(os.getenv('BOT_TOKEN'))




