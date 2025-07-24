import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz 
import misc.utils as utils
import leaderboard
import traceback
from dotenv import load_dotenv
import os
from db.db_interface import DB
import api.rapid_sports as sports_api
from misc.utils import fetch_user_data, map_roles_to_emojis, map_teams_to_emojis    
from commands import kupong, results


load_dotenv()
scheduler = AsyncIOScheduler()
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

timezone = pytz.timezone('Europe/Oslo')

@bot.event
async def on_ready():
    db = DB("infobase.db")
    print(f"Bot has started and is in {len(bot.guilds)} guild(s)")

    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILDS:
            print(f"Leaving unauthorized guild: {guild.name} ({guild.id})")
            await guild.leave()


    scheduler.start()
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

    fetch_user_data(bot=bot, db=db) 
    map_roles_to_emojis(bot=bot, db=db)
    map_teams_to_emojis(bot=bot, db=db, auth=os.getenv('API_TOKEN'))

@bot.tree.command(name='ukens_kupong', description='Send ukens kupong for de neste dagene.')
@commands.has_permissions(manage_messages=True)
async def SendUkensKupong(interaction: discord.Interaction, 
                          days: int, 
                          channel: discord.TextChannel):
    

    await interaction.response.defer(ephemeral=True)
    kupong = kupong.Kupong(days=days, db=DB("infobase.db"), channel=channel)
    await kupong.send()
    await interaction.followup.send(f"Ukens kupong for de neste {days} dagene er sendt til {channel.mention}.", ephemeral=True)


