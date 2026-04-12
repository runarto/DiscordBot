"""
One-off script: force re-fetch of xG for Eliteserien 2020 from xgscore.io
and write the values into infobase.db.

Run from the project root:
    python -m scripts.refetch_xg_2020
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db.db_interface import DB
from api.xgscore import fetch_season_xg
from misc.constants import LEAGUES

SEASON = 2020
DB_PATH = "infobase.db"

def main():
    db = DB(DB_PATH)
    elite_id = LEAGUES["ELITE"]["id"]

    print(f"Fetching xgscore.io data for Eliteserien {SEASON}...")
    xg_matches = fetch_season_xg(SEASON)
    print(f"Got {len(xg_matches)} played matches from xgscore")

    # Build lookup of DB rows indexed by (date, home_team, away_team)
    all_rows = db.get_all_eliteserien_matches_for_xg(elite_id)
    row_index = {}
    for row in all_rows:
        if not row["kick_off_time"].startswith(str(SEASON)):
            continue
        key = (row["kick_off_time"][:10], row["home_team"], row["away_team"])
        row_index[key] = row

    print(f"Found {len(row_index)} {SEASON} matches in DB")

    filled = 0
    unmatched = []
    for xm in xg_matches:
        key = (xm["date"].strftime("%Y-%m-%d"), xm["home_team"], xm["away_team"])
        row = row_index.get(key)
        if row is None:
            unmatched.append(key)
            continue
        db.update_match_xg(row["match_id"], elite_id, xm["home_xg"], xm["away_xg"])
        filled += 1

    print(f"Updated {filled} matches with xG")
    if unmatched:
        print(f"Could not match {len(unmatched)} xgscore entries to DB rows:")
        for k in unmatched:
            print(f"  {k}")

if __name__ == "__main__":
    main()
