import logging
import discord
from discord.ext import commands
from misc.schedule import Schedule

import logging

def setup_logging():
    logger = logging.getLogger("discord_bot")
    logger.setLevel(logging.DEBUG)  # Set logger to DEBUG so it captures everything

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # File handler (INFO+)
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (DEBUG+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Show DEBUG in terminal
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def setup_bot():
    intents = discord.Intents.default()
    intents.members = True
    intents.reactions = True
    intents.message_content = True
    intents.guilds = True

    bot = commands.Bot(command_prefix="/", intents=intents)
    return bot


def setup_scheduler(db, channel: discord.TextChannel, logger: logging.Logger):
    """
    Sets up the scheduler for storing predictions.
    """
    return Schedule(db, channel, logger)
