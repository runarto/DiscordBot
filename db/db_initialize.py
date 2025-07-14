import sqlite3
from db.db_create import create_matches_table, create_users_table, create_predictions_table, create_scores_table

class DB:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)

    def init_db(self):
        self.create_tables()

    def create_tables(self):
        create_predictions_table(self.conn)
        create_matches_table(self.conn)
        create_scores_table(self.conn)
        create_users_table(self.conn)

    

    

    

