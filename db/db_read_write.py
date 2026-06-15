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
    return conn.execute("SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id, processed FROM matches ORDER BY kick_off_time;").fetchall()

def get_matches_by_league(conn: Connection, league_id: int):
    return conn.execute("""
        SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id, processed
        FROM matches
        WHERE league_id = ?
        ORDER BY kick_off_time;
    """, (league_id,)).fetchall()

def get_unprocessed_matches_by_league(conn: Connection, league_id: int):
    return conn.execute("""
        SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id, processed
        FROM matches
        WHERE league_id = ? AND processed = 0
        ORDER BY kick_off_time;
    """, (league_id,)).fetchall()

def mark_match_processed(conn: Connection, match_id: int):
    with conn:
        conn.execute("UPDATE matches SET processed = 1 WHERE match_id = ?;", (match_id,))

def get_match(conn: Connection, match_id: Optional[int] = None, message_id: Optional[int] = None):
    if match_id and message_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id, processed
            FROM matches
            WHERE match_id = ? AND message_id = ?;
        """
        return conn.execute(query, (match_id, message_id)).fetchone()
    elif match_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id, processed
            FROM matches
            WHERE match_id = ?;
        """
        return conn.execute(query, (match_id,)).fetchone()
    elif message_id:
        query = """
            SELECT match_id, message_id, home_team, away_team, kick_off_time, cancelled, league_id, processed
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


# --- Bot Predictions Read/Write ---

def upsert_bot_prediction(conn: Connection, match_id: int, league_id: int,
                           home_prob: float, draw_prob: float, away_prob: float, outcome: str) -> None:
    with conn:
        conn.execute("""
            INSERT INTO bot_predictions (match_id, league_id, home_prob, draw_prob, away_prob, outcome)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, league_id) DO UPDATE SET
                home_prob = excluded.home_prob,
                draw_prob = excluded.draw_prob,
                away_prob = excluded.away_prob,
                outcome   = excluded.outcome;
        """, (match_id, league_id, home_prob, draw_prob, away_prob, outcome))

def get_bot_prediction(conn: Connection, match_id: int, league_id: int):
    return conn.execute("""
        SELECT match_id, league_id, home_prob, draw_prob, away_prob, outcome
        FROM bot_predictions WHERE match_id = ? AND league_id = ?;
    """, (match_id, league_id)).fetchone()

def get_all_bot_predictions(conn: Connection):
    return conn.execute("""
        SELECT match_id, league_id, home_prob, draw_prob, away_prob, outcome
        FROM bot_predictions;
    """).fetchall()


# --- Historical Matches Read/Write ---

def insert_historical_match(conn: Connection, match_id: int, league_id: int, season: int,
                             home_team: str, away_team: str, home_goals: int, away_goals: int,
                             kick_off_time: str, page_url: str = None, replace: bool = False):
    with conn:
        if replace:
            # Upsert: update all match fields but preserve cached xG so it is
            # not wiped on every startup when the current season is re-fetched.
            conn.execute("""
                INSERT INTO historical_matches
                    (match_id, league_id, season, home_team, away_team, home_goals, away_goals, kick_off_time, page_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id, league_id) DO UPDATE SET
                    season       = excluded.season,
                    home_team    = excluded.home_team,
                    away_team    = excluded.away_team,
                    home_goals   = excluded.home_goals,
                    away_goals   = excluded.away_goals,
                    kick_off_time = excluded.kick_off_time,
                    page_url     = excluded.page_url;
            """, (match_id, league_id, season, home_team, away_team, home_goals, away_goals, kick_off_time, page_url))
        else:
            conn.execute("""
                INSERT OR IGNORE INTO historical_matches
                    (match_id, league_id, season, home_team, away_team, home_goals, away_goals, kick_off_time, page_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (match_id, league_id, season, home_team, away_team, home_goals, away_goals, kick_off_time, page_url))

def get_historical_matches(conn: Connection) -> list:
    return conn.execute("""
        SELECT match_id, league_id, season, home_team, away_team, home_goals, away_goals, kick_off_time,
               home_xg, away_xg
        FROM historical_matches
        ORDER BY kick_off_time;
    """).fetchall()

def update_page_url(conn: Connection, match_id: int, league_id: int, page_url: str) -> None:
    """Sets page_url on an existing row only if it is currently NULL."""
    with conn:
        conn.execute("""
            UPDATE historical_matches SET page_url = ?
            WHERE match_id = ? AND league_id = ? AND page_url IS NULL;
        """, (page_url, match_id, league_id))

def get_all_eliteserien_matches_for_xg(conn: Connection, league_id: int) -> list:
    """Returns all Eliteserien historical match rows for xG backfill."""
    return conn.execute("""
        SELECT match_id, league_id, home_team, away_team, kick_off_time, home_xg
        FROM historical_matches
        WHERE league_id = ?
        ORDER BY kick_off_time;
    """, (league_id,)).fetchall()


def reset_xg_for_league(conn: Connection, league_id: int) -> None:
    """Resets all xG values to NULL for the given league."""
    with conn:
        conn.execute("""
            UPDATE historical_matches SET home_xg = NULL, away_xg = NULL
            WHERE league_id = ?;
        """, (league_id,))

def update_match_xg(conn: Connection, match_id: int, league_id: int,
                    home_xg: float, away_xg: float) -> None:
    with conn:
        conn.execute("""
            UPDATE historical_matches
            SET home_xg = ?, away_xg = ?
            WHERE match_id = ? AND league_id = ?;
        """, (home_xg, away_xg, match_id, league_id))

def has_historical_season(conn: Connection, league_id: int, season: int) -> bool:
    row = conn.execute("""
        SELECT 1 FROM historical_matches
        WHERE league_id = ? AND season = ?
        LIMIT 1;
    """, (league_id, season)).fetchone()
    return row is not None
