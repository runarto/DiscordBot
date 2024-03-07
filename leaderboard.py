import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logic
import file_functions
import perms
import json





channel_id = perms.CHANNEL_ID #Kanalen hvor kupongen sendes
import traceback


async def update_user_scores():
    try:

        all_users = file_functions.read_file(logic.all_users)
        
        predictions = file_functions.read_file(logic.output_predictions_file) #{message_id, [data]}
        print("predictions fetched\n")

        if not predictions:
            return {}, [], 0

        team_emojis = file_functions.read_file(logic.team_emojis_file)
        print("emojis fetched\n")

        # Sort the order_tuple based on match_id
        order_tuple = file_functions.read_file(logic.tracked_messages) #[message-id, match-id]
        message_match_dict = dict(order_tuple) #message_match_dict[message_id] = match_id
        print("message-match\n")


        
        num_of_games = 0
        user_scores = file_functions.read_file(logic.user_scores) #Total poengsum all-time
        this_week_user_score = []  #Ukens poeng

        for message_id, user_predictions in predictions.items():
            match_id = message_match_dict.get(message_id)
            print(f"{match_id}\n")
            
            actual_result, home_team, away_team = await logic.get_match_results(match_id)
            actual_result = None
            print(f"{actual_result}\n")
            home_team_emoji = team_emojis.get(home_team)
            away_team_emoji = team_emojis.get(away_team)

            if home_team_emoji is None:
                home_team_emoji = "🏠"
            if away_team_emoji is None:
                away_team_emoji = "✈️"

            actual_result = home_team_emoji if actual_result is True else (away_team_emoji if actual_result is False else "\U0001F1FA")


            if (actual_result != "No result"):
                num_of_games+=1

                for prediction in user_predictions:
                    user_id = prediction['user_id']
                    user_display_name = prediction['user_nick']
                    user_prediction = prediction['reaction']

                    if user_display_name not in all_users:
                        all_users[user_display_name] = user_id.strip('<@!>')

                    print(user_display_name)
                    print(user_prediction)

            # Initialize score for each user if not already present
                    if user_display_name not in user_scores:
                        user_scores[user_display_name] = 0

            # Rest of your scoring logic

                    user_score_entry = next((item for item in this_week_user_score if item['user_id'] == user_id), None)
                    if not user_score_entry:
                        user_score_entry = {'user_id': user_id, 'points': 0, 'user_nick': user_display_name}
                        this_week_user_score.append(user_score_entry)


                    if user_prediction == actual_result:
                        user_scores[user_display_name] += 1
                        user_score_entry['points'] += 1

        print(this_week_user_score)

        file_functions.write_file(logic.all_users, all_users)

        return user_scores, this_week_user_score, num_of_games

    except (FileNotFoundError, KeyError, TypeError) as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

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


async def format_leaderboard_message(guild):
    
    user_scores, this_week_user_scores, num_of_games = await update_user_scores()
    print("scores fetched\n")

    username_to_id = file_functions.read_file(logic.all_users)
    print(username_to_id)

    team_emojis = file_functions.read_file(logic.team_emojis_file)
    
    if not user_scores or not this_week_user_scores:
        return

    message_parts = []

    if this_week_user_scores:
        sorted_this_week_user_scores = sort_user_scores(this_week_user_scores)
        points_to_users = {}
        for user in sorted_this_week_user_scores:
            points = user['points']
            if points not in points_to_users:
                points_to_users[points] = []
            points_to_users[points].append(user['user_nick'])

        message_parts.append(f"**Av {num_of_games} mulige:**")
        for points, users in sorted(points_to_users.items(), reverse=True):
            names = ', '.join(users)
            message_parts.append(f"{points} poeng: {names}")

        # Check for and announce the weekly winner
        if sorted_this_week_user_scores:
        # Find the highest score
            highest_score = sorted_this_week_user_scores[0]['points']

            # Find all users who have achieved the highest score
            winners = [user['user_id'] for user in sorted_this_week_user_scores if user['points'] == highest_score]

            # Format the congratulatory message
            if len(winners) > 1:
                # Join all but the last winner with commas, and append the last winner with "og"
                winners_formatted = ', '.join(winners[:-1]) + " og " + winners[-1]
                message_parts.append(f"Gratulerer til ukas vinnere {winners_formatted}!\n")
            else:
                message_parts.append(f"Gratulerer til ukas vinner {winners[0]}!\n")

    if user_scores:
        sorted_user_score = sort_user_scores(user_scores)
        message_parts.append("Totale poeng:")
        for rank, (username, score) in enumerate(sorted_user_score, start=1):
            user_id = username_to_id.get(username)
            if user_id is not None:
                user_id = user_id.strip('<@!>')
            role = await get_user_primary_role(user_id, guild, team_emojis)
            if role == None:
                role = ""
            message_parts.append(f"{rank}. {role}{username}: {score}p")

        file_functions.write_file(logic.user_scores, user_scores)

    return '\n'.join(message_parts)





