from datetime import datetime, timedelta
import requests
from api.api_utils import generate_headers, validate
from typing import List

def get_fixture(auth: str, fixture_id: int) -> List[dict]:
    """https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures"""
    
    """
        Fetches a specific fixture by its ID.
    """
    
    url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
    headers = generate_headers(auth)

    query = {
        "timezone": "Europe/Oslo"
    }
    
    return validate(requests.get(url, headers=headers, params=query))


def get_teams(auth: str) -> List[dict]:     
    """https://www.api-football.com/documentation-v3#tag/Teams/operation/get-teams"""

    """
        Fetches teams from the API.
    """
    
    url = "https://v3.football.api-sports.io/teams"
    headers = generate_headers(auth)

    query = {
        "league": 103,
        "season": 2025,
    }
    
    return validate(requests.get(url, headers=headers, params=query))

def get_fixtures(auth: str, x_days: int) -> List[dict]:
    """https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures"""
    
    """
        Fetches match fixtures for the next x_days from the API.
    """

    today_date = datetime.now().strftime("%Y-%m-%d")
    new_date = datetime.now() + timedelta(days=x_days)
    formatted_new_date = new_date.strftime("%Y-%m-%d")  

    url = "https://v3.football.api-sports.io/fixtures"
    headers = generate_headers(auth)

    query = {
        "league": 103,
        "season": 2025,
        "timezone": "Europe/Oslo",
        "from": today_date,
        "to": formatted_new_date 
    }
    
    return validate(requests.get(url, headers=headers, params=query))


def get_fixture_result(auth: str, match_id: int) -> List[dict]:
    """https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures"""
    
    """
        Fetches result for a specific match-id.
    """

    query = {
        "status": "FT"
    }

    url = f"https://v3.football.api-sports.io/fixtures?{match_id}"
    headers = generate_headers(auth)

    return validate(requests.get(url, headers=headers, params=query))


