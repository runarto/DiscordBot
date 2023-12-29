from importFile import *


def run_bot():
    client.run(perms.TOKEN)

async def main_bot():

    # update_hour = int(input("Update jobs hour: "))
    # update_minute = int(input("Update jobs minute"))
    # hour_leaderboard = int(input("Send leaderboard hour"))
    # minute_leaderbaord = int(input("Send leaderboard mintue"))
    
    #scheduler.add_job(update_jobs, 'cron', day_of_week='wed', hour=update_hour, minute=update_minute, args=[scheduler], name='update_jobs')
    #scheduler.add_job(send_leaderboard_message, 'cron', day_of_week='wed', hour = hour_leaderboard, minute=minute_leaderbaord, name='test_run')
    #scheduler.add_job(send_scheduled_matches, 'cron', day_of_week='wed', hour= update_hour, minute=update_minute+2, timezone=perms.timezone, name='send_scheduled_matches')
    scheduler.start()

    await client.start(perms.TOKEN)


async def update_jobs(date_start, hour_start, minute_start, message_ids):

    if not date_start:  # Check if there are no new jobs to schedule
        print("No new jobs to schedule.")
        return

    # Remove existing jobs
    for job in scheduler.get_jobs():
        if job.id in message_ids:
            try:
                scheduler.remove_job(job.id)
                print(f"Job {job.id} removed successfully.")
            except JobLookupError:
                print(f"Job {job.id} could not be found.")
            except Exception as e:
                print(f"An error occurred while removing job {job.id}: {e}")

    # Schedule new jobs
    for date, hour, minute, message_id in zip(date_start, hour_start, minute_start, message_ids):
        job_function = partial(compare_and_update_reaction_for_message, message_id)
        scheduler.add_job(job_function, 'cron', day_of_week=date, hour=hour, minute=minute, timezone=perms.timezone, id=message_id)
    
    # Print scheduled jobs
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

            data = []
            for fixture in fixtures: #Itererer omver kampenee
                print(fixture)
                # Format the message with fixture details
                message_content = f"{fixture['home_team']} vs {fixture['away_team']}" #Genererer melding

                # Send the message to the channel
                message = await channel.send(message_content) #Sender melding om kamp
                data.append((message.id ,fixture['match_id']))


    
        
                
                await message.add_reaction('🏠') #Legger til reaksjoner. 
                await message.add_reaction('🏳️') #Benytter disse tre fast for å gjøre det lettere
                await message.add_reaction('✈️')
            
            file_functions.write_file(logic.tracked_messages, data) #Lagrer meldinger i en JSON. 

            

            
        
        else:
            print(f"Could not find channel with ID {channel_id}")
    except discord.errors.Forbidden:
        print(f"Missing permissions to send message in channel {channel_id}")
    except Exception as e:
        print(f"An error occurred: {e}")


async def send_scheduled_matches(): #Egentlig overflødig 
    await send_message_to_channel() 


#Brukes bare til å returnere hvilken dag det er, time, minutt og melding

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


#Legger til i input_predictions-fila

@client.event
async def on_reaction_add(reaction, user):
# Ignore the bot's own reactions

    if user == client.user:
        return

    else:
        if reaction.message.channel.id == channel_id:
            message_id = reaction.message.id
                # Check if the user already reacted with a different emoji
            if (await user_already_reacted(reaction, user)):
                return
            else:
                file_functions.save_reaction_data(str(reaction.emoji), user.mention, user.display_name, message_id)
                print(f"Reaction added by {user.name}: {reaction.emoji} from message {reaction.message.content}")
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
                    file_functions.remove_reaction_data(str(reactions.emoji), user.mention, user.display_name,reaction.message.id)
                    # Save the new reaction data
                    file_functions.save_reaction_data(str(reaction.emoji), user.mention, user.display_name, reaction.message.id)
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
            file_functions.remove_reaction_data(str(reaction.emoji), user.id, user.display_name, reaction.message.id)
            print(f"Reaction removed by {user.name}: {reaction.emoji} from message {reaction.message.content}")
    except Exception as e:
        print(f"Error in on_reaction_remove: {e}")

#Funksjonene under blir brukt implisitt for å sende ut en melding med informasjon 
#resultater. Selve meldingen blir sendt i send_message_to_channel() funksjonen

def update_user_scores(days):
    try:
        predictions = file_functions.read_file(logic.output_predictions_file) #{message_id, [data]}

        sorted_predictions = {}

        # Sort the order_tuple based on match_id
        order_tuple = file_functions.read_file(logic.tracked_messages)
        order_tuple.sort(key=lambda x: x[1])

        # Iterate through the sorted order_tuple and populate the sorted_data dictionary
        for message_content_id, _ in order_tuple:
            if message_content_id in predictions:
                sorted_predictions[message_content_id] = predictions[message_content_id]
        
        if not predictions:
            return {}, [], 0
        
        actual_results = logic.get_match_results(days) 
        num_of_games = len(actual_results)
        
        user_scores = file_functions.read_file(logic.user_scores) #Total poengsum all-time

        if len(actual_results) != len(predictions):
            # If they don't have the same size, remove elements from predictions
            keys_to_remove = [key for key in predictions if key not in actual_results]
            for key in keys_to_remove:
                del predictions[key]



        this_week_user_score = []  #Ukens poeng

        for message_id, user_predictions in predictions.items():
            for prediction in user_predictions:
                user_id = prediction['user_id']
                user_display_name = prediction['user_nick']
                user_prediction = prediction['reaction']

        # Initialize score for each user if not already present
                if user_display_name not in user_scores:
                    user_scores[user_display_name] = 0

        # Rest of your scoring logic
                actual_result = actual_results.keys()
                actual_result = "🏠" if actual_result is True else ("✈️" if actual_result is False else "🏳️")
                predicted_result = user_prediction

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