async def compare_and_update_reaction_for_message(message_id, channel, bot):
    """
    Compares stored reaction data with current reactions on Discord for a specific message and updates as necessary.

    :param message_id: ID of the message to compare reactions for.
    """
    message_id = str(message_id)
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
        
        if message_id not in stored_reactions.keys():
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

            if str(message_id) in outputData:
                del outputData[str(message_id)]
            
            outputData[message_id] = updated_reactions_list
            file_functions.write_file(logic.output_predictions_file, outputData)
            return
        


        # Process reactions for each user in the stored reactions
        
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
            elif len(current_user_reactions) == 1 and current_user_reactions[0] == stored_reaction_type:
                updated_reactions_list.append({
                    "user_id": stored_user_id, 
                    "user_nick": stored_user_data["user_nick"], 
                    "reaction": current_user_reactions[0]
                })
                print("Case 1.1")
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

        if str(message_id) in outputData:
            del outputData[str(message_id)]
        
        outputData[message_id] = updated_reactions_list
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
    


async def fetch_user_primary_role(guild, user_id, team_emojis):
    try:
        user = await guild.fetch_member(user_id)
    except:
        # Handle the case where the member is not found or an error occurs
        print(f"Member with ID {user_id} not found.")
        return None

    if user and not user.bot:
        # Iterate through the roles and return the first one with a unicode emoji
        highest_val = 0
        for role in user.roles:
            if  role.position > highest_val and role.name not in logic.nonRoles:
                highest_val = role.position
                team_name = role.name

        print(team_name)

        highest_similarity = 0
        for team in team_emojis.keys():
            print(team)
            similarity = logic.check_similarity(team_name.lower(), team.split(" ")[0].lower())
            print(similarity)
            if similarity > highest_similarity:
                curr_emoji = team_emojis.get(team)
                print(curr_emoji)
                highest_similarity = similarity

        # Return an empty string if no role with a unicode emoji is found
        
        print(curr_emoji)
        return curr_emoji
    else:
        # Return None if the user is not found or is a bot
        return None

# Example usage
async def get_user_primary_role(user_id, guild, team_emojis):

    if user_id is None:
        return None

    # Find the specific guild by ID
    if not guild:
        print(f"Guild was not found.")
        return None

    primary_role = await fetch_user_primary_role(guild, int(user_id), team_emojis)
    if primary_role is not None:
        return primary_role


async def total_leaderboard_message(user_scores, guild):
    username_to_id = file_functions.read_file(logic.all_users)
    team_emojis = file_functions.read_file(logic.team_emojis_file)
    message_parts = []
    sorted_user_score = sort_user_scores(user_scores)
    message_parts.append("Totale poeng:")
    for rank, (username, score) in enumerate(sorted_user_score, start=1):
        user_id = username_to_id.get(username)
        if user_id is not None:
            user_id = user_id.strip('<@!>')
        role = await get_user_primary_role(user_id, guild, team_emojis)
        if role == None:   
            role = ""
        message_parts.append(f"{rank}. {role}{username}: {score}p")

    return '\n'.join(message_parts)