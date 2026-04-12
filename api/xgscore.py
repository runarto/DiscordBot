"""
xgscore.io API client for fetching historical xG data for Eliteserien.

Endpoint: https://api.xgscore.io/games/xg?tournamentId=nor-1&seasonId={year}&gameweek={gw}
Returns 8 matches per gameweek (16-team league), up to 30 gameweeks per season.
"""
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List

import requests

from api.api_utils import normalise_xgscore_name

_BASE = "https://api.xgscore.io/games/xg"
_HEADERS = {
    "accept": "application/json",
    "accept-language": "en",
    "x-geolocation": "NO",
    "x-utc-offset": "1",
    "referer": "https://xgscore.io/",
    "User-Agent": "Mozilla/5.0",
}


def fetch_season_xg(season: int, delay: float = 0.5) -> List[Dict]:
    """
    Fetch all played matches with xG for the given Eliteserien season.

    Returns a list of dicts:
        home_team, away_team  — FotMob-normalised names
        date                  — datetime (UTC)
        home_xg, away_xg      — floats
    """
    results = []
    consecutive_empty = 0
    for gw in range(1, 35):
        try:
            r = requests.get(
                _BASE,
                params={"tournamentId": "nor-1", "lng": "en",
                        "seasonId": season, "gameweek": gw},
                headers=_HEADERS,
                timeout=10,
            )
            r.raise_for_status()
            matches = r.json()
        except Exception:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break
            continue

        if not matches:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break
            time.sleep(delay)
            continue

        consecutive_empty = 0

        for m in matches:
            if not m.get("played"):
                continue
            xg = m.get("xG")
            if not xg or xg.get("h") is None or xg.get("a") is None:
                continue
            try:
                dt = datetime.fromisoformat(
                    m["datetime"].replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            except (KeyError, ValueError):
                continue
            results.append({
                "home_team": normalise_xgscore_name(m["teams"]["h"]["name"]),
                "away_team": normalise_xgscore_name(m["teams"]["a"]["name"]),
                "date": dt,
                "home_xg": float(xg["h"]),
                "away_xg": float(xg["a"]),
            })

        time.sleep(delay)

    return results
