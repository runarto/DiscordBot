import sqlite3
from db.db_create import create_matches_table, create_users_table, create_predictions_table, create_scores_table
import db.db_read_write as db_rw

class DB:
    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path)
        self.create()

    def create(self):
        create_predictions_table(self._conn)
        create_matches_table(self._conn)
        create_scores_table(self._conn)
        create_users_table(self._conn)

    def insert_match(self, match_id, home_team, away_team, kick_off_time):
        db_rw.insert_match(self._conn, match_id, home_team, away_team, kick_off_time)

    def get_all_matches(self):
        return db_rw.get_all_matches(self._conn)

    def get_match_by_id(self, match_id):
        return db_rw.get_match_by_id(self._conn, match_id)
    
    def insert_prediction(self, match_id, user_id, prediction):
        db_rw.insert_prediction(self._conn, match_id, user_id, prediction)
    
    def get_predictions_for_user(self, user_id):
        return db_rw.get_predictions_for_user(self._conn, user_id)
    
    def get_prediction(self, match_id, user_id):
        return db_rw.get_prediction(self._conn, match_id, user_id)

    def get_all_predictions_for_match(self, match_id):
        return db_rw.get_all_predictions_for_match(self._conn, match_id)
    
    def upsert_score(self, user_id, points_delta=0, win_delta=0):
        db_rw.upsert_score(self._conn, user_id, points_delta, win_delta)

    def get_user_score(self, user_id):
        return db_rw.get_user_score(self._conn, user_id)
    
    def get_all_scores(self):
        return db_rw.get_all_scores(self._conn)
    
    def insert_user(self, user_id: int, user_name: str, user_emoji: str = None):
        db_rw.insert_user(self._conn, user_id, user_name, user_emoji)

    def get_team_emojis(self):
        return db_rw.get_team_emojis(self._conn)
    
    def insert_team_emoji(self, team_name, emoji):
        db_rw.insert_team_emoji(self._conn, team_name, emoji)
    
    def close(self):
        self._conn.close()

    

    

    

