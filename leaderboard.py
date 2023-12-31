import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logic
import file_functions
import perms
import asyncio
import json
import traceback

channel_id = perms.CHANNEL_ID #Kanalen hvor kupongen sendes
intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True
scheduler = AsyncIOScheduler()
bot = commands.Bot(command_prefix="!", intents=intents)

def update_user_scores(days):
    try:
        counter = 0; 
        predictions = file_functions.read_file(logic.output_predictions_file) #{message_id, [data]}

        if not predictions:
            return {}, [], 0

        sorted_predictions = {}

        # Sort the order_tuple based on match_id
        order_tuple = file_functions.read_file(logic.tracked_messages)
        order_tuple.sort(key=lambda x: x[1])

        # Iterate through the sorted order_tuple and populate the sorted_data dictionary
        for message_content_id, _ in order_tuple:
            if message_content_id in predictions:
                sorted_predictions[message_content_id] = predictions[message_content_id]
    
        
        actual_results = logic.get_match_results(days) 
        actual_result = actual_results.keys()
        num_of_games = len(actual_results)
        
        user_scores = file_functions.read_file(logic.user_scores) #Total poengsum all-time

        if len(actual_results) != len(predictions):
            # If they don't have the same size, remove elements from predictions
            keys_to_remove = [key for key in predictions if key not in actual_results]
            for key in keys_to_remove:
                del predictions[key]



        this_week_user_score = []  #Ukens poeng

        for message_id, user_predictions in predictions.items():
            actual_result = actual_result[counter]
            for prediction in user_predictions:
                user_id = prediction['user_id']
                user_display_name = prediction['user_nick']
                user_prediction = prediction['reaction']

        # Initialize score for each user if not already present
                if user_display_name not in user_scores:
                    user_scores[user_display_name] = 0

        # Rest of your scoring logic
                #Inneholder sortert liste med True, False, None 
                actual_result = "🏠" if actual_result is True else ("✈️" if actual_result is False else "🏳️")
                predicted_result = user_prediction

                user_score_entry = next((item for item in this_week_user_score if item['user_id'] == user_id), None)
                if not user_score_entry:
                    user_score_entry = {'user_id': user_id, 'points': 0, 'user_nick': user_display_name}
                    this_week_user_score.append(user_score_entry)


                if predicted_result == actual_result:
                    user_scores[user_display_name] += 1
                    user_score_entry['points'] += 1

            counter+= 1
        
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


@bot.event
async def send_leaderboard_message(days):
    message = format_leaderboard_message(days)
    if message:
        channel = bot.get_channel(perms.CHANNEL_ID)
        if channel:  # Check if channel is found
            await channel.send(message)
            return
        else:
            print(f"Could not find channel with ID {perms.CHANNEL_ID}")
    else:
        print("No message to send.")



