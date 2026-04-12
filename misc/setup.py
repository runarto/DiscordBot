import logging
from datetime import datetime
from typing import List
import discord
from discord.ext import commands
from misc.schedule import Schedule
from db.db_interface import DB
from api.fotmob import get_historical_matches
from api.xgscore import fetch_season_xg
from predictor import FormPredictor, EloPredictor, GoalsPredictor, EnsemblePredictor, from_fotmob
from predictor.calibration import calibrate_rho
from misc.constants import LEAGUES

TRAINING_SEASONS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
CURRENT_SEASON = 2026          # always re-fetched; past seasons are cached permanently
TRAINING_LEAGUE_KEYS = ["ELITE", "OBOS"]


def _backfill_xg_from_xgscore(logger: logging.Logger, db: DB, seasons: List[int]) -> None:
    """
    Fetches xG from xgscore.io and writes it into historical_matches.

    Strategy:
    - Current season: always re-fetch (new matches are played throughout the year).
    - Past seasons: skip if every match in that season already has a positive xG value
      (meaning xgscore has already been the source). Otherwise re-fetch and overwrite,
      so stale FotMob-scraped values are corrected.

    Matching is by date (YYYY-MM-DD, UTC) + home_team + away_team.
    """
    elite_id = LEAGUES["ELITE"]["id"]

    # Mark non-Eliteserien rows that are still NULL as permanently unavailable.
    for row in db._conn.execute("""
        SELECT match_id, league_id FROM historical_matches
        WHERE home_xg IS NULL AND league_id != ?
    """, (elite_id,)).fetchall():
        db.update_match_xg(row["match_id"], row["league_id"], -1.0, -1.0)

    # Build a lookup of ALL Eliteserien rows indexed by (date, home, away)
    all_rows = db.get_all_eliteserien_matches_for_xg(elite_id)
    row_index: dict = {}
    for row in all_rows:
        key = (row["kick_off_time"][:10], row["home_team"], row["away_team"])
        row_index[key] = row

    # Per-season coverage: is every match already filled with a positive (xgscore) value?
    season_fully_covered: dict = {}
    for season in seasons:
        season_rows = [r for r in all_rows if r["kick_off_time"].startswith(str(season))]
        if not season_rows:
            season_fully_covered[season] = True
            continue
        season_fully_covered[season] = all(
            r["home_xg"] is not None and r["home_xg"] > 0 for r in season_rows
        )

    filled_ids: set = set()

    for season in seasons:
        is_current = (season == CURRENT_SEASON)
        if season_fully_covered[season] and not is_current:
            logger.debug(f"  Season {season}: fully covered, skipping")
            continue

        logger.info(f"  Fetching xgscore season {season}...")
        xg_matches = fetch_season_xg(season)
        logger.info(f"  Got {len(xg_matches)} played matches from xgscore")

        for xm in xg_matches:
            key = (xm["date"].strftime("%Y-%m-%d"), xm["home_team"], xm["away_team"])
            row = row_index.get(key)
            if row is None:
                continue
            db.update_match_xg(row["match_id"], elite_id, xm["home_xg"], xm["away_xg"])
            filled_ids.add(row["match_id"])

    # Mark any Eliteserien match not filled in this run as permanently unavailable
    unfilled = 0
    for row in all_rows:
        if row["match_id"] not in filled_ids and (row["home_xg"] is None or row["home_xg"] <= 0):
            db.update_match_xg(row["match_id"], elite_id, -1.0, -1.0)
            unfilled += 1

    if filled_ids or unfilled:
        logger.info(f"xG backfill complete: {len(filled_ids)} filled, {unfilled} marked unavailable")


