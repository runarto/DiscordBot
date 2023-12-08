import requests
from datetime import timedelta, datetime
import pytz  # This library is used for time zone conversions
from perms import API_TOKEN
from dateutil import parser



emoji_dictionary = {
    "Bodo/Glimt": "<:Glimt:1039831920978169857>",
    "Ham-Kam": "<:Hamkam:1039832337032163358>",
    "Aston Villa": ":brannbad:819294515755745281:",
    "Rosenborg": "<:Rosenborg:1059898578883051561>",
    "Lillestrom": "<:Lillestroem:1039835160125902908>",
    "Tromso": "<:Tromsoe:1039842401025527868>",
    "Viking": "<:Viking:1039842907894599760>",
    "Valerenga": "<:Vaalerenga:1039843306043080735>",
    "Sandefjord": "<:Sandefjord:1039840813544378418>",
    "Stromsgodset": "<:Stroemsgodset:1039841950079143937>",
    "ODD Ballklubb": "<:Odd:1039839692373368872>",
    "Molde": "<:Molde:1039836329502052444>",
    "Stabaek": "<:Stabaek:1039844256304595014>",
    "Sarpsborg 08 FF": "<:Sarpsborg:1039841407134867516>",
    "Haugesund": "<:Haugesund:1039832977158443058>",
    "Aalesund": "<:Aalesund:1039831454353457254>"
}

emoji_list = [
    "<:Glimt:1039831920978169857>",
    "<:Hamkam:1039832337032163358>",
    "<:Brann:1039844066487185429>",
    "<:Rosenborg:1059898578883051561>",
    "<:Lillestroem:1039835160125902908>",
    "<:Tromsoe:1039842401025527868>",
    "<:Viking:1039842907894599760>",
    "<:Vaalerenga:1039843306043080735>",
    "<:Sandefjord:1039840813544378418>",
    "<:Stroemsgodset:1039841950079143937>",
    "<:Odd:1039839692373368872>",
    "<:Molde:1039836329502052444>",
    "<:Stabaek:1039844256304595014>",
    "<:Sarpsborg:1039841407134867516>",
    "<:Haugesund:1039832977158443058>",
    "<:Aalesund:1039831454353457254>"
]

user_scores = "user_scores.json"
tracked_messages = {}
predictions_file = 'input_predictions.json'
output_predictions_file = 'output_predictions.json'


#Returnerer hvilken runde det er. Overflødig funksjon. 

def get_round():
    api_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/rounds"
    headers = {
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    query_round = {
        "league": "39",
        "season": "2023"
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

    api_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    query_fixtures = {
        "league": "39",
        "season": "2023",
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
                'match_id': fixture['fixture']['id']
            }
            #if current_round == match_info['round']:
            match_details.append(match_info)
        return match_details
    

#get_match_results() blir kalt 7 dager etter get_matches()

#Returnerer resultater for kamper de siste sju dagene. 

def get_match_results(x_days):

    today_date = datetime.now().strftime("%Y-%m-%d")

    new_date = datetime.now() + timedelta(days=x_days)
    formatted_new_date = new_date.strftime("%Y-%m-%d")  


    api_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    params = {
        'league': 39,
        'season': 2023,
        'from': formatted_new_date,
        'to': today_date,
        'status': 'FT' 
    }

    response = requests.get(api_url, headers=headers, params=params)
    data = response.json()

    results = {}
    for fixture in data['response']:
        home_win = fixture['teams']['home']['winner']

        if home_win is True:
            result = True  # Home win
        elif home_win is False:
            result = False  # Away win
        else:
            result = None  # Draw or data not available

        message = f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"

        results[message] = result

        

    return dict(sorted(results.items()))



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


def check_time(reaction):
    message_content = reaction.message.content
    datetime_str = message_content.split('\n')[0].strip()
    
    # Parse the datetime string into a datetime object
    match_start = parser.isoparse(datetime_str)

    # Check if current time is before the match start time
    if datetime.datetime.now(datetime.timezone.utc) < match_start:
        return True
    else:
        return False



