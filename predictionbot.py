import discord
import logic
import asyncio
import json
import file_functions
from dateutil import parser
import perms
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from functools import partial
from collections import defaultdict
from datetime import datetime
from apscheduler.jobstores.base import JobLookupError



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
    
    scheduler.add_job(update_jobs, 'cron', day_of_week='wed', hour=18, minute=25, args=[scheduler], name='update_jobs')

    scheduler.add_job(send_leaderboard_message, 'cron', day_of_week='wed', hour = 23, minute=30, name='test_run')

    scheduler.add_job(send_scheduled_matches, 'cron', day_of_week='wed', hour=18, minute=30, timezone=perms.timezone, name='send_scheduled_matches')

    scheduler.start()

    await client.start(perms.TOKEN)


async def update_jobs(scheduler):
    
    date_start, hour_start, minute_start, messages = get_day_hour_minute()

    for message in messages:
        job_id = message

    for job in scheduler.get_jobs():
        try:
            if job.id == job_id:
                scheduler.remove_job(job_id)
                print(f"Job {job_id} removed successfully.")
        except JobLookupError:
            print(f"Job {job_id} could not be found.")
        except UnboundLocalError:
            pass
        except Exception as e:
            print(f"An error occurred while removing job {job_id}: {e}")

    if not date_start: #Hvis date_start er tom så er det ingen kamper. 
        print("No new jobs to schedule.")
        return
    
    
    for date, hour, minute, message in zip(date_start, hour_start, minute_start, messages):
        job_function = partial(file_functions.save_predictions_to_json, logic.predictions_file, logic.output_predictions_file, message)
        scheduler.add_job(job_function, 'cron', day_of_week=date, hour=hour, minute=minute, timezone=perms.timezone, name=job_id)
    
    jobs = scheduler.get_jobs()
    print("Scheduled Jobs:")
    for job in jobs:
        print(f"Job ID: {job.id}")
        print(f"Next Run Time: {job.next_run_time}")
        print(f"Job Function: {job.func_ref}")
        print("-" * 20)

#trenger å resette input_predictions-fila typ hver tirsdag. samme gjelder output predictions



@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


#Sender melding ut til kanalen med kampene for oppkommende uke, og legger til reaksjoner

@client.event
async def send_message_to_channel():
    file_functions.write_file(logic.predictions_file, {})

    with open(logic.predictions_file, 'w') as file: #Tømmer input_predictions-fila
        json.dump({}, file)
        print("Dumped old predictions 1/2\n")
    try:
        channel = client.get_channel(channel_id)
        if channel:
            message = format_leaderboard_message() 
            print(message)
            if message and message.strip(): #sjekker om meldinga ikke er tom
                await channel.send(message) #Sender melding om ukas resultater og leaderboard
            


            with open(logic.output_predictions_file, 'w') as file: #Tømmer output_predictions
                json.dump({}, file)
            
            print("Dumped old predictions 2/2\n")

            fixtures = logic.get_matches(0) #Henter inn kamper de neste x dagene

            for fixture in fixtures: #Itererer omver kampenee
                print(fixture)
                # Format the message with fixture details
                emoji = "<:brannbad:819294515755745281>"
                message_content = f"{fixture['home_team']} vs {fixture['away_team']}" #Genererer melding
                # Send the message to the channel
                message = await channel.send(message_content) #Sender melding om kamp
                logic.tracked_messages[message.id] = fixture['match_id'] #fixture['home_team'] + " " + fixture['away_team']

                home_team = fixture['home_team'] #Vet ikke hvorfor jeg har dette her
                away_team = fixture['away_team']
        
                
                await message.add_reaction('🏠') #Legger til reaksjoner. 
                await message.add_reaction('🏳️') #Benytter disse tre fast for å gjøre det lettere
                await message.add_reaction('✈️')


        else:
            print(f"Could not find channel with ID {channel_id}")
    except discord.errors.Forbidden:
        print(f"Missing permissions to send message in channel {channel_id}")
    except Exception as e:
        print(f"An error occurred: {e}")


async def send_scheduled_matches(): #Egentlig overflødig 
    await send_message_to_channel() 


#Brukes bare til å returnere hvilken dag det er, time, minutt og melding

def get_day_hour_minute():

    day_of_week = []
    hour = []
    minute = []
    data = logic.get_matches(0)
    messages = []
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

        messages.append(f"{date['home_team']} vs {date['away_team']}")

    return day_of_week, hour, minute, messages


#Legger til i input_predictions-fila

@client.event
async def on_reaction_add(reaction, user):
# Ignore the bot's own reactions

    if user == client.user:
        return

    else:
        if reaction.message.channel.id == channel_id:
            print("now hereeeeee")
            message_content = reaction.message.content
                # Check if the user already reacted with a different emoji
            if (await user_already_reacted(reaction, user)):
                return
            else:
                file_functions.save_reaction_data(str(reaction.emoji), user.mention, user.display_name, message_content)
                print(f"Reaction added by {user.name}: {reaction.emoji} from message {message_content}")
        else:
            return
    



