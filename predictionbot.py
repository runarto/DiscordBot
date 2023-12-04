import discord
import logic
import asyncio
import json
import file_functions
from dateutil import parser
import datetime
import perms
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from functools import partial


channel_id = perms.CHANNEL_ID

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler()

async def main_bot():
    
    scheduler.add_job(update_jobs, 'cron', day_of_week='tue', hour=0, minute=0, args=[scheduler], name='update_jobs')

    scheduler.add_job(send_scheduled_matches, 'cron', day_of_week='tue', hour=15, minute=0, timezone=perms.timezone, name='send_scheduled_matches')

    scheduler.start()

    await client.start(perms.TOKEN)


    await client.start(perms.TOKEN)

async def update_jobs(scheduler):
    
    date_start, hour_start, minute_start, messages = get_day_hour_minute()

    
    for job in scheduler.get_jobs():
        if job.name == 'save_predictions_to_db_job':
            job.remove()

    
    for date, hour, minute, message in zip(date_start, hour_start, minute_start, messages):
        job_function = partial(file_functions.save_predictions_to_db, 'predictions.json', 'predictions.db', message)
        scheduler.add_job(job_function, 'cron', day_of_week=date, hour=hour, minute=minute, timezone=perms.timezone, name='save_predictions_to_db_job')



@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    print(logic.tracked_messages)

@client.event
async def send_message_to_channel(client, channel_id):
    try:
        channel = client.get_channel(channel_id)
        if channel:

            fixtures = logic.get_matches()

            for fixture in fixtures:
                # Format the message with fixture details
                message_content = f"{fixture['date']}\n{fixture['home_team']} vs {fixture['away_team']}"
                # Send the message to the channel
                message = await channel.send(message_content)
                logic.tracked_messages[message.id] = fixture['home_team'] + " " + fixture['away_team']

                home_team = fixture['home_team']
                away_team = fixture['away_team']
        
                #await message.add_reaction(logic.emoji_dictionary[home_team])
                await message.add_reaction('🏠')
                await message.add_reaction('🏳️')
                await message.add_reaction('✈️')
                # await message.add_reaction(logic.emoji_dictionary[away_team


        else:
            print(f"Could not find channel with ID {channel_id}")
    except discord.errors.Forbidden:
        print(f"Missing permissions to send message in channel {channel_id}")
    except Exception as e:
        print(f"An error occurred: {e}")


async def send_scheduled_matches():
    await send_message_to_channel(client, perms.CHANNEL_ID)



def get_day_hour_minute():

    day_of_week = []
    hour = []
    minute = []
    data = logic.get_matches()
    messages = []
    for date in data:
     # Parse the date string into a datetime object
        date_time = datetime.fromisoformat(date['date'])
        # Get the day of the week
        day_of_week_add = date_time.strftime('%A')[:3].lower()
        day_of_week.append(day_of_week_add)
        # Get the hour and minute
        hour_add = date_time.strftime('%H')
        hour.append(hour_add)

        minute_add = date_time.strftime('%M')[:1]
        minute.append(minute_add)

        messages.append(f"{date['date']}\n{date['home_team']} vs {date['away_team']}")

    return day_of_week, hour, minute, messages




@client.event
async def on_reaction_add(reaction, user):
    # Ignore the bot's own reactions
    
    if user == client.user:
            return
    
    message_content = reaction.message.content
    datetime_str = message_content.split('\n')[0].strip()
    
    # Parse the datetime string into a datetime object
    match_start = parser.isoparse(datetime_str)

    # Check if current time is before the match start time
    #if datetime.datetime.now(datetime.timezone.utc) < match_start:

    if reaction.message.author == client.user:
            # Check if the user already reacted with a different emoji
        if (await user_already_reacted(reaction, user)):
            return
        else:
            file_functions.save_reaction_data(str(reaction.emoji), user.name, reaction.message.content)
            print(f"Reaction added by {user.name}: {reaction.emoji} from message {reaction.message.content}")
    #else:
        #print(f"User {user.name} tried to react with {reaction.emoji} on the message {reaction.message.content}, but the game was already started\n.")
        #await reaction.remove(user)





async def user_already_reacted(reaction, user):
    for reactions in reaction.message.reactions:
        if reactions.emoji != reaction.emoji:
            async for users in reactions.users():
                if users == user:
                    # Remove the previous reaction data
                    file_functions.remove_reaction_data(str(reactions.emoji), user.name, reaction.message.content)
                    # Save the new reaction data
                    file_functions.save_reaction_data(str(reaction.emoji), user.name, reaction.message.content)
                    # Remove the user's previous reaction
                    await reactions.remove(user)
                    return True
    return False  # Return False if no previous reaction was found




@client.event
async def on_reaction_remove(reaction, user):
    try:
        if user == client.user:
            return
        if reaction.message.author == client.user:
            file_functions.remove_reaction_data(str(reaction.emoji), user.name, reaction.message.content)
            print(f"Reaction removed by {user.name}: {reaction.emoji} from message {reaction.message.content}")
    except Exception as e:
        print(f"Error in on_reaction_remove: {e}")