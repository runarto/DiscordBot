import json
import re
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple

from api.api_utils import (
    generate_headers,
    fetch_page,
    fetch_all_pages,
    fetch_season_pages,
    extract_league_teams,
    normalize_match,
    parse_utc,
    parse_score,
)
from misc.dataclasses import Result, Match


_XG_UNAVAILABLE: Tuple[float, float] = (-1.0, -1.0)


def get_fixture(fixture_id: int, league_id: int = 59, slug: str = "eliteserien") -> List[dict]:
    matches = fetch_all_pages(league_id=league_id, slug=slug)
    return [normalize_match(m) for m in matches if int(m.get("id", -1)) == fixture_id]


def get_teams(auth: str, league_id: int, season: int, slug: str = "eliteserien") -> List[dict]:
    data = fetch_page(league_id=league_id, slug=slug, page=0)
    return extract_league_teams(data)


def get_fixtures(x_days: int, league_id: int, slug: str = "eliteserien") -> List[Match]:
    now_utc = datetime.now(timezone.utc)
    end_utc = now_utc + timedelta(days=x_days)

    matches = fetch_all_pages(league_id=league_id, slug=slug)

    result = []
    for m in matches:
        nm = normalize_match(m)
        kickoff = parse_utc(nm["kickoff_utc"])
        if kickoff is None or not (now_utc <= kickoff <= end_utc):
            continue
        result.append(Match(
            match_id=nm["match_id"],
            message_id=-1,
            home_team=nm["home_team_name"],
            away_team=nm["away_team_name"],
            kick_off_time=nm["kickoff_utc"],
            cancelled=nm["cancelled"],
            league_id=league_id,
        ))
    return result


def get_historical_matches(league_id: int, slug: str, seasons: List[int]) -> List[Dict]:
    results = []
    for season in seasons:
        matches = fetch_season_pages(league_id=league_id, slug=slug, season=season)
        for m in matches:
            nm = normalize_match(m)
            if nm["match_state"] != "finished":
                continue
            score = parse_score(nm["score"])
            if score is None:
                continue
            kickoff = parse_utc(nm["kickoff_utc"])
            if kickoff is None:
                continue
            home_goals, away_goals = score
            results.append({
                "match_id": nm["match_id"],
                "home_team": nm["home_team_name"],
                "away_team": nm["away_team_name"],
                "home_goals": home_goals,
                "away_goals": away_goals,
                "date": kickoff,
                "league_id": league_id,
                "page_url": nm["page_url"],
            })
    return results


def get_remaining_fixtures(league_id: int, slug: str) -> List[Dict]:
    now_utc = datetime.now(timezone.utc)
    matches = fetch_all_pages(league_id=league_id, slug=slug)
    fixtures = []
    for m in matches:
        nm = normalize_match(m)
        if nm["match_state"] != "scheduled":
            continue
        kickoff = parse_utc(nm["kickoff_utc"])
        if kickoff is None or kickoff <= now_utc:
            continue
        if nm["home_team_name"] and nm["away_team_name"]:
            fixtures.append({"home_team": nm["home_team_name"], "away_team": nm["away_team_name"]})
    return fixtures


def get_match_xg(page_url: str, expected_match_id: Optional[int] = None) -> Optional[Tuple[float, float]]:
    """
    Fetches xG for a single match from its FotMob page URL.

    Returns:
        (home_xg, away_xg)   — real xG values (both >= 0)
        (-1.0, -1.0)         — definitively no data (wrong match or no xG stats)
        None                 — transient network/parse error; will be retried
    """
    slug = page_url.split("#")[0]
    url = f"https://www.fotmob.com{slug}"
    try:
        resp = requests.get(url, headers=generate_headers(), timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    script_match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        resp.text, re.DOTALL,
    )
    if not script_match:
        return None

    try:
        data = json.loads(script_match.group(1))
        page_props = data["props"]["pageProps"]

        if expected_match_id is not None:
            returned_id = page_props.get("general", {}).get("matchId")
            if returned_id is not None and int(returned_id) != int(expected_match_id):
                return _XG_UNAVAILABLE

        stat_groups = page_props["content"]["stats"]["Periods"]["All"]["stats"]
        for group in stat_groups:
            for stat in group.get("stats", []):
                if stat.get("key") == "expected_goals":
                    values = stat.get("stats", [])
                    if values[0] is None or values[1] is None:
                        continue
                    return float(values[0]), float(values[1])
    except (KeyError, IndexError, TypeError, ValueError):
        return _XG_UNAVAILABLE

    return _XG_UNAVAILABLE


def get_fixture_result(match_id: int, league_id: int = 59, slug: str = "eliteserien") -> Result:
    result = get_fixture(fixture_id=match_id, league_id=league_id, slug=slug)[0]
    return Result(
        match_id=result["match_id"],
        home_team=result["home_team_name"],
        away_team=result["away_team_name"],
        status={
            "short": result["status_reason_short"],
            "long": result["status_reason_long"],
            "key": result["status_reason_key"],
        },
        result=result["score"],
    )
