from datetime import datetime, timedelta
import requests

def generate_headers(API_TOKEN: str):
    return {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_TOKEN  # Be cautious with your API key
    }

def validate(response: requests.Response):
    return response.raise_for_status() 

def get_matches(auth: str, x_days: int):
    """https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures"""
    
    """
        Fetches match fixtures for the next x_days from the API.
    """

    today_date = datetime.now().strftime("%Y-%m-%d")
    new_date = datetime.now() + timedelta(days=x_days)
    formatted_new_date = new_date.strftime("%Y-%m-%d")  

    url = "https://v3.football.api-sports.io/fixtures"
    headers = generate_headers(auth)

    query_fixtures = {
        "league": "103",
        "season": "2025",
        "timezone": "Europe/Oslo",
        "from": today_date,
        "to": formatted_new_date 
    }
    
    return requests.get(url, headers=headers, params=query_fixtures).json()


def get_match_results(auth: str, match_id: int):
    """https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures"""
    
    """
        Fetches result for a specific match-id.
    """

    url = f"https://v3.football.api-sports.io/fixtures?{match_id}"
    headers = generate_headers(auth)

    return validate(requests.get(url, headers=headers)).json()
    


        