#Denne funksjonen sjekker bare om en bruker allerede har reagert, og fjerner isåfall den forrige reaksjonen,
#og oppdaterer med den nye. 

async def user_already_reacted(reaction, user):
    for reactions in reaction.message.reactions:
        if reactions.emoji != reaction.emoji:
            async for users in reactions.users():
                if users == user:
                    # Remove the previous reaction data
                    file_functions.remove_reaction_data(str(reactions.emoji), user.id, reaction.message.content)
                    # Save the new reaction data
                    file_functions.save_reaction_data(str(reaction.emoji), user.id, user.display_name, reaction.message.content)
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
        if (reaction.message.author == client.user) and (reaction.message.channel.id == channel_id):
            file_functions.remove_reaction_data(str(reaction.emoji), user.name, reaction.message.content)
            print(f"Reaction removed by {user.name}: {reaction.emoji} from message {reaction.message.content}")
    except Exception as e:
        print(f"Error in on_reaction_remove: {e}")

#Funksjonene under blir brukt implisitt for å sende ut en melding med informasjon 
#resultater. Selve meldingen blir sendt i send_message_to_channel() funksjonen

def update_user_scores():
    try:
        predictions = file_functions.read_file(logic.output_predictions_file) #

        predictions = dict(sorted(predictions.items()))
        
        if not predictions:
            return {}, [], 0
        #actual_results = logic.get_match_results()
        actual_results = {
            "Message content 1": True,
            "Message content 2": None   
        }
        num_of_games = len(actual_results)
        
        user_scores = file_functions.read_file(logic.user_scores) #Laster inn json fil med user_scores



        this_week_user_score = []  # Using defaultdict for automatic handling of new keys

        for game_id, user_predictions in predictions.items():
            for prediction in user_predictions:
                user_id = prediction['user_id']
                user_display_name = prediction['user_nick']

        # Initialize score for each user if not already present
                if user_display_name not in user_scores:
                    user_scores[user_display_name] = 0

        # Rest of your scoring logic
                actual_result = actual_results.get(game_id)
                actual_result = "🏠" if actual_result is True else ("✈️" if actual_result is False else "🏳️")
                predicted_result = prediction['reaction']

                user_score_entry = next((item for item in this_week_user_score if item['user_id'] == user_id), None)
                if not user_score_entry:
                    user_score_entry = {'user_id': user_id, 'points': 0, 'user_nick': user_display_name}
                    this_week_user_score.append(user_score_entry)


                if predicted_result == actual_result:
                    user_scores[user_display_name] += 1
                    user_score_entry['points'] += 1
        
        return user_scores, this_week_user_score, num_of_games

    except (FileNotFoundError, KeyError, TypeError) as e:
        print(f"An error occurred: {e}")
        # Return empty data or handle the error as needed
        return {}, [], 0



#Sorterer 

def sort_user_scores(user_scores):
    if user_scores is None:
        return

    # Check if user_scores is a dictionary
    if isinstance(user_scores, dict):
        # Sorting the dictionary by its values (scores) in descending order
        sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores

    # Check if user_scores is a list of dictionaries
    elif isinstance(user_scores, list):
        # Sorting the list of dictionaries by 'points' in each dictionary in descending order
        sorted_scores = sorted(user_scores, key=lambda x: x['points'], reverse=True)
        return sorted_scores

    # Return an empty list if user_scores is neither a dict nor a list of dicts
    return  


def format_leaderboard_message():
    user_scores, this_week_user_scores, num_of_games = update_user_scores()
    
    if not user_scores or not this_week_user_scores:
        return

    message_parts = []

    if this_week_user_scores:
        sorted_this_week_user_scores = sort_user_scores(this_week_user_scores)
        print(sorted_this_week_user_scores)

        message_parts.append(f"**Av {num_of_games} mulige:**")
        for user in sorted_this_week_user_scores:
            message_parts.append(f"{user['points']} poeng: {user['user_nick']}")

        if sorted_this_week_user_scores:
            weekly_winner_user = sorted_this_week_user_scores[0]
            weekly_winner_id = weekly_winner_user['user_id'] # username of this week's top scorer
            message_parts.append(f"Gratulerer til ukas vinner {weekly_winner_id}!\n")

    if user_scores:
        sorted_user_score = sort_user_scores(user_scores)
        message_parts.append("Totale poeng:")
        for rank, (username, score) in enumerate(sorted_user_score, start=1):
            message_parts.append(f"{rank}. {username}: {score}p")

        file_functions.write_file(logic.user_scores, user_scores)

    return '\n'.join(message_parts)


@client.event
async def send_leaderboard_message():
    while True:
        message = format_leaderboard_message()
        if message:
            channel = client.get_channel(channel_id)
            if channel:  # Check if channel is found
                await channel.send(message)
                return
            else:
                print(f"Could not find channel with ID {channel_id}")
        else:
            print("No message to send.")

        # Wait for 60 seconds (1 minute) before checking again
        await asyncio.sleep(60)


