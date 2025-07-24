

# --- Matches Read/Write ---

def insert_match(conn, match_id, message_id, home_team, away_team, kick_off_time):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO matches (match_id, message_id, home_team, away_team, kick_off_time)
            VALUES (?, ?, ?, ?);
        """, (match_id, message_id, home_team, away_team, kick_off_time))

def get_all_matches(conn):
    return conn.execute("SELECT * FROM matches ORDER BY kick_off_time;").fetchall()

def get_match_by_id(conn, match_id):
    return conn.execute("SELECT * FROM matches WHERE match_id = ?;", (match_id,)).fetchone()

# --- Predictions Read/Write ---

def insert_prediction(conn, match_id, user_id, prediction):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO predictions (match_id, user_id, prediction)
            VALUES (?, ?, ?);
        """, (match_id, user_id, prediction))

def get_predictions_for_user(conn, user_id):
    return conn.execute("SELECT * FROM predictions WHERE user_id = ?;", (user_id,)).fetchall()

def get_prediction(conn, match_id, user_id):
    return conn.execute("""
        SELECT prediction FROM predictions 
        WHERE match_id = ? AND user_id = ?;
    """, (match_id, user_id)).fetchone()

def get_all_predictions_for_match(conn, match_id):
    return conn.execute("""
        SELECT user_id, prediction FROM predictions
        WHERE match_id = ?;
    """, (match_id,)).fetchall()

# --- Scores Read/Write ---

def upsert_score(conn, user_id, points_delta=0, win_delta=0):
    with conn:
        conn.execute("""
            INSERT INTO scores (user_id, points, weekly_wins)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                points = points + excluded.points,
                weekly_wins = weekly_wins + excluded.weekly_wins;
        """, (user_id, points_delta, win_delta))

def get_user_score(conn, user_id):
    return conn.execute("SELECT * FROM scores WHERE user_id = ?;", (user_id,)).fetchone()

def get_all_scores(conn):
    return conn.execute("SELECT * FROM scores ORDER BY points DESC;").fetchall()

# --- Users Read/Write ---

def insert_user(conn, user_id, user_name, user_display_name, user_emoji=None):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, user_name, user_display_name, user_emoji)
            VALUES (?, ?, ?);
        """, (user_id, user_name, user_display_name, user_emoji))

def get_user(conn, user_id):
    return conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)).fetchone()

def get_all_users(conn):
    return conn.execute("SELECT * FROM users;").fetchall()

# --- Team Emojis Read/Write ---

def get_team_emojis(conn):
    return conn.execute("SELECT * FROM team_emojis;").fetchall()

def insert_team_emoji(conn, role_name, emoji):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO team_emojis (role_name, emoji)
            VALUES (?, ?);
        """, (role_name, emoji))

# --- Teams Read/Write ---

def insert_team(conn, team_name_api, team_name_norsk, team_emoji):
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO teams (team_name_api, team_name_norsk, team_emoji)
            VALUES (?, ?, ?);
        """, (team_name_api, team_name_norsk, team_emoji))

def get_team(conn, team_name_api):
    return conn.execute("SELECT * FROM teams WHERE team_name_api = ?;", (team_name_api,)).fetchone()