def format_leaderboard_message(days):
    user_scores, this_week_user_scores, num_of_games = update_user_scores(days)
    
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
async def send_leaderboard_message(days):
    while True:
        message = format_leaderboard_message(days)
        if message:
            channel = client.get_channel(channel_id)
            if channel:  # Check if channel is found
                await channel.send(message)
                return
            else:
                print(f"Could not find channel with ID {channel_id}")
        else:
            print("No message to send.")

        # Wait for 180 seconds (3 minutes) before checking again
        await asyncio.sleep(180)




async def compare_and_update_reaction_for_message(message_id):
    """
    Compares stored reaction data with current reactions on Discord for a specific message and updates as necessary.

    :param message_id: ID of the message to compare reactions for.
    """
    # Load reaction data from the JSON file
    with open(logic.predictions_file, 'r') as file:
        stored_reactions = json.load(file)

    # Check if the specific message_id is in the stored reactions
    if message_id not in stored_reactions:
        print(f"No stored reactions found for message ID {message_id}")
        return

    # Fetch the current reactions from Discord for this message ID
    current_reactions = await fetch_current_reactions(message_id)

    # Dictionary to track reactions for each user
    user_reactions = {}
    for reaction_type, user_ids in current_reactions.items():
        for user_id in user_ids:
            user_reactions.setdefault(user_id, []).append(reaction_type)

    # List to hold the updated reaction data for this message
    updated_reactions_list = []

    # Process reactions for each user in the stored reactions
    for stored_user_data in stored_reactions[message_id]:
        stored_user_id = stored_user_data['user_id']
        stored_reaction_type = stored_user_data['reaction_type']
        current_user_reactions = user_reactions.get(stored_user_id, [])

        # Apply logic based on the number of current reactions for the user
        if len(current_user_reactions) == 1 and current_user_reactions[0] != stored_reaction_type:
            updated_reactions_list.append({
                "user_id": stored_user_id, 
                "user_nick": stored_user_data["user_nick"], 
                "reaction": current_user_reactions[0]
            })
        elif len(current_user_reactions) == 2:
            if stored_reaction_type in current_user_reactions:
                new_reaction = next(reaction for reaction in current_user_reactions if reaction != stored_reaction_type)
                updated_reactions_list.append({
                    "user_id": stored_user_id, 
                    "user_nick": stored_user_data["user_nick"], 
                    "reaction": new_reaction
                })
            else:
                updated_reactions_list.append({
                    "user_id": stored_user_id, 
                    "user_nick": stored_user_data["user_nick"], 
                    "reaction": '🏠'
                })
        elif len(current_user_reactions) >= 3:
            updated_reactions_list.append({
                "user_id": stored_user_id, 
                "user_nick": stored_user_data["user_nick"], 
                "reaction": '🏠'
            })

    # Save the updated reactions list for the specific message
    outputData = {}
    outputData[message_id] = updated_reactions_list
    logic.write_file(logic.output_predictions_file, outputData)







# Function to fetch message by ID and content
async def fetch_current_reactions(message_id):
    """
    Fetches the current reactions for a message and structures them as
    reaction_type -> list of user IDs who reacted with that type.

    :param client: Discord client object.
    :param channel_id: ID of the channel where the message is located.
    :param message_id: ID of the message to fetch reactions for.
    :return: Dictionary with reaction types as keys and lists of user IDs as values.
    """
    try:
        # Get the channel object from its ID
        channel = client.get_channel(channel_id)
        if channel is None:
            print("Channel not found.")
            return {}

        # Fetch the message from the channel
        message = await channel.fetch_message(message_id)

        # Dictionary to hold the reactions data
        reactions_data = {}

        # Iterate over each reaction in the message
        for reaction in message.reactions:
            # Ignore reactions added by the bot itself
            if reaction.me:
                continue

            # List to hold user IDs for this reaction type
            user_ids = []

            # Fetch the users who reacted with this emoji
            users = await reaction.users().flatten()
            for user in users:
                if user != client.user:  # Ignore bot's own reactions
                    user_ids.append(user.id)

            # Assign the list of user IDs to the reaction type
            reactions_data[str(reaction.emoji)] = user_ids

        return reactions_data
    except discord.NotFound:
        print("Message not found.")
    except discord.Forbidden:
        print("Missing permissions to read this message.")
    except discord.HTTPException as e:
        print(f"HTTP exception: {e}")
        return {}


