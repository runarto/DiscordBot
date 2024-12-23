import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logic
import file_functions
import perms
import API

channel_id = perms.CHANNEL_ID #Kanalen hvor kupongen sendes
import traceback


async def update_user_scores():
    try:
        
        predictions = file_functions.read_file(logic.predictions_file) #{message_id, [data]}
        print("predictions fetched\n")

        if not predictions:
            return {}, [], 0

        team_emojis = file_functions.read_file(logic.team_emojis_file)
        print("emojis fetched\n")

        # Sort the order_tuple based on match_id
        order_tuple = file_functions.read_file(logic.tracked_messages) #[message-id, match-id]
        message_id_match_id_dict = dict(order_tuple) #message_match_dict[message_id] = match_id
        print("message-match\n")

        num_of_games = 0
        user_scores = file_functions.read_file(logic.user_scores) #Total poengsum all-time
        this_week_user_score = []  #Ukens poeng

        for message_id, reactions_data in predictions.items():
            match_id = message_id_match_id_dict.get(message_id)
            print(f"{match_id}\n")
            actual_result, home_team, away_team = await API.get_match_results(match_id)
            if actual_result == "No result":
                continue

            num_of_games += 1
            home_team_emoji = team_emojis.get(home_team, "🏠")
            away_team_emoji = team_emojis.get(away_team, "✈️")

            actual_result = home_team_emoji if actual_result is True else (away_team_emoji if actual_result is False else "\U0001F1FA")

            for reaction, users in reactions_data.items():
                for user_id in users:
                    user_prediction = reaction

                    if user_prediction == actual_result:
                        if user_id not in user_scores:
                            user_scores[user_id] = 0
                        user_scores[user_id] += 1

                        user_score_entry = next((item for item in this_week_user_score if item['user_id'] == user_id), None)
                        if not user_score_entry:
                            user_score_entry = {'user_id': user_id, 'points': 0}
                            this_week_user_score.append(user_score_entry)

                        user_score_entry['points'] += 1


        return user_scores, this_week_user_score, num_of_games

    except (FileNotFoundError, KeyError, TypeError) as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

        # Return empty data or handle the error as needed
        return {}, [], 0
    



#Sorterer 

def sort_user_scores(user_scores, weekly_winners):
    if user_scores is None:
        return

    # Check if user_scores is a dictionary
    if isinstance(user_scores, dict):
        # Sorting the dictionary by its values (scores) in descending order
        return sorted(
        user_scores.items(),
        key=lambda item: (item[1], weekly_winners.get(item[0].strip('<@!>'), 0)),
        reverse=True
    )

    # Check if user_scores is a list of dictionaries
    elif isinstance(user_scores, list):
        # Sorting the list of dictionaries by 'points' in each dictionary in descending order
        sorted_scores = sorted(user_scores, key=lambda x: x['points'], reverse=True)
        return sorted_scores

    # Return an empty list if user_scores is neither a dict nor a list of dicts
    return []


async def format_leaderboard_message(guild):
    
    user_scores, this_week_user_scores, num_of_games = await update_user_scores()
    print("scores fetched\n")

    team_emojis = file_functions.read_file(logic.team_emojis_file)
    weekly_winners = file_functions.read_file("jsonfiles/weekly_winners.json")
    
    if not user_scores or not this_week_user_scores:
        return

    message_parts = []

    if this_week_user_scores: # Check if there were any games this prior week. 
        scores_this_week = sort_user_scores(this_week_user_scores, None)
        points_to_users = await get_user_nicknames(scores_this_week, guild)
        message_parts = format_message(points_to_users, num_of_games)

        # Check for and announce the weekly winner
        if scores_this_week:
            # Find the highest score
            highest_score = scores_this_week[0]['points']

            # Find all users who have achieved the highest score
            weekly_winners, winners = get_weekly_winners(weekly_winners, scores_this_week, highest_score)

            # Format the congratulatory message
            winner_message = format_winner_message(winners)
            message_parts.append(winner_message)

    if user_scores:
        # Sort user scores with weekly wins as a tiebreaker
        sorted_user_score = sort_user_scores(user_scores, weekly_winners)
        message_parts.append("Totale poeng:")
        
        current_rank = 0  # Initialize rank separately
        previous_score = None
        previous_weekly_wins = None

        for index, (user_id, score) in enumerate(sorted_user_score, start=1):
            try:
                if user_id is not None:
                    user_id = user_id.strip('<@!>')

                # Fetch role and nickname
                role = await get_primary_role_for_user(user_id, guild, team_emojis)
                if role is None:
                    role = ""

                user_nick = await guild.fetch_member(int(user_id))
                weekly_win_count = weekly_winners.get(user_id, 0)

                # Determine rank only for valid users
                if score != previous_score or weekly_win_count != previous_weekly_wins:
                    current_rank += 1

                # Append to message parts
                if user_id in weekly_winners:
                    message_parts.append(f"{current_rank}. {role}{user_nick.display_name}: {score}p (us: {weekly_win_count})")
                else:
                    message_parts.append(f"{current_rank}. {role}{user_nick.display_name}: {score}p")

                # Update previous values
                previous_score = score
                previous_weekly_wins = weekly_win_count

            except discord.NotFound:
                print(f"Member with user_id: {user_id} not found in guild: {guild.name} (ID: {guild.id}), skipping.")
                continue

            
            

        file_functions.write_file(logic.user_scores, user_scores)
        file_functions.write_file("jsonfiles/weekly_winners.json", weekly_winners)

    return '\n'.join(message_parts)


