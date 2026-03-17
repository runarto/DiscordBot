from sqlite3 import Connection
from typing import Optional, Union

# --- Matches Read/Write ---

def insert_match(conn: Connection, match_id: Union[int, str], message_id: Union[int, str], home_team: str, away_team: str, kick_off_time: str, league_id: int, cancelled: bool = False):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO matches (match_id, message_id, home_team, away_team, kick_off_time, league_id, cancelled)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (match_id, message_id, home_team, away_team, kick_off_time, league_id, cancelled))

def get_all_matches(conn: Connection):
    return conn.execute("SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id FROM matches ORDER BY kick_off_time;").fetchall()

def get_matches_by_league(conn: Connection, league_id: int):
    return conn.execute("""
        SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id
        FROM matches
        WHERE league_id = ?
        ORDER BY kick_off_time;
    """, (league_id,)).fetchall()

def get_match(conn: Connection, match_id: Optional[int] = None, message_id: Optional[int] = None):
    if match_id and message_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id
            FROM matches
            WHERE match_id = ? AND message_id = ?;
        """
        return conn.execute(query, (match_id, message_id)).fetchone()
    elif match_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id
            FROM matches
            WHERE match_id = ?;
        """
        return conn.execute(query, (match_id,)).fetchone()
    elif message_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id
            FROM matches
            WHERE message_id = ?;
        """
        return conn.execute(query, (message_id,)).fetchone()
    else:
        raise ValueError("At least one of match_id or message_id must be provided.")


# --- Predictions Read/Write ---

def insert_prediction(conn: Connection, message_id: Union[int, str], user_id: Union[int, str], prediction: str):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO predictions (message_id, user_id, prediction)
            VALUES (?, ?, ?);
        """, (message_id, user_id, prediction))

def get_predictions_for_user(conn: Connection, user_id: Union[int, str]):
    return conn.execute("""
        SELECT message_id, user_id, prediction 
        FROM predictions 
        WHERE user_id = ?;
    """, (user_id,)).fetchall()

def get_prediction(conn: Connection, message_id: Union[int, str], user_id: Union[int, str]):
    return conn.execute("""
        SELECT message_id, user_id, prediction 
        FROM predictions 
        WHERE message_id = ? AND user_id = ?;
    """, (message_id, user_id)).fetchone()

def get_all_predictions_for_match(conn: Connection, message_id: Union[int, str]):
    return conn.execute("""
        SELECT message_id, user_id, prediction 
        FROM predictions 
        WHERE message_id = ?;
    """, (message_id,)).fetchall()


# --- Scores Read/Write ---

def upsert_score(conn: Connection, user_id: Union[int, str], league_id: int, points_delta: int = 0, win_delta: int = 0):
    with conn:
        conn.execute("""
            INSERT INTO scores (user_id, league_id, points, weekly_wins)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, league_id) DO UPDATE SET
                points = points + excluded.points,
                weekly_wins = weekly_wins + excluded.weekly_wins;
        """, (user_id, league_id, points_delta, win_delta))

def get_user_score(conn: Connection, user_id: Union[int, str], league_id: int):
    return conn.execute("""
        SELECT user_id, league_id, points, weekly_wins
        FROM scores
        WHERE user_id = ? AND league_id = ?;
    """, (user_id, league_id)).fetchone()

def get_all_scores(conn: Connection):
    return conn.execute("""
        SELECT user_id, league_id, points, weekly_wins
        FROM scores
        ORDER BY points DESC;
    """).fetchall()

def get_scores_by_league(conn: Connection, league_id: int):
    return conn.execute("""
        SELECT user_id, league_id, points, weekly_wins
        FROM scores
        WHERE league_id = ?
        ORDER BY points DESC;
    """, (league_id,)).fetchall()


# --- Users Read/Write ---

def insert_user(conn: Connection, user_id: Union[int, str], user_name: str, user_display_name: str, user_emoji: str = None):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, user_name, user_display_name, user_emoji)
            VALUES (?, ?, ?, ?);
        """, (user_id, user_name, user_display_name, user_emoji))

def get_user(conn: Connection, user_id: Union[int, str]):
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

def insert_team_emoji(conn: Connection, role_name: str, emoji: str):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO team_emojis (role_name, emoji)
            VALUES (?, ?);
        """, (role_name, emoji))


# --- Teams Read/Write ---

def insert_team(conn: Connection, team_name: str, league_id: int, team_emoji: str):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO teams (team_name, league_id, team_emoji)
            VALUES (?, ?, ?);
        """, (team_name, league_id, team_emoji))

def get_team(conn: Connection, team_name: str, league_id: int):
    return conn.execute("""
        SELECT team_name, league_id, team_emoji
        FROM teams
        WHERE team_name = ? AND league_id = ?;
    """, (team_name, league_id)).fetchone()

def get_team_by_name(conn: Connection, team_name: str):
    return conn.execute("""
        SELECT team_name, league_id, team_emoji
        FROM teams
        WHERE team_name = ?
        LIMIT 1;
    """, (team_name,)).fetchone()

def get_teams_by_league(conn: Connection, league_id: int):
    return conn.execute("""
        SELECT team_name, league_id, team_emoji
        FROM teams
        WHERE league_id = ?;
    """, (league_id,)).fetchall()
