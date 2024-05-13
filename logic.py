from perms import API_TOKEN
import requests
import pytz
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import file_functions
import perms

nonRoles = ["Sørveradministrator", "bot-fikler", "Norges Fotballforbund", "Tippekuppongmester"]
MAX_MESSAGE_LENGTH = 2000



teams = [
    "Kristiansund BK",
    "Tromso", 
    "Brann",
    "Sarpsborg 08 FF",
    "Viking",
    "Bodo/Glimt",
    "ODD Ballklubb",
    "Haugesund",
    "Sandefjord",
    "Rosenborg",
    "Stromsgodset",
    "Ham-Kam",
    "Lillestrom",
    "KFUM Oslo",
    "Fredrikstad",
    "Molde",
    "Moss",
    "Kongsvinger",
    "Bryne",
    "Raufoss",
    "Ranheim",
    "jerv",
    "Skeid",
    "Stabaek",
    "Sogndal",
    "Valerenga",
    "Start",
    "Aalesund",
    "Sandnes ULF",
    "Asane",
    "Lyn Fotball",
    "Hei"
]

teams_norske_navn = {
    "Kristiansund BK": "Kristiansund",
    "Tromso": "Tromsø",
    "Brann": "Brann",
    "Sarpsborg 08 FF": "Sarpsborg 08",
    "Viking": "Viking",
    "Bodo/Glimt": "Bodø/Glimt", #5/10
    "ODD Ballklubb": "Odd", #3/3
    "Haugesund": "Haugesund", #9/9
    "Sandefjord": "Sandefjord", #10/10
    "Rosenborg": "Rosenborg", #9/9
    "Stromsgodset": "Strømsgodset", #11/13
    "Ham-Kam": "Ham-Kam", #6/7
    "Lillestrom": "Lillestrøm",# > 9/11
    "KFUM Oslo": "KFUM", #4/4
    "Fredrikstad": "Fredrikstad", #11/11
    "Molde": "Molde", #5/5
    "Moss": "Moss",
    "Kongsvinger": "Kongsvinger",
    "Bryne": "Bryne",
    "Raufoss": "Raufoss",
    "Ranheim": "Ranheim",
    "jerv": "Jerv",
    "Skeid": "Skeid",
    "Stabaek": "Stabæk",
    "Sogndal": "Sogndal",
    "Valerenga": "Vålerenga",
    "Start": "Start",
    "Aalesund": "Aalesund",
    "Sandnes ULF": "Sandnes Ulf",
    "Asane": "Åsane"
}

team_emoji_id = [
    "<:Brann:1039844066487185429>",
    "<:Glimt:1039831920978169857>",
    "<:Fredrikstad:1039945582917210162>",
    "<:Kristiansund:1039834384854941726>",
    "<:Lillestroem:1039835160125902908>",
    "<:Odd:1039839692373368872>",
    "<:Tromsoe:1039842401025527868>",
    "<:Rosenborg:1059898578883051561>",
    "<:Hamkam:1039832337032163358>",
    "<:Molde:1039836329502052444>",
    "<:KFUM:1039945755814805574>",
    "<:Stroemsgodset:1039841950079143937>",
    "<:Viking:1039842907894599760>",
    "<:Sandefjord:1039840813544378418>",
    "<:Haugesund:1039832977158443058>"
]


user_scores = "jsonfiles/user_scores.json"
tracked_messages = "jsonfiles/match_messages.json"
predictions_file = 'jsonfiles/input_predictions.json'
output_predictions_file = 'jsonfiles/output_predictions.json'
team_emojis_file = "jsonfiles/team_emoji_map.json"
all_users = "jsonfiles/all_users.json"


#Returnerer hvilken runde det er. Overflødig funksjon. 

def get_round():
    api_url = "https://v3.football.api-sports.io/fixtures/rounds"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    query_round = {
        "league": "103",
        "season": "2024"
    }
    response = requests.get(api_url, headers=headers, params=query_round)
    if response.status_code == 200:
        data = response.json()

        return data["response"][0]
    else:
        return None


#Returnerer kamp-detaljer for aktuelle kamper x dager frem i tid. 