async def get_user_nicknames(user_scores, guild):
    points_to_users = {}
    for user in user_scores:
        try:
            points = user['points']
            if points not in points_to_users:
                points_to_users[points] = []
            user_id = user['user_id'].strip('<@!>')
            user_nick = await guild.fetch_member(int(user_id))
            points_to_users[points].append(user_nick.display_name)
        except discord.NotFound:
            print(f"Member with user_id: {user_id} not found in guild: {guild.name} (ID: {guild.id}), skipping.")
            continue
    return points_to_users

def format_message(points_to_users, num_of_games):
    message_parts = [f"**Av {num_of_games} mulige:**"]
    for points, users in sorted(points_to_users.items(), reverse=True):
        names = ', '.join(users)
        message_parts.append(f"{points} poeng: {names}")
    return message_parts

def format_winner_message(winners):
    if len(winners) > 1:
        winners_formatted = ', '.join(winners[:-1]) + " og " + winners[-1]
        return f"Gratulerer til ukas vinnere {winners_formatted}!\n"
    else:
        return f"Gratulerer til ukas vinner {winners[0]}!\n"

def get_weekly_winners(weekly_winners, sorted_this_week_user_scores, highest_score):
    winners = [user['user_id'] for user in sorted_this_week_user_scores if user['points'] == highest_score]
    for winner in winners:
        user_id = winner.strip('<@!>')
        if user_id in weekly_winners:
            weekly_winners[user_id] += 1
        else:
            weekly_winners[user_id] = 1

    return weekly_winners, winners




async def store_predictions(message_id, channel, bot):

    message_id = str(message_id)

    try:
        current_reactions = await fetch_reactions_from_message(message_id, channel, bot)
        file_functions.store_predictions(logic.predictions_file, message_id, current_reactions)
        return
    except discord.NotFound:
        print("Message or channel not found.")
        return
    except discord.Forbidden:
        print("Missing permissions to read the message or channel.")
        return
    except discord.HTTPException as e:
        print(f"HTTP exception occurred: {e}")



async def fetch_reactions_from_message(message_id, channel, bot):
    try:
        if channel is None:
            print("Channel not found. Unable to proceed.")
            return {}

        print(f"Attempting to fetch message with ID: {message_id} from channel: {channel.name}")
        message = await channel.fetch_message(message_id)
        print(f"Message fetched: {message.id} - Content: {message.content}")

        reactions_data = {}
        global_mentions = set()  # Track all user mentions globally

        print(f"Starting to process reactions for message ID: {message_id}")

        for reaction in message.reactions:
            print(f"Processing reaction: {reaction.emoji} - Count: {reaction.count}")

            user_mentions = set()  # Track user mentions for this reaction
            print(f"Fetching users for reaction: {reaction.emoji}")

            users = [user async for user in reaction.users()]
            print(f"Fetched {len(users)} users for reaction: {reaction.emoji}")

            for user in users:
                if user and bot.user and user.id != bot.user.id and user.mention not in global_mentions:
                    user_mentions.add(user.mention)
                    global_mentions.add(user.mention)  # Add to global tracker
                    print(f"Added user mention: {user.mention} for reaction: {reaction.emoji}")

            reactions_data[str(reaction.emoji)] = list(user_mentions)  # Convert set back to list
            print(f"Collected {len(user_mentions)} unique user(s) for reaction: {reaction.emoji}")

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

    


async def fetch_primary_role_for_user(guild, user_id, team_emojis):
    try:
        user = await guild.fetch_member(user_id)
    except discord.NotFound:
        print(f"Member with user_id: {user_id} not found in guild: {guild.name} (ID: {guild.id}), skipping.")
        return None

    if user and not user.bot:
        # Iterate through the roles and return the first one with a unicode emoji
        highest_val = 0
        for role in user.roles:
            if (role.position > highest_val) and (role.name not in logic.nonRoles) and (role.position <= logic.MAX_ROLE_VALUE):
                highest_val = role.position
                team_name = role.name

        highest_similarity = 0
        for team in team_emojis.keys():
            similarity = logic.check_similarity(team_name.lower(), team.split(" ")[0].lower())
            if similarity > highest_similarity:
                curr_emoji = team_emojis.get(team)
                highest_similarity = similarity

        # Return an empty string if no role with a unicode emoji is found
        if curr_emoji is not None:
            return curr_emoji
    else:
        # Return None if the user is not found or is a bot
        return None

# Example usage
async def get_primary_role_for_user(user_id, guild, team_emojis):

    if user_id is None:
        return None

    # Find the specific guild by ID
    if not guild:
        print(f"Guild was not found.")
        return None
    
    if user_id == str(696084965875646465):
        print(f"User: {user_id}, emoji: <:Odd:1039839692373368872>")
        return "<:Odd:1039839692373368872>"

    primary_role = await fetch_primary_role_for_user(guild, user_id, team_emojis)
    if primary_role is not None:
        print(f"User: {user_id}, emoji: {primary_role}")
        return primary_role
    
    return None


async def total_leaderboard_message(user_scores, guild):
    username_to_id = file_functions.read_file(logic.all_users)
    team_emojis = file_functions.read_file(logic.team_emojis_file)
    weekly_winners = file_functions.read_file("jsonfiles/weekly_winners.json")
    message_parts = []
    sorted_user_score = sort_user_scores(user_scores, weekly_winners)
    message_parts.append("Totale poeng:")
    for rank, (username, score) in enumerate(sorted_user_score, start=1):
        user_id = username_to_id.get(username)
        if user_id is not None:
            user_id = user_id.strip('<@!>')
        role = await get_primary_role_for_user(user_id, guild, team_emojis)
        if role == None:   
            role = ""
        message_parts.append(f"{rank}. {role}{username}: {score}p")
        if user_id in weekly_winners:
            message_parts.append(f"(us: {weekly_winners[username]})")

    return '\n'.join(message_parts)