from datetime import datetime, timedelta
from perms import API_TOKEN
import requests

def get_matches(x_days):

    today_date = datetime.now().strftime("%Y-%m-%d")
    new_date = datetime.now() + timedelta(days=x_days)
    formatted_new_date = new_date.strftime("%Y-%m-%d")  

    api_url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_TOKEN # Be cautious with your API key
    }
    query_fixtures = {
        "league": "103",
        "season": "2025",
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
        for match in match_details:
            print(f"Date: {match['date']}, Home Team: {match['home_team']}, Away Team: {match['away_team']}, "
            f"Round: {match['round']}, Match ID: {match['match_id']}, Status: {match['status']}")
        return match_details
    



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

    print(f"Home team: {home_team}\n")
    print(f"Away team: {away_team}\n")
    print(f"Result: {result}\n")

    return result, home_team, away_team



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

    print(f"Result: {result}\n")
    print("Home team: " + home_team + "\n")
    print("Away team: " + away_team + "\n")
    return result, home_team, away_team