async def SendUkensResultater(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    results = results.Results(db=DB("infobase.db"), channel=channel)
    await results.send()












@bot.tree.command(name="total_ledertavle", description="Vis totale resultater")
async def TotalLeaderboard(interaction: discord.Interaction):
    if utils.check_if_valid_server(interaction.guild_id):
        await interaction.response.defer(ephemeral=True)

        if interaction.guild_id != perms.guild_id:
            await interaction.followup.send("Denne kommandoen kan kun brukes i en spesifikk server", ephemeral=True)
            return

        # Sort user scores by points (descending order)
        scores = file_functions.read_file(utils.user_scores)
        guild = interaction.guild

        if isinstance(scores, dict):
            leaderboard_message = await leaderboard.total_leaderboard_message(scores, guild)
        else:
            await interaction.followup.send("Det oppsto en feil med å hente poengene.", ephemeral=True)
            return
        # Send the leaderboard message to the Discord channel
        if leaderboard_message == "Tippekupongen 2024:\n":
            await interaction.followup.send("Vær litt tålmodig da, det ekke registrert poeng enda.")
        else:
            messages = utils.split_message(leaderboard_message)
            for m in messages:
                await interaction.followup.send(m, ephemeral=True)
    else:
        await interaction.response.send_message("Denne kommandoen kan kun brukes i en spesifikk server.", ephemeral=True)




@bot.tree.command(name="ukens_resultater", description="Vis resultatene fra forrige uke, og totale resultater. Kall denne FØR ukens kupong")
@commands.has_permissions(manage_messages=True)
async def SendResults(interaction: discord.Interaction):
    if utils.check_if_valid_server(interaction.guild_id):
        await interaction.response.defer()

        try:
            guild = await bot.fetch_guild(perms.guild_id)
            message = await leaderboard.format_leaderboard_message(guild)
            print(message)

            if message and message.strip():
                messages = utils.split_message(message)
                for m in messages:
                    await interaction.followup.send(m)
            else:
                await interaction.followup.send("Det har ikke vært noen kamper de siste dagene, eller så er det ikke data å hente ut. Prøv igjen senere.", ephemeral=True)
                # Send "Task completed!" message after other responses
        except discord.errors.Forbidden:
            await interaction.followup.send("Du kanke bruke denne kommandoen tjommi.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}. Ta kontakt med Runar (trunar)", ephemeral=True)
            traceback.print_exc()

        # Send "Task completed!" message after all other responses
        await interaction.followup.send("Task completed!", ephemeral=True)
    else:
        await interaction.response.send_message("Denne kommandoen kan kun brukes i en spesifikk server.", ephemeral=True)



        


@bot.tree.command(name="lagre_tips_manuelt", description="Kopier meldingen for kampen sine reaksjoner du vil lagre")
@commands.has_permissions(manage_messages=True)
async def FindMessageByContent(interaction: discord.Interaction, content: str):
    if utils.check_if_valid_server(interaction.guild_id):
        print(f"Searching for message with content: {content}")
        channel = await bot.fetch_channel(channel_id)
        await interaction.response.defer(ephemeral=True)
        message_data = file_functions.read_file(utils.tracked_messages)  # List of (message_id, match_id)
        found = False

        for message_id, _ in message_data:
            message = await channel.fetch_message(int(message_id))
            print(f"Checking message: {message.content}")
            if content in message.content:
                await interaction.followup.send(f"Message found: {message.jump_url}", ephemeral=True)
                await leaderboard.store_predictions(message_id, channel, bot)
                found = True
                break
    else:
        await interaction.response.send_message("Denne kommandoen kan kun brukes i en spesifikk server.", ephemeral=True)

@bot.tree.command(name="se_scheduled_events", description="Se når kupongen for en kamp blir lagret")
@commands.has_permissions(manage_messages=True)
async def print_scheduled_event(interaction: discord.Interaction):
    jobs = file_functions.read_file(utils.scheduled_jobs)
    message_ids = [job['message_id'] for job in jobs]
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
async def ClearCache(interaction: discord.Integration):
    if utils.check_if_valid_server(interaction.guild_id):
        await interaction.response.defer(ephemeral=True)
        file_functions.clear_file(utils.predictions_file, {})
        file_functions.clear_file(utils.tracked_messages, [])
        file_functions.clear_file(utils.scheduled_jobs, [])
        await interaction.followup.send("Cache tømt", ephemeral=True)
    else:
        await interaction.response.send_message("Denne kommandoen kan kun brukes i en spesifikk server.", ephemeral=True)


@bot.tree.command(name='sjekk_lagret_data', description='Sjekker predictions-fila')
@commands.has_permissions(manage_messages=True)
async def CheckIfPredictionIsStored(interaction: discord.Integration):
    await interaction.response.defer(ephemeral=True)
    channel = await bot.fetch_channel(channel_id)
    predictions_file = file_functions.read_file(utils.predictions_file)
    message_list = []
    for message_id, _ in predictions_file.items():
        message = await channel.fetch_message(int(message_id))
        if message:
            msg = f"Reactions for match {message} has been stored."
            message_list.append(msg)
    if message_list:
        await interaction.followup.send("\n".join(message_list), ephemeral=True)
    else:
        await interaction.followup.send("No stored predictions found.", ephemeral=True)



async def update_jobs(date_start, hour_start, minute_start, message_ids, channel):

    # Remove existing jobs
    if scheduler.get_jobs():
        scheduler.remove_all_jobs()
        print("Old jobs removed")

    if not date_start:  # Check if there are no new jobs to schedule
        print("No new jobs to schedule.")
        return False

    job_details_list = []  # List to hold details of each job
    existing_jobs = file_functions.read_file(utils.scheduled_jobs)
    
    if not isinstance(existing_jobs, list):
            existing_jobs = []
    
    # Schedule new jobs
    for date, hour, minute, message_id in zip(date_start, hour_start, minute_start, message_ids):
        scheduler.add_job(
            leaderboard.store_predictions, 
            'cron', 
            day_of_week=date, 
            hour=hour, 
            minute=minute, 
            timezone=timezone, 
            args=[message_id, channel, bot], 
            id=str(message_id)
        )

        save_schedule_to_json = {
            "message_id": message_id,
            "date": date,
            "hour": hour,
            "minute": minute
        }
        
        existing_jobs.append(save_schedule_to_json)

        job_details = f"Job ID: {message_id}, Scheduled Time: {date} at {hour}:{minute}, Function: {leaderboard.store_predictions.__name__}"
        job_details_list.append(job_details)

    file_functions.write_file(utils.scheduled_jobs, existing_jobs)

    print("Jobs added.")
    for details in job_details_list:
        print(details)

    return True

@bot.tree.command(name='finne_luremuser', description='Sjekker om folk har reagert på melding etter kampstart')
@commands.has_permissions(manage_messages=True)
async def FindLuremuser(
    interaction: discord.Interaction,
    message_id: str,
    channel: discord.TextChannel | None = None,
):
    await interaction.response.defer(ephemeral=True)

    try:
        tracked_channel = await bot.fetch_channel(channel_id)
        message = await tracked_channel.fetch_message(int(message_id))
        if not message:
            await interaction.followup.send("❌ Fant ikke meldingen.", ephemeral=True)
            return

        predictions = file_functions.read_file(utils.predictions_file)
        prediction_data = predictions.get(message_id, {})

        late_reactors = []

        for reaction in message.reactions:
            emoji = str(reaction.emoji)
            stored_users = prediction_data.get(emoji, [])

            async for user in reaction.users():
                if user.bot:
                    continue

                user_tag = f"<@{user.id}>"
                if user_tag not in stored_users:
                    late_reactors.append((user_tag, emoji))

        if late_reactors:
            lines = [f"{user} med {emoji}" for user, emoji in late_reactors]
            content = (
                f"⚠️ Følgende brukere har **reagert etter kampstart** på meldingen:\n"
                f"{message.jump_url}\n\n" +
                "\n".join(lines)
            )
        else:
            content = f"✅ Alle reaksjoner er lagret for kampen: {message.jump_url}"

        # Send either to specified channel or as ephemeral followup
        if channel:
            await channel.send(content)
            await interaction.followup.send(
                f"Resultatet ble sendt til {channel.mention}.", ephemeral=False
            )
        else:
            await interaction.followup.send(content, ephemeral=False)

    except discord.NotFound:
        await interaction.followup.send("❌ Meldingen ble ikke funnet. Dobbeltsjekk meldings-ID.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Mangler tillatelse til å hente meldingen eller sende i kanalen.", ephemeral=True)
    except discord.HTTPException:
        await interaction.followup.send("❌ Noe gikk galt under henting av meldingen eller sending av svar.", ephemeral=True)





bot.run(os.getenv('BOT_TOKEN'))




