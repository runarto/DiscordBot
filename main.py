import discord
from discord.ext import commands
import pytz 
import misc.utils as utils
from dotenv import load_dotenv
import os
from db.db_interface import DB
from misc.utils import fetch_user_data, map_roles_to_emojis, map_teams_to_emojis    
from commands import kupong, results


load_dotenv()
intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
CHANNEL_ID = 1094933846383923320
GUILD_ID = 1039825091430719559
ALLOWED_GUILDS = [1039825091430719559]
BOT_TOKEN = os.getenv('BOT_TOKEN')
timezone = pytz.timezone('Europe/Oslo')


@bot.event
async def on_ready():
    db = DB("infobase.db")
    print(f"Bot has started and is in {len(bot.guilds)} guild(s)")

    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILDS:
            print(f"Leaving unauthorized guild: {guild.name} ({guild.id})")
            await guild.leave()


    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f'Logged in as {bot.user}')

    # fetch_user_data(bot=bot, db=db) 
    # map_roles_to_emojis(bot=bot, db=db)
    # map_teams_to_emojis(bot=bot, db=db, auth=os.getenv('API_TOKEN'))

@bot.tree.command(name='ukens_kupong', description='Send ukens kupong for de neste dagene.')
@commands.has_permissions(manage_messages=True)
async def SendUkensKupong(interaction: discord.Interaction, days: int, channel: discord.TextChannel):
    """
    Sends the weekly coupon for the next specified number of days to a given channel.
    """
    await interaction.response.defer(ephemeral=True)
    kup = kupong.Kupong(days=days, db=DB("infobase.db"), channel=channel)
    await kup.send_msg()
    await interaction.followup.send(f"Ukens kupong for de neste {days} dagene er sendt til {channel.mention}.", ephemeral=True)


async def SendUkensResultater(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Sends the results of the matches for the week to a specified channel.
    """
    await interaction.response.defer(ephemeral=True)
    res = results.Results(db=DB("infobase.db"), channel=channel)
    await res.send()


# TODO: Schedule task to scrape message reactions and store to predictions table



import json
from db.db_interface import DB

# Load the files
with open("user_scores_Eliteserien.json", "r") as f:
    total_scores = json.load(f)

with open("weekly_winners.json", "r") as f:
    weekly_wins = json.load(f)

# Open DB connection
db = DB("infobase.db")
#db.drop_table("scores")  # Drop the scores table if it exists

for user_tag, total_points in total_scores.items():
    user_id = user_tag.strip("<@>")
    weekly_wins_count = weekly_wins.get(user_id, 0)

    db.upsert_score(user_id=user_id, points_delta=total_points, win_delta=weekly_wins_count)













        







#bot.run(os.getenv('BOT_TOKEN'))




