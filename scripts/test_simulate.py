"""
Quick smoke test for the season simulator.

Run from the project root:
    python scripts/test_simulate.py [ELITE|OBOS]
"""

import sys
from datetime import datetime

from api.fotmob import get_remaining_fixtures
from db.db_interface import DB
from misc.constants import LEAGUES
from misc.setup import setup_predictor, setup_logging
from predictor.simulator import (
    Fixture,
    SeasonSimulator,
    TeamStanding,
    format_sim_result,
    standings_from_rows,
)

LEAGUE_KEY = sys.argv[1] if len(sys.argv) > 1 else "ELITE"
LEAGUE_ZONES = {
    "ELITE": {"top_n": 3, "bottom_m": 2, "top_label": "Europa",  "bottom_label": "Nedrykk"},
    "OBOS":  {"top_n": 2, "bottom_m": 3, "top_label": "Opprykk", "bottom_label": "Nedrykk"},
}

logger = setup_logging()
db = DB("test.db")
config = LEAGUES[LEAGUE_KEY]
zones = LEAGUE_ZONES[LEAGUE_KEY]

print(f"Training predictor...")
predictor = setup_predictor(logger=logger, db=db)

print(f"Building standings for {config['name']} {config['season']}...")
all_rows = db.get_historical_matches()
season_rows = [r for r in all_rows if r["league_id"] == config["id"] and r["season"] == config["season"]]
standings = standings_from_rows(season_rows)
print(f"  {len(standings)} teams from played matches")

print(f"Fetching remaining fixtures from FotMob...")
raw = get_remaining_fixtures(league_id=config["id"], slug=config["slug"])
fixtures = [Fixture(home_team=f["home_team"], away_team=f["away_team"]) for f in raw]
print(f"  {len(fixtures)} remaining fixtures")

# Add teams that haven't played yet
known = {s.team for s in standings}
for f in fixtures:
    for team in (f.home_team, f.away_team):
        if team not in known:
            standings.append(TeamStanding(team=team, played=0, won=0, drawn=0, lost=0, goals_for=0, goals_against=0))
            known.add(team)
            print(f"  Added unplayed team: {team}")

print(f"  {len(standings)} total teams in simulation")
print(f"Running simulation...")

sim = SeasonSimulator(predictor, n_sims=10_000)
result = sim.simulate(standings, fixtures, top_n=zones["top_n"], bottom_m=zones["bottom_m"])

print()
print(format_sim_result(result, config["name"], top_label=zones["top_label"], bottom_label=zones["bottom_label"]))
