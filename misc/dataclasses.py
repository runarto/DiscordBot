from dataclasses import dataclass
from typing import Optional, Dict
from sqlite3 import Row

def row_to_dataclass(row: Row, dataclass_type: type):
    return dataclass_type(**dict(row))

@dataclass
class League:
    league_id: int
    name: str
    season: int

@dataclass
class Match:
    match_id: int
    message_id: int
    home_team: str
    away_team: str
    kick_off_time: str
    cancelled: bool
    league_id: int
    
@dataclass 
class Result:
    match_id: int
    home_team: str
    away_team: str
    status: Dict[str, str]
    result: Optional[str]

@dataclass
class Prediction:
    message_id: int
    user_id: str
    prediction: str

@dataclass
class Score:
    user_id: str
    league_id: int
    points: int = 0
    weekly_wins: int = 0

@dataclass
class User:
    user_id: str
    user_name: str
    user_display_name: str
    user_emoji: Optional[str] = None

@dataclass
class TeamEmoji:
    role_name: str
    emoji: str

@dataclass
class Team:
    team_name: str
    league_id: int
    team_emoji: str
