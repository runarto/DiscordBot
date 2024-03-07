import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import perms
import pytz 
import logic
import file_functions
import leaderboard
import datetime
from functools import partial
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime
import traceback
import asyncio


scheduler = AsyncIOScheduler()
intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
channel_id = perms.CHANNEL_ID

timezone = pytz.timezone('Europe/Oslo')


@bot.event
async def on_ready():
    print(f"Bot has started and is in {len(bot.guilds)} guild(s)")
    
    # guild = await bot.fetch_guild(perms.guild_id)
    # for role in guild.roles:
    #     print(f"{role.name}, {role.position}\n")


    scheduler.start()
    await bot.tree.sync()  # Synchronizing slash commands with Discord
    print(f'Logged in as {bot.user}')

    # Debugging: List all commands in the command tree
    print("Registered Commands:")
    for command in bot.tree.get_commands():
        print(f"- {command.name} (Type: {'Slash Command' if isinstance(command, discord.app_commands.Command) else 'Text Command'})")
    
    await logic.map_emojis_to_teams(bot, logic.teams)
    print("Emojis fetched")





@bot.event
async def on_reaction_add(reaction, user):
# Ignore the bot's own reactions

    if user == bot.user:
        return

    else:
        if reaction.message.channel.id == channel_id:
            message_id = reaction.message.id
                # Check if the user already reacted with a different emoji
            if (await user_already_reacted(reaction, user)):
                return
            else:
                await file_functions.save_reaction_data(str(reaction.emoji), user.mention, user.display_name, str(message_id))
                print(f"Reaction added by {user.name}: {reaction.emoji} from message {reaction.message.content}")
        else:
            return
        

@bot.event
async def on_reaction_remove(reaction, user): # Remove reaction data when a user removes their reaction (this function needs to be tested more thoroughly)
    try:
        if user == bot.user:
            return
        if (reaction.message.author == bot.user) and (reaction.message.channel.id == channel_id):
            await file_functions.remove_reaction_data(str(reaction.emoji), user.id, user.display_name, str(reaction.message.id))
            print(f"Reaction removed by {user.name}: {reaction.emoji} from message {reaction.message.content}")
    except Exception as e:
        print(f"Error in on_reaction_remove: {e}")


async def user_already_reacted(reaction, user):
    for reactions in reaction.message.reactions:
        if reactions.emoji != reaction.emoji:
            async for users in reactions.users():
                if users == user:
                    # Remove the previous reaction data
                    await file_functions.remove_reaction_data(str(reactions.emoji), user.mention, user.display_name, str(reaction.message.id))
                    # Save the new reaction data
                    await file_functions.save_reaction_data(str(reaction.emoji), user.mention, user.display_name, str(reaction.message.id))
                    # Remove the user's previous reaction
                    await reactions.remove(user)
                    return True
    return False  # Return False if no previous reaction was found





