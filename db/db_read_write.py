from sqlite3 import Connection
from typing import Optional

# --- Matches Read/Write ---

def insert_match(conn: Connection, match_id, message_id, home_team, away_team, kick_off_time):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO matches (match_id, message_id, home_team, away_team, kick_off_time)
            VALUES (?, ?, ?, ?, ?);
        """, (match_id, message_id, home_team, away_team, kick_off_time))

def get_all_matches(conn: Connection):
    return conn.execute("SELECT match_id, message_id, home_team, away_team, kick_off_time FROM matches ORDER BY kick_off_time;").fetchall()

def get_match(conn: Connection, match_id: Optional[int] = None, message_id: Optional[int] = None):
    if match_id and message_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time 
            FROM matches 
            WHERE match_id = ? AND message_id = ?;
        """
        return conn.execute(query, (match_id, message_id)).fetchone()
    elif match_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time 
            FROM matches 
            WHERE match_id = ?;
        """
        return conn.execute(query, (match_id,)).fetchone()
    elif message_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time 
            FROM matches 
            WHERE message_id = ?;
        """
        return conn.execute(query, (message_id,)).fetchone()
    else:
        raise ValueError("At least one of match_id or message_id must be provided.")


# --- Predictions Read/Write ---

def insert_prediction(conn: Connection, message_id, user_id, prediction):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO predictions (message_id, user_id, prediction)
            VALUES (?, ?, ?);
        """, (message_id, user_id, prediction))

def get_predictions_for_user(conn: Connection, user_id):
    return conn.execute("""
        SELECT message_id, user_id, prediction 
        FROM predictions 
        WHERE user_id = ?;
    """, (user_id,)).fetchall()

def get_prediction(conn: Connection, message_id, user_id):
    return conn.execute("""
        SELECT message_id, user_id, prediction 
        FROM predictions 
        WHERE message_id = ? AND user_id = ?;
    """, (message_id, user_id)).fetchone()

def get_all_predictions_for_match(conn: Connection, message_id):
    return conn.execute("""
        SELECT user_id, prediction 
        FROM predictions 
        WHERE message_id = ?;
    """, (message_id,)).fetchall()


# --- Scores Read/Write ---

def upsert_score(conn: Connection, user_id, points_delta=0, win_delta=0):
    with conn:
        conn.execute("""
            INSERT INTO scores (user_id, points, weekly_wins)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                points = points + excluded.points,
                weekly_wins = weekly_wins + excluded.weekly_wins;
        """, (user_id, points_delta, win_delta))

def get_user_score(conn: Connection, user_id):
    return conn.execute("""
        SELECT user_id, points, weekly_wins 
        FROM scores 
        WHERE user_id = ?;
    """, (user_id,)).fetchone()

def get_all_scores(conn: Connection):
    return conn.execute("""
        SELECT user_id, points, weekly_wins 
        FROM scores 
        ORDER BY points DESC;
    """).fetchall()


# --- Users Read/Write ---

def insert_user(conn: Connection, user_id, user_name, user_display_name, user_emoji=None):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, user_name, user_display_name, user_emoji)
            VALUES (?, ?, ?, ?);
        """, (user_id, user_name, user_display_name, user_emoji))

def get_user(conn: Connection, user_id):
    return conn.execute("""
        SELECT user_id, user_name, user_display_name, user_emoji 
        FROM users 
        WHERE user_id = ?;
    """, (user_id,)).fetchone()

def get_all_users(conn: Connection):
    return conn.execute("""
        SELECT user_id, user_name, user_display_name, user_emoji 
        FROM users;
    """).fetchall()


# --- Team Emojis Read/Write ---

def get_team_emojis(conn: Connection):
    return conn.execute("""
        SELECT role_name, emoji 
        FROM team_emojis;
    """).fetchall()

def insert_team_emoji(conn: Connection, role_name, emoji):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO team_emojis (role_name, emoji)
            VALUES (?, ?);
        """, (role_name, emoji))


# --- Teams Read/Write ---

def insert_team(conn: Connection, team_name_api, team_name_norsk, team_emoji):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO teams (team_name_api, team_name_norsk, team_emoji)
            VALUES (?, ?, ?);
        """, (team_name_api, team_name_norsk, team_emoji))

def get_team(conn: Connection, team_name_api):
    return conn.execute("""
        SELECT team_name_api, team_name_norsk, team_emoji 
        FROM teams 
        WHERE team_name_api = ?;
    """, (team_name_api,)).fetchone()