def get_matches(x_days):
    today_date = datetime.now().strftime("%Y-%m-%d")

    new_date = datetime.now() + timedelta(days=x_days)
    formatted_new_date = new_date.strftime("%Y-%m-%d")  



    #Hver gang get_matches() kjører henter vi inn kamper som er fra denne dagen, og 7 dager frem i tid

    api_url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    query_fixtures = {
        "league": "103",
        "season": "2024",
        "timezone": "Europe/Oslo",
        "from": today_date,
        "to": formatted_new_date 
    }
    
    response = requests.get(api_url, headers=headers, params=query_fixtures)
    if response.status_code == 200:
        data = response.json()
        match_details = []
        for fixture in data['response']:
            match_info = {
                'date': fixture['fixture']['date'],
                'home_team': fixture['teams']['home']['name'],
                'away_team': fixture['teams']['away']['name'],
                'round': fixture['league']['round'],
                'match_id': fixture['fixture']['id'],
                'status': fixture['fixture']['status']['short']
            }
            #if current_round == match_info['round']:
            match_details.append(match_info)
        return match_details
    

#get_match_results() blir kalt 7 dager etter get_matches()

#Returnerer resultater for kamper de siste sju dagene. 
async def get_match_results(match_id):

    api_url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    params = {
        'id': match_id,
    }

    response = requests.get(api_url, headers=headers, params=params)
    data = response.json()

    for fixture in data['response']:
        print(fixture['fixture']['status']['short'])
        if fixture['fixture']['status']['short'] in ['FT', 'PEN', 'AET', 'AWD', 'WO']:
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            home_win = fixture['teams']['home']['winner']


            if home_win is True:
                result = True  # Home win
            elif home_win is False:
                result = False  # Away win
            else:
                result = None  # Draw
        elif fixture['fixture']['status']['short'] in ['CANC', 'ABD', 'PST', 'TBD']:
            return "Game never started"
        else:
            return "No result"

        #message = f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
    print(f"{result}\n")
    print(f"{home_team}\n")
    print(f"{away_team}\n")

    return result, home_team, away_team


#Overflødig. 

def fixture_status(match_details):
    # Define the UTC+1 time zone
    utc_plus_one = pytz.timezone('Etc/GMT-1')

    # Get the current time in UTC+1
    current_time_utc_plus_one = datetime.now(utc_plus_one)
    print(current_time_utc_plus_one)

    started_matches = []

    for match in match_details:
        # Parse the match date-time string
        match_time_utc = datetime.fromisoformat(match['date'])

        # Check if the current time is past the match time
        if current_time_utc_plus_one > match_time_utc:
            started_matches.append(match)

    return started_matches


#Bare for testing. 

def print_match_table(match_list):
    # Define the table headers
    headers = ['Date', 'Home Team', 'Away Team', 'Full-Time Score', 'Round']
    
    # Find the maximum length for each column
    column_lengths = [len(header) for header in headers]
    for match in match_list:
        column_lengths[0] = max(column_lengths[0], len(match['date']))
        column_lengths[1] = max(column_lengths[1], len(match['home_team']))
        column_lengths[2] = max(column_lengths[2], len(match['away_team']))
        column_lengths[3] = max(column_lengths[3], len(str(match['fulltime_score'])))
        column_lengths[4] = max(column_lengths[4], len(match['round']))

    # Print table header
    header_row = '|'.join(header.center(column_lengths[i]) for i, header in enumerate(headers))
    print(header_row)
    print('-' * len(header_row))  # Separator

    # Print each row of match data
    for match in match_list:
        row = '|'.join([
            match['date'].center(column_lengths[0]),
            match['home_team'].center(column_lengths[1]),
            match['away_team'].center(column_lengths[2]),
            str(match['fulltime_score']).center(column_lengths[3]),
            match['round'].center(column_lengths[4])
        ])
        print(row)



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



def FormatMatchMessge(fixture, emoji_data):
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

def get_match_results_non_async(match_id):

    api_url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    params = {
        'id': match_id,
    }

    response = requests.get(api_url, headers=headers, params=params)
    data = response.json()

    for fixture in data['response']:
        print(fixture['fixture']['status']['short'])
        if fixture['fixture']['status']['short'] in ['FT', 'PEN', 'AET', 'AWD', 'WO']:
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            home_win = fixture['teams']['home']['winner']


            if home_win is True:
                result = True  # Home win
            elif home_win is False:
                result = False  # Away win
            else:
                result = None  # Draw
        elif fixture['fixture']['status']['short'] in ['CANC', 'ABD', 'PST', 'TBD']:
            return "Game never started"
        else:
            return "No result"

        #message = f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
    print(f"{result}\n")
    print(f"{home_team}\n")
    print(f"{away_team}\n")

    return result, home_team, away_team


get_match_results_non_async(1164375)