async def compare_and_update_reaction_for_message(message_id, channel, bot):
    """
    Compares stored reaction data with current reactions on Discord for a specific message and updates as necessary.

    :param message_id: ID of the message to compare reactions for.
    """
    try:
        # Load reaction data from the JSON file
        with open(logic.predictions_file, 'r') as file:
            stored_reactions = json.load(file)
        
        with open(logic.output_predictions_file, 'r') as file:
            if file.read(1):
                file.seek(0)  # Reset file read position
                outputData = json.load(file)
            else:
                outputData = {}  # Initialize as empty dictionary if file is empty
        print(outputData)


        # Fetch the current reactions from Discord for this message ID
        current_reactions = await fetch_current_reactions(message_id, channel, bot)

        # Dictionary to track reactions for each user
        user_reactions = {}
        for reaction_type, user_ids in current_reactions.items():
            for user_id in user_ids:
                if user_id:
                    user_reactions.setdefault(user_id, []).append(reaction_type)

        # List to hold the updated reaction data for this message
        updated_reactions_list = []

        # Check if the specific message_id is in the stored reactions
        if str(message_id) not in stored_reactions.keys():
            print(f"No stored reactions found for message ID {message_id}")
            for user_id, reaction_types in user_reactions.items():
                user = await bot.fetch_user(int(user_id.strip('<@!>')))
                user_nick = user.display_name  # Fetch the display name of the user

                # Check if the user has used one or more reactions
                if len(reaction_types) > 1:
                    updated_reactions_list.append({
                        "user_id": user_id, 
                        "user_nick": user_nick, 
                        "reaction": '🏠'
                    })
                else:
                    updated_reactions_list.append({
                        "user_id": user_id, 
                        "user_nick": user_nick, 
                        "reaction": reaction_types[0]
                    })

            
            
            outputData[str(message_id)] = updated_reactions_list
            file_functions.write_file(logic.output_predictions_file, outputData)
            return


        # Process reactions for each user in the stored reactions
        else:
            print("I am become death")
            for stored_user_data in stored_reactions[str(message_id)]:
                stored_user_id = stored_user_data['user_id']
                stored_reaction_type = stored_user_data['reaction']
                current_user_reactions = user_reactions.get(stored_user_id, [])
                print(current_user_reactions, "Here")
                print(stored_reaction_type,"stored reaction")

                # Apply logic based on the number of current reactions for the user
                if len(current_user_reactions) == 1 and current_user_reactions[0] != stored_reaction_type:
                    updated_reactions_list.append({
                        "user_id": stored_user_id, 
                        "user_nick": stored_user_data["user_nick"], 
                        "reaction": current_user_reactions[0]
                    })
                    print("Case 1")
                elif len(current_user_reactions) == 2:
                    if stored_reaction_type in current_user_reactions:
                        new_reaction = next(reaction for reaction in current_user_reactions if reaction != stored_reaction_type)
                        updated_reactions_list.append({
                            "user_id": stored_user_id, 
                            "user_nick": stored_user_data["user_nick"], 
                            "reaction": new_reaction
                        })
                        print("Case 2")
                    else:
                        updated_reactions_list.append({
                            "user_id": stored_user_id, 
                            "user_nick": stored_user_data["user_nick"], 
                            "reaction": '🏠'
                        })
                        print("Case 2.1")
                elif len(current_user_reactions) >= 3:
                    updated_reactions_list.append({
                        "user_id": stored_user_id, 
                        "user_nick": stored_user_data["user_nick"], 
                        "reaction": '🏠'
                    })
                    print("Case 3")

        # Save the updated reactions list for the specific message
            outputData[str(message_id)] = updated_reactions_list
            print(outputData)
            file_functions.write_file(logic.output_predictions_file, outputData)
            return

    except discord.NotFound:
        print("Message or channel not found.")
        return {}
    except discord.Forbidden:
        print("Missing permissions to read the message or channel.")
        return {}
    except discord.HTTPException as e:
        print(f"HTTP exception occurred: {e}")
        return {}


async def fetch_current_reactions(message_id, channel, bot):
    """
    Fetches the current reactions for a message and structures them as
    reaction_type -> list of user IDs who reacted with that type.

    :param message_id: ID of the message to fetch reactions for.
    :return: Dictionary with reaction types as keys and lists of user IDs as values.
    """
    try:

        if channel is None:
            print("Channel not found. Unable to proceed.")
            return {}

        print(f"Attempting to fetch message with ID: {message_id} from channel: {channel.name}")
        message = await channel.fetch_message(message_id)
        print(f"Message fetched: {message.id} - Content: {message.content}")

        reactions_data = {}
        print(f"Starting to process reactions for message ID: {message_id}")

        for reaction in message.reactions:
            print(f"Processing reaction: {reaction.emoji} - Count: {reaction.count}")

            user_ids = []
            print(f"Fetching users for reaction: {reaction.emoji}")

            users = [user async for user in reaction.users()]
            print(f"Fetched {len(users)} users for reaction: {reaction.emoji}")

            for user in users:
                print(user)

                # Check if user is None
                if user is None:
                    print("Encountered None in users list.")
                    continue

                # Check if bot.user is None
                if bot.user is None:
                    print("Bot user object is None.")
                    continue

                # Check if the user is not the bot
                if user.id != bot.user.id:
                    # Add the user's ID to the list
                    user_ids.append(user.mention)
                    print(f"Added user ID: {user.id} for reaction: {reaction.emoji}")
                else:
                    print(f"Skipping bot's own reaction: {reaction.emoji}")

            reactions_data[str(reaction.emoji)] = user_ids
            print(f"Collected {len(user_ids)} user(s) for reaction: {reaction.emoji}")

        print(f"Completed processing reactions for message ID: {message_id}")
        print(reactions_data)
        return reactions_data
    except discord.NotFound:
        print("Message or channel not found.")
        return {}
    except discord.Forbidden:
        print("Missing permissions to read the message or channel.")
        return {}
    except discord.HTTPException as e:
        print(f"HTTP exception occurred: {e}")
        return {}

