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
from collections import defaultdict


channel_id = perms.CHANNEL_ID

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler()

def run_bot():
    client.run(perms.TOKEN)

async def main_bot():
    
    scheduler.add_job(update_jobs, 'cron', day_of_week='tue', hour=0, minute=0, args=[scheduler], name='update_jobs')

    scheduler.add_job(send_scheduled_matches, 'cron', day_of_week='tue', hour=15, minute=0, timezone=perms.timezone, name='send_scheduled_matches')

    scheduler.start()

    await client.start(perms.TOKEN)


async def update_jobs(scheduler):
    
    date_start, hour_start, minute_start, messages = get_day_hour_minute()

    
    for job in scheduler.get_jobs():
        if job.name == 'save_predictions_to_json':
            job.remove()

    
    for date, hour, minute, message in zip(date_start, hour_start, minute_start, messages):
        job_function = partial(file_functions.save_predictions_to_json, 'input_predictions.json', 'output_predictions.json', message)
        scheduler.add_job(job_function, 'cron', day_of_week=date, hour=hour, minute=minute, timezone=perms.timezone, name='save_predictions_to_json')

#trenger å resette input_predictions-fila typ hver tirsdag. samme gjelder output predictions



@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await send_message_to_channel()
    print(logic.tracked_messages)


#Sender melding ut til kanalen med kampene for oppkommende uke, og legger til reaksjoner

@client.event
async def send_message_to_channel():
    with open(logic.predictions_file, 'w') as file:
        json.dump({}, file)
    try:
        channel = client.get_channel(channel_id)
        if channel:
            message = format_leaderboard_message()
            await channel.send(message)

            with open(logic.output_predictions_file, 'w') as file:
                json.dump({}, file)


            fixtures = logic.get_matches(7)

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
    await send_message_to_channel()


#Brukes bare til å returnere hvilken dag det er, time, minutt og melding

def get_day_hour_minute():

    day_of_week = []
    hour = []
    minute = []
    data = logic.get_matches(7)
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


#Legger til i input_predictions-fila

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



#Denne funksjonen sjekker bare om en bruker allerede har reagert, og fjerner isåfall den forrige reaksjonen,
#og oppdaterer med den nye. 

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


#Denne funksjonen fjerner data fra input_predictions-fila dersom noen fjerner en reaksjon

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

#Denne funksjonen kjører 7 dager etter meldingen om kamper blir sendt.
def update_user_scores():
    try:
        predictions = file_functions.read_predictions("output_predictions.json")
        if not predictions:
            return {}, {}, 0
        actual_results = logic.get_match_results()
        num_of_games = len(actual_results)
        logic.user_scores = {}
        this_week_user_score = defaultdict(int)  # Using defaultdict for automatic handling of new keys

        for game, user_predictions in predictions.items():
            actual_result = actual_results.get(game)
            if actual_result is not None:
                for prediction in user_predictions:
                    username = prediction['username']
                    predicted_result = "\ud83c\udfe0" if actual_result is True else ("\u2708\ufe0f" if actual_result is False else "\ud83c\udff3\ufe0f")
                    if predicted_result == prediction['reaction']:
                        logic.user_scores[username] = logic.user_scores.get(username, 0) + 1
                        this_week_user_score[username] += 1

        return logic.user_scores, dict(this_week_user_score), num_of_games

    except (FileNotFoundError, KeyError, TypeError) as e:
        print(f"An error occurred: {e}")
        # Return empty data or handle the error as needed
        return {}, {}, 0

#Sorterer 

def sort_user_scores(user_scores):
    if user_scores is None:
        return
    # Convert dictionary into a list of tuples and sort by score in descending order
    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores



def format_leaderboard_message():
    # Sort this week's scores in descending order
    user_scores, this_week_user_scores, num_of_games = update_user_scores()
    
    if not user_scores:
        return
    
    if not this_week_user_scores:
        return


    sorted_user_score = sort_user_scores(user_scores)
    sorted_this_week_user_scores = sort_user_scores(this_week_user_scores)


    # Start the message with the total number of games
    message_parts = [f"Av {num_of_games} mulige:"]

    # Add this week's scores and corresponding users to the message
    for score, users in sorted_this_week_user_scores:
        users_str = ', '.join(users)
        message_parts.append(f"{score} poeng denne uken: {users_str}")

    # Add the congratulatory note for this week's winner
    weekly_winner = sorted_this_week_user_scores[0][0]  # username of this week's top scorer
    message_parts.append(f"Gratulerer til ukas vinner {weekly_winner}!")

    # Add the overall leaderboard
    message_parts.append("Total poeng:")
    for rank, (username, score) in enumerate(sorted_user_score, start=1):
        message_parts.append(f"{rank}. {username}: - {score}p")

    return '\n'.join(message_parts)

@client.event
async def send_leaderboard_message():
        channel = client.get_channel(channel_id)
        message = format_leaderboard_message()
        await channel.send(message)




