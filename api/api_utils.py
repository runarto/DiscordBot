import requests
from typing import List

def generate_headers(API_TOKEN: str) -> dict:
    return {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": API_TOKEN  # Be cautious with your API key
    }

def validate(response: requests.Response) -> List[dict]:
    response.raise_for_status() 
    return response.json()  # or whatever is appropriate

