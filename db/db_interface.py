import sqlite3
from db.db_create import (
    create_matches_table,
    create_users_table,
    create_predictions_table,
    create_scores_table,
    create_team_emojis_table,
    create_teams_table,
    create_historical_matches_table,
    create_bot_predictions_table,
)
import db.db_read_write as db_rw
from misc.dataclasses import Match, Prediction, Score, User, TeamEmoji, Team, row_to_dataclass
from typing import Union, List
import datetime



class DB:
    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.create()

    def create(self):
        create_predictions_table(self._conn)
        create_matches_table(self._conn)
        create_scores_table(self._conn)
        create_users_table(self._conn)
        create_team_emojis_table(self._conn)
        create_teams_table(self._conn)
        create_historical_matches_table(self._conn)
        create_bot_predictions_table(self._conn)

    def insert_match(self, match_id: Union[int, str], message_id: Union[int, str], home_team: str, away_team: str, kick_off_time: Union[str, datetime.datetime], league_id: int, cancelled: bool = False):
        db_rw.insert_match(self._conn, match_id, message_id, home_team, away_team, kick_off_time, league_id, cancelled)

    def get_all_matches(self) -> List[Match]:
        rows = db_rw.get_all_matches(self._conn)
        return [row_to_dataclass(row, Match) for row in rows]

    def get_matches_by_league(self, league_id: int) -> List[Match]:
        rows = db_rw.get_matches_by_league(self._conn, league_id)
        return [row_to_dataclass(row, Match) for row in rows]

    def get_match_by_id(self, match_id: Union[int, str] = None, message_id: Union[int, str] = None) -> Match:
        row = db_rw.get_match(self._conn, match_id, message_id)
        return row_to_dataclass(row, Match) if row else None

    def insert_prediction(self, message_id: Union[int, str], user_id: Union[int, str], prediction: str):
        db_rw.insert_prediction(self._conn, message_id, user_id, prediction)

    def get_predictions_for_user(self, user_id: Union[int, str]) -> List[Prediction]:
        rows = db_rw.get_predictions_for_user(self._conn, user_id)
        return [row_to_dataclass(row, Prediction) for row in rows]

    def get_prediction(self, message_id: Union[int, str], user_id: Union[int, str]) -> Prediction:
        row = db_rw.get_prediction(self._conn, message_id, user_id)
        return row_to_dataclass(row, Prediction) if row else None

    def get_all_predictions_for_match(self, message_id: Union[int, str]) -> List[Prediction]:
        rows = db_rw.get_all_predictions_for_match(self._conn, message_id)
        return [row_to_dataclass(row, Prediction) for row in rows]

    def upsert_score(self, user_id: Union[int, str], league_id: int, points_delta: int = 0, win_delta: int = 0):
        db_rw.upsert_score(self._conn, user_id, league_id, points_delta, win_delta)

    def get_user_score(self, user_id: Union[int, str], league_id: int) -> Score:
        row = db_rw.get_user_score(self._conn, user_id, league_id)
        return row_to_dataclass(row, Score) if row else None

    def get_all_scores(self) -> List[Score]:
        rows = db_rw.get_all_scores(self._conn)
        return [row_to_dataclass(row, Score) for row in rows]

    def get_scores_by_league(self, league_id: int) -> List[Score]:
        rows = db_rw.get_scores_by_league(self._conn, league_id)
        return [row_to_dataclass(row, Score) for row in rows]

    def insert_user(self, user_id: Union[int, str], user_name: Union[int, str], user_display_name: str, user_emoji: str = None):
        db_rw.insert_user(self._conn, user_id, user_name, user_display_name, user_emoji)

    def get_user(self, user_id: Union[int, str]) -> User:
        row = db_rw.get_user(self._conn, user_id)
        return row_to_dataclass(row, User) if row else None
    
    def get_all_users(self) -> List[User]:
        rows = db_rw.get_all_users(self._conn)
        return [row_to_dataclass(row, User) for row in rows]

    def get_team_emojis(self) -> List[TeamEmoji]:
        rows = db_rw.get_team_emojis(self._conn)
        return [row_to_dataclass(row, TeamEmoji) for row in rows]

    def insert_team_emoji(self, role_name: str, emoji: str):
        db_rw.insert_team_emoji(self._conn, role_name, emoji)

    def delete_team_emoji(self, role_name: str):
        with self._conn:
            self._conn.execute("DELETE FROM team_emojis WHERE role_name = ?;", (role_name,))

    def insert_team(self, team_name: str, league_id: int, team_emoji: str):
        db_rw.insert_team(self._conn, team_name, league_id, team_emoji)

    def get_team(self, team_name: str, league_id: int) -> Team:
        row = db_rw.get_team(self._conn, team_name, league_id)
        return row_to_dataclass(row, Team) if row else None

    def get_team_by_name(self, team_name: str) -> Team:
        row = db_rw.get_team_by_name(self._conn, team_name)
        return row_to_dataclass(row, Team) if row else None

    def get_teams_by_league(self, league_id: int) -> List[Team]:
        rows = db_rw.get_teams_by_league(self._conn, league_id)
        return [row_to_dataclass(row, Team) for row in rows]
    
    def drop_table(self, table_name: str):
        with self._conn:
            self._conn.execute(f"DROP TABLE IF EXISTS {table_name};")

    def flush_table(self, table_name: str):
        with self._conn:
            self._conn.execute(f"DELETE FROM {table_name};")
            self._conn.commit()

    def delete_matches_by_league(self, league_id: int):
        with self._conn:
            self._conn.execute("DELETE FROM matches WHERE league_id = ?;", (league_id,))
            self._conn.commit()

    def insert_historical_match(self, match_id: int, league_id: int, season: int,
                                 home_team: str, away_team: str, home_goals: int,
                                 away_goals: int, kick_off_time: str, page_url: str = None,
                                 replace: bool = False):
        db_rw.insert_historical_match(self._conn, match_id, league_id, season,
                                      home_team, away_team, home_goals, away_goals,
                                      kick_off_time, page_url, replace)

    def get_historical_matches(self) -> list:
        return db_rw.get_historical_matches(self._conn)

    def update_page_url(self, match_id: int, league_id: int, page_url: str) -> None:
        db_rw.update_page_url(self._conn, match_id, league_id, page_url)

    def get_all_eliteserien_matches_for_xg(self, league_id: int) -> list:
        return db_rw.get_all_eliteserien_matches_for_xg(self._conn, league_id)

    def reset_xg_for_league(self, league_id: int) -> None:
        db_rw.reset_xg_for_league(self._conn, league_id)

    def update_match_xg(self, match_id: int, league_id: int, home_xg: float, away_xg: float) -> None:
        db_rw.update_match_xg(self._conn, match_id, league_id, home_xg, away_xg)

    def has_historical_season(self, league_id: int, season: int) -> bool:
        return db_rw.has_historical_season(self._conn, league_id, season)

    def upsert_bot_prediction(self, match_id: int, league_id: int,
                               home_prob: float, draw_prob: float, away_prob: float, outcome: str) -> None:
        db_rw.upsert_bot_prediction(self._conn, match_id, league_id, home_prob, draw_prob, away_prob, outcome)

    def get_bot_prediction(self, match_id: int, league_id: int):
        return db_rw.get_bot_prediction(self._conn, match_id, league_id)

    def get_all_bot_predictions(self):
        return db_rw.get_all_bot_predictions(self._conn)

    def close(self):
        self._conn.close()
