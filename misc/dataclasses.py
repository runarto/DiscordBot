from dataclasses import dataclass
from typing import Optional
from sqlite3 import Row

def row_to_dataclass(row: Row, dataclass_type: type):
    return dataclass_type(**dict(row))

@dataclass
class Match:
    match_id: int
    message_id: int
    home_team: str
    away_team: str
    kick_off_time: str

@dataclass
class Prediction:
    message_id: int
    user_id: str
    prediction: str

@dataclass
class Score:
    user_id: str
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
    team_name_api: str
    team_name_norsk: str
    team_emoji: str
