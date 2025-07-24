

def create_matches_table(conn):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            kick_off_time TEXT NOT NULL
        );
        """)

def create_predictions_table(conn):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            match_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            prediction TEXT NOT NULL,
            PRIMARY KEY (match_id, user_id),
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        );
        """)

def create_scores_table(conn):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user_id TEXT PRIMARY KEY,
            points INTEGER NOT NULL DEFAULT 0,
            weekly_wins INTEGER NOT NULL DEFAULT 0
        );
        """)

def create_users_table(conn):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            user_name TEXT NOT NULL,
            user_emoji TEXT
        );
        """)

def create_team_emojis_table(conn):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS team_emojis (
            role_name TEXT PRIMARY KEY,
            emoji TEXT NOT NULL
        );
        """)

def create_teams_table(conn):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_name_api TEXT PRIMARY KEY,
            team_name_norsk TEXT NOT NULL,
            team_emoji TEXT NOT NULL
        );
        """)
