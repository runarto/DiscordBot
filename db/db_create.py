from sqlite3 import Connection



def create_matches_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            kick_off_time TEXT NOT NULL,
            league_id INTEGER NOT NULL,
            cancelled INTEGER NOT NULL DEFAULT 0,
            processed INTEGER NOT NULL DEFAULT 0
        );
        """)
    try:
        conn.execute("ALTER TABLE matches ADD COLUMN processed INTEGER NOT NULL DEFAULT 0;")
        conn.commit()
        # First-time migration: mark all past matches as processed using ISO format
        # comparison so same-day dates are handled correctly.
        conn.execute("""
            UPDATE matches SET processed = 1
            WHERE kick_off_time < strftime('%Y-%m-%dT%H:%M:%SZ', 'now');
        """)
        conn.commit()
    except Exception:
        pass  # column already exists, migration already ran

    # Always-running idempotent fix: mark matches as processed if they kicked off
    # >4 hours ago AND have stored predictions (proving the match actually started).
    # Catches cases where the first-time migration missed same-day matches due to
    # the datetime() vs strftime() format mismatch.
    conn.execute("""
        UPDATE matches SET processed = 1
        WHERE processed = 0
        AND kick_off_time < strftime('%Y-%m-%dT%H:%M:%SZ', datetime('now', '-4 hours'))
        AND EXISTS (
            SELECT 1 FROM predictions WHERE predictions.message_id = matches.message_id LIMIT 1
        );
    """)
    conn.commit()

def create_predictions_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            message_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            prediction TEXT NOT NULL,
            PRIMARY KEY (message_id, user_id)
        );
        """)

def create_scores_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user_id TEXT NOT NULL,
            league_id INTEGER NOT NULL,
            points INTEGER NOT NULL DEFAULT 0,
            weekly_wins INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, league_id)
        );
        """)

def create_users_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            user_name TEXT NOT NULL,
            user_display_name TEXT NOT NULL,
            user_emoji TEXT
        );
        """)

def create_team_emojis_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS team_emojis (
            role_name TEXT PRIMARY KEY,
            emoji TEXT NOT NULL
        );
        """)

def create_teams_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_name TEXT NOT NULL,
            league_id INTEGER NOT NULL,
            team_emoji TEXT NOT NULL,
            PRIMARY KEY (team_name, league_id)
        );
        """)

def create_bot_predictions_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bot_predictions (
            match_id INTEGER NOT NULL,
            league_id INTEGER NOT NULL,
            home_prob REAL NOT NULL,
            draw_prob REAL NOT NULL,
            away_prob REAL NOT NULL,
            outcome TEXT NOT NULL,
            PRIMARY KEY (match_id, league_id)
        );
        """)

def create_historical_matches_table(conn: Connection):
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS historical_matches (
            match_id INTEGER NOT NULL,
            league_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_goals INTEGER NOT NULL,
            away_goals INTEGER NOT NULL,
            kick_off_time TEXT NOT NULL,
            home_xg REAL,
            away_xg REAL,
            page_url TEXT,
            PRIMARY KEY (match_id, league_id)
        );
        """)
    # Migration: add columns to existing tables that predate this schema
    for col_def in ("home_xg REAL", "away_xg REAL", "page_url TEXT"):
        try:
            conn.execute(f"ALTER TABLE historical_matches ADD COLUMN {col_def};")
            conn.commit()
        except Exception:
            pass  # column already exists
