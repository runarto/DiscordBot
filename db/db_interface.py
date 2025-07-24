import sqlite3
from db.db_create import (
    create_matches_table,
    create_users_table,
    create_predictions_table,
    create_scores_table,
    create_team_emojis_table,
    create_teams_table,
)
import db.db_read_write as db_rw
from misc.dataclasses import Match, Prediction, Score, User, TeamEmoji, Team, row_to_dataclass



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

    def insert_match(self, match_id, message_id, home_team, away_team, kick_off_time):
        db_rw.insert_match(self._conn, match_id, message_id, home_team, away_team, kick_off_time)

    def get_all_matches(self):
        rows = db_rw.get_all_matches(self._conn)
        return [row_to_dataclass(row, Match) for row in rows]

    def get_match_by_id(self, match_id):
        row = db_rw.get_match_by_id(self._conn, match_id)
        return row_to_dataclass(row, Match) if row else None

    def insert_prediction(self, match_id, user_id, prediction):
        db_rw.insert_prediction(self._conn, match_id, user_id, prediction)

    def get_predictions_for_user(self, user_id):
        rows = db_rw.get_predictions_for_user(self._conn, user_id)
        return [row_to_dataclass(row, Prediction) for row in rows]

    def get_prediction(self, match_id, user_id):
        row = db_rw.get_prediction(self._conn, match_id, user_id)
        return row_to_dataclass(row, Prediction) if row else None

    def get_all_predictions_for_match(self, match_id):
        rows = db_rw.get_all_predictions_for_match(self._conn, match_id)
        return [row_to_dataclass(row, Prediction) for row in rows]

    def upsert_score(self, user_id, points_delta=0, win_delta=0):
        db_rw.upsert_score(self._conn, user_id, points_delta, win_delta)

    def get_user_score(self, user_id):
        row = db_rw.get_user_score(self._conn, user_id)
        return row_to_dataclass(row, Score) if row else None

    def get_all_scores(self):
        rows = db_rw.get_all_scores(self._conn)
        return [row_to_dataclass(row, Score) for row in rows]

    def insert_user(self, user_id: int, user_name: str, user_display_name: str, user_emoji: str = None):
        db_rw.insert_user(self._conn, user_id, user_name, user_display_name, user_emoji)

    def get_user(self, user_id):
        row = db_rw.get_user(self._conn, user_id)
        return row_to_dataclass(row, User) if row else None
    
    def get_all_users(self):
        rows = db_rw.get_all_users(self._conn)
        return [row_to_dataclass(row, User) for row in rows]

    def get_team_emojis(self):
        rows = db_rw.get_team_emojis(self._conn)
        return [row_to_dataclass(row, TeamEmoji) for row in rows]

    def insert_team_emoji(self, role_name, emoji):
        db_rw.insert_team_emoji(self._conn, role_name, emoji)

    def delete_team_emoji(self, role_name):
        with self._conn:
            self._conn.execute("DELETE FROM team_emojis WHERE role_name = ?;", (role_name,))

    def insert_team(self, team_name_api, team_name_norsk, team_emoji):
        db_rw.insert_team(self._conn, team_name_api, team_name_norsk, team_emoji)

    def get_team(self, team_name_api):
        row = db_rw.get_team(self._conn, team_name_api)
        return row_to_dataclass(row, Team) if row else None
    
    def drop_table(self, table_name: str):
        with self._conn:
            self._conn.execute(f"DROP TABLE IF EXISTS {table_name};")

    def flush_table(self, table_name: str):
        with self._conn:
            self._conn.execute(f"DELETE FROM {table_name};")
            self._conn.commit()


    def close(self):
        self._conn.close()
