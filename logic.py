from perms import API_TOKEN
from difflib import SequenceMatcher
import file_functions
import perms
import API
from datetime import datetime


def check_similarity(input1, input2):
    return SequenceMatcher(None, input1, input2).ratio()

async def map_emojis_to_teams(bot, teams):

    file_functions.write_file(team_emojis_file, {})

    guild = bot.get_guild(perms.guild_id)
    if not guild:
        print(f"Guild with ID {perms.guild_id} not found.")
        return

    team_emoji_mappings = {}

    for team in teams:

        best_match = None
        highest_ratio = 0
        team_split = team.split(" ")[0]

        for emoji in guild.emojis:
            similarity = check_similarity(emoji.name.lower(), team_split.lower())

            if similarity > highest_ratio:
                highest_ratio = similarity
                best_match = emoji

        if best_match:
            team_emoji_mappings[f"{team}"] = f"<:{best_match.name}:{best_match.id}>"
    
    file_functions.write_file(team_emojis_file, team_emoji_mappings)
    

    
    

    return team_emoji_mappings

def format_match_message(fixture, emoji_data):
    home_team = fixture['home_team']
    away_team = fixture['away_team']

    home_team_emoji = emoji_data.get(home_team)
    if home_team_emoji is None:
        home_team_emoji = '🏠'  # Replace 'Default Emoji' with your default emoji

    away_team_emoji = emoji_data.get(away_team)
    if away_team_emoji is None:
        away_team_emoji = '✈️'  # Replace 'Default Emoji' with your default emoji

    if fixture['home_team'] in teams_norske_navn:
        home_team = teams_norske_navn[fixture['home_team']]

    if fixture['away_team'] in teams_norske_navn:
        away_team = teams_norske_navn[fixture['away_team']]

    if home_team_emoji == '🏠' or away_team_emoji == '✈️': 
        message_content = f"{home_team} vs {away_team}"
    else:
        message_content = f"{home_team_emoji} {home_team} vs {away_team} {away_team_emoji}"

    return message_content, home_team_emoji, away_team_emoji

def split_message(message):
    split_messages = []
    current_message = ""
    for char in message:
        current_message += char
        if len(current_message) >= MAX_MESSAGE_LENGTH:
            # Find the last newline character before reaching the character limit
            last_newline_index = current_message.rfind('\n', 0, MAX_MESSAGE_LENGTH)
            if last_newline_index != -1:
                split_messages.append(current_message[:last_newline_index+1])
                current_message = current_message[last_newline_index+1:]
            else:
                # If no newline is found within the limit, split at the character limit
                split_messages.append(current_message)
                current_message = ""
    if current_message:
        split_messages.append(current_message)
    return split_messages

def check_if_valid_server(server_id):
    if server_id == perms.guild_id:
        return True
    else:
        return False

#get_matches(0)


def get_day_hour_minute(days):

    day_of_week = []
    hour = []
    minute = []
    data = API.get_matches(days)
    message_id_and_match_id = file_functions.read_file(tracked_messages)
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