def setup_predictor(logger: logging.Logger, db: DB) -> EnsemblePredictor:
    """
    Loads historical match data from the database, fetching from the FotMob API
    only for seasons that are not yet cached. The current season is always
    re-fetched so newly played matches are included on every startup.
    """
    for key in TRAINING_LEAGUE_KEYS:
        config = LEAGUES[key]
        league_id = config["id"]
        for season in TRAINING_SEASONS:
            is_current = season == CURRENT_SEASON

            if not is_current and db.has_historical_season(league_id, season):
                logger.debug(f"Season {season} for {config['name']} already cached, skipping API call.")
                continue

            logger.info(f"Fetching {'current' if is_current else 'historical'} data for {config['name']} season {season}...")
            raw = get_historical_matches(league_id=league_id, slug=config["slug"], seasons=[season])
            for m in raw:
                db.insert_historical_match(
                    match_id=m["match_id"],
                    league_id=league_id,
                    season=season,
                    home_team=m["home_team"],
                    away_team=m["away_team"],
                    home_goals=m["home_goals"],
                    away_goals=m["away_goals"],
                    kick_off_time=m["date"].isoformat(),
                    page_url=m.get("page_url"),
                    replace=is_current,
                )
                if m.get("page_url"):
                    db.update_page_url(m["match_id"], league_id, m["page_url"])
            logger.info(f"Cached {len(raw)} matches for {config['name']} season {season}.")

    training_league_ids = {LEAGUES[k]["id"] for k in TRAINING_LEAGUE_KEYS}
    # --- Back-fill page_urls for cached seasons that predate this column ---
    for key in TRAINING_LEAGUE_KEYS:
        config = LEAGUES[key]
        league_id = config["id"]
        for season in TRAINING_SEASONS:
            if season == CURRENT_SEASON:
                continue  # already handled above
            needs_urls = db._conn.execute("""
                SELECT COUNT(*) FROM historical_matches
                WHERE league_id = ? AND season = ? AND page_url IS NULL
            """, (league_id, season)).fetchone()[0]
            if needs_urls == 0:
                continue
            logger.info(f"Back-filling page_urls for {config['name']} {season}...")
            raw = get_historical_matches(league_id=league_id, slug=config["slug"], seasons=[season])
            for m in raw:
                if m.get("page_url"):
                    db.update_page_url(m["match_id"], league_id, m["page_url"])

    # --- Backfill xG from xgscore.io (one request per gameweek, not per match) ---
    _backfill_xg_from_xgscore(logger, db, [CURRENT_SEASON])

    rows = db.get_historical_matches()
    all_raw = [
        {
            "match_id": row["match_id"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_goals": row["home_goals"],
            "away_goals": row["away_goals"],
            "date": datetime.fromisoformat(row["kick_off_time"]),
            "league_id": row["league_id"],
            "home_xg": row["home_xg"],
            "away_xg": row["away_xg"],
        }
        for row in rows
        if row["league_id"] in training_league_ids
    ]

    matches = from_fotmob(all_raw)
    form_pred  = FormPredictor()
    elo_pred   = EloPredictor()
    goals_pred = GoalsPredictor()
    predictor = EnsemblePredictor([
        (elo_pred,   0.30),
        (form_pred,  0.05),
        (goals_pred, 0.65),
    ])
    predictor.train(matches)

    # Wire ELO-derived league quality into GoalsPredictor so cross-league
    # predictions are scaled by the empirical strength gap between leagues.
    if elo_pred.league_avg_elos:
        max_elo = max(elo_pred.league_avg_elos.values())
        quality = {lid: avg / max_elo for lid, avg in elo_pred.league_avg_elos.items()}
        goals_pred.set_league_quality(quality)
        logger.info(f"League quality calibration: { {lid: round(q, 3) for lid, q in quality.items()} }")

    # Calibrate Dixon-Coles ρ on training data
    optimal_rho = calibrate_rho(goals_pred, matches)
    goals_pred._rho = optimal_rho
    logger.info(f"Calibrated Dixon-Coles ρ = {optimal_rho:.3f}")

    logger.info(f"Predictor trained on {len(matches)} cached matches.")
    return predictor

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("discord_bot")
    logger.setLevel(logging.DEBUG)  # Set logger to DEBUG so it captures everything

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # File handler (INFO+)
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (DEBUG+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Show DEBUG in terminal
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def setup_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.members = True
    intents.reactions = True
    intents.message_content = True
    intents.guilds = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    return bot


async def setup_scheduler(bot: commands.Bot, db: DB, channel_id: int, logger: logging.Logger) -> Schedule:
    """
    Sets up the scheduler for storing predictions.
    """
    channel = await bot.fetch_channel(channel_id)
    return Schedule(db, channel, logger)