@bot.tree.command(name='sendmsg', description='Sender melding til en kanal av ditt valg')
@commands.has_permissions(manage_messages=True)  # Ensure only authorized users use this command
async def send_message(interaction: discord.Interaction, channel: discord.TextChannel, *, message: str):
    try:
        await channel.send(message)
        await interaction.response.send_message(f"Melding sent til {channel.name}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Jeg har ikke tilgang til å sende melding i denne kanalen.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)



@bot.tree.command(name='ukens_kupong', description='Send ukens kupong for de neste dagene')
@commands.has_permissions(manage_messages=True)
async def send_ukens_kupong(interaction: discord.Interaction, days: int, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    emoji_data = file_functions.read_file(logic.team_emojis_file)

    try:
        await channel.send("Ukens kupong:")

        fixtures = logic.get_matches(days)  # Fetch matches for the next x days
        data = []

        for fixture in fixtures:

            home_team = fixture['home_team']
            print(home_team)
            away_team = fixture['away_team']
            print(away_team)



            home_team_emoji = emoji_data.get(home_team)
            if home_team_emoji is None:
                home_team_emoji = '🏠'  # Replace 'Default Emoji' with your default emoji

            away_team_emoji = emoji_data.get(away_team)
            if away_team_emoji is None:
                away_team_emoji = '✈️'  # Replace 'Default Emoji' with your default emoji

            if fixture['home_team'] in logic.teams_norske_navn:
                home_team = logic.teams_norske_navn[fixture['home_team']]
                print(home_team)

            if fixture['away_team'] in logic.teams_norske_navn:
                away_team = logic.teams_norske_navn[fixture['away_team']]
                print(away_team)

            if home_team_emoji == '🏠' or away_team_emoji == '✈️': 
                message_content = f"{home_team} vs {away_team}"
            else:
                message_content = f"{home_team_emoji} {home_team} vs {away_team} {away_team_emoji}"

            message = await channel.send(message_content)

            data.append((str(message.id), fixture['match_id']))  # Store message ID and match ID

            # Adding reactions to the message

            for reaction in (home_team_emoji, '🇺', away_team_emoji):
                await message.add_reaction(reaction)

        # Writing tracked messages to file
        file_functions.write_file(logic.tracked_messages, data)

        date_start, hour_start, minute_start, messages_id = get_day_hour_minute(days)
        anyGames = await update_jobs(date_start, hour_start, minute_start, messages_id, channel)
        if anyGames == False:
            await interaction.followup.send(f"Ingen kamper de neste {days} dagene", ephemeral=True)
            return
        await interaction.followup.send("Kupong sendt!", ephemeral=True)
        return

    except discord.errors.Forbidden:
        await interaction.followup.send(f"Missing permissions to send message in channel {channel.name}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}. Ta kontakt med Runar (trunar)", ephemeral=True)
        traceback.print_exc()





@bot.tree.command(name="total_ledertavle", description="Vis totale resultater")
async def total_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if interaction.guild_id != perms.guild_id:
        await interaction.followup.send("Denne kommandoen kan kun brukes i en spesifikk server", ephemeral=True)
        return

    # Sort user scores by points (descending order)
    scores = file_functions.read_file(logic.user_scores)
    guild = interaction.guild

    if isinstance(scores, dict):
        leaderboard_message = leaderboard.total_leaderboard_message(scores, guild)
    else:
        await interaction.followup.send("Det oppsto en feil med å hente poengene.", ephemeral=True)
        return
    # Send the leaderboard message to the Discord channel
    if leaderboard_message == "Tippekupongen 2024:\n":
        await interaction.followup.send("Vær litt tålmodig da, det ekke registrert poeng enda.")
    else:
        await interaction.followup.send(leaderboard_message, ephemeral=True)




@bot.tree.command(name = "ukens_resultater", description="Vis resultatene fra forrige uke, og totale resultater. Kall denne FØR ukens kupong")
@commands.has_permissions(manage_messages=True)
async def send_leaderboard_message(interaction: discord.Interaction):

    await interaction.response.defer() 

    channel = await bot.fetch_channel(channel_id)
    guild = await bot.fetch_guild(perms.guild_id)

    try:
        message = await leaderboard.format_leaderboard_message(guild)

        if message and message.strip():
            await interaction.followup.send(message)
            #await interaction.followup.send("Melding sent, og filer tømt. Nå kan du sende ukens kupong.", ephemeral=True)
            #file_functions.write_file(logic.tracked_messages, []) #Tømmer meldingslisten etter at vi skriver ut ukens resulater.
            #file_functions.write_file(logic.predictions_file, {})
            #file_functions.write_file(logic.output_predictions_file, {}) #Tømmer fila. 

        else:
            await interaction.followup.send("Det har ikke vært noen kamper de siste dagene, eller så er det ikke data å hente ut. Prøv igjen senere.", ephemeral=True)
            await interaction.followup.send("Task completed!", ephemeral=True)

    except discord.errors.Forbidden:
        await interaction.followup.send("Du kanke bruke denne kommandoen tjommi.", ephemeral=True)
        await interaction.followup.send("Task completed!", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}. Ta kontakt med Runar (trunar)", ephemeral=True)
        traceback.print_exc()


        


@bot.tree.command(name="lagre_tips_manuelt", description="Kopier meldingen for kampen sine reaksjoner du vil lagre")
@commands.has_permissions(manage_messages=True)
async def find_message_by_content(interaction: discord.Interaction, content: str):
    channel = await bot.fetch_channel(channel_id)
    await interaction.response.defer(ephemeral=True)
    message_data = file_functions.read_file(logic.tracked_messages)  # List of (message_id, match_id)
    found = False

    for message_id, _ in message_data:
        try:
            # Fetch the channel by ID (assuming you know which channel to look in)

            # Fetch the message by ID from the channel
            message = await channel.fetch_message(message_id)

            if message.content == content:
                # Message found
                print(message.content)
                await leaderboard.compare_and_update_reaction_for_message(message_id, channel, bot)
                await interaction.followup.send("Reaksjonene er ferdig lagret", ephemeral=True)
                found = True
                break
        except discord.NotFound:
            await interaction.followup.send("Fant ikke den aktuelle kampen", ephemeral=True)
            continue  # If message not found, continue to the next one
        except Exception as e:
            # Handle other potential errors
            await interaction.followup.send(f"An error occurred: {e}. Ta kontakt med Runar (trunar)", ephemeral=True)
            traceback.print_exc()
            continue

    if not found:
        await interaction.followup.send("Fant ikke den aktuelle kampen", ephemeral=True)

@bot.tree.command(name="se_scheduled_events", description="Se når kupongen for en kamp blir lagret")
@commands.has_permissions(manage_messages=True)
async def print_scheduled_event(interaction: discord.Interaction):
    matches = file_functions.read_file(logic.tracked_messages)
    message_ids = {str(message_id) for message_id, _ in matches}
    channel = await bot.fetch_channel(channel_id)
    await interaction.response.defer(ephemeral=True)
    for job in scheduler.get_jobs():
        if job.id in message_ids:
            try:
                match_message = await channel.fetch_message(job.id)
                match_content = match_message.content  # Get the content of the message
                await interaction.followup.send(f"{match_content} sin kupong vil bli hentet ut {job.next_run_time}", ephemeral=True)
            except discord.NotFound:
                await interaction.followup.send(f"Message with ID {job.id} not found in channel.", ephemeral=True)
                continue
            except Exception as e:
                await interaction.followup.send(f"An error occurred: {e}. Ta kontakt med Runar (trunar)", ephemeral=True)
                traceback.print_exc()
                continue




@bot.tree.command(name='clear_cache', description='Tømmer json-filer')
@commands.has_permissions(manage_messages=True)
async def clear_cache(interaction: discord.Integration):
    await interaction.response.defer(ephemeral=True)
    file_functions.write_file(logic.predictions_file, {})
    file_functions.write_file(logic.output_predictions_file, {})
    file_functions.write_file(logic.tracked_messages, [])
    await interaction.followup.send("Cache tømt", ephemeral=True)


def get_day_hour_minute(days):

    day_of_week = []
    hour = []
    minute = []
    data = logic.get_matches(days)
    message_id_and_match_id = file_functions.read_file(logic.tracked_messages)
    message_ids = [message_id for message_id, _ in message_id_and_match_id]

# Extract the message IDs as a list


    for date in data:
     # Parse the date string into a datetime object
        date_time = datetime.fromisoformat(date['date'])
        # Get the day of the week
        day_of_week_add = date_time.strftime('%A')[:3].lower()
        day_of_week.append(day_of_week_add)
        # Get the hour and minute
        hour_add = int(date_time.strftime('%H'))
        hour.append(str(hour_add))

        minute_add = int(date_time.strftime('%M')) 
        minute.append(str(minute_add))

    return day_of_week, hour, minute, message_ids


async def update_jobs(date_start, hour_start, minute_start, message_ids, channel):

    # Remove existing jobs
    if scheduler.get_jobs():
        scheduler.remove_all_jobs()
        print("Old jobs removed")

    if not date_start:  # Check if there are no new jobs to schedule
        print("No new jobs to schedule.")
        return False

    job_details_list = []  # List to hold details of each job
    # Schedule new jobs
    for date, hour, minute, message_id in zip(date_start, hour_start, minute_start, message_ids):
        scheduler.add_job(
            leaderboard.compare_and_update_reaction_for_message, 
            'cron', 
            day_of_week=date, 
            hour=hour, 
            minute=minute, 
            timezone=timezone, 
            args=[message_id, channel, bot], 
            id=str(message_id)
        )

        job_details = f"Job ID: {message_id}, Scheduled Time: {date} at {hour}:{minute}, Function: {leaderboard.compare_and_update_reaction_for_message.__name__}"
        job_details_list.append(job_details)

    print("Jobs added.")
    for details in job_details_list:
        print(details)

    
    return True

bot.run(perms.TOKEN)




