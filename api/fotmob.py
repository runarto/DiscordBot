from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import requests
from api.api_utils import generate_headers, validate
from misc.dataclasses import Result, Match


BASE_LEAGUE_URL = "https://www.fotmob.com/nb/leagues/{league_id}/fixtures/{slug}?group=by-date&page={page}"

def _extract_all_matches(data: Dict) -> List[Dict]:
    matches = data.get("props", {}).get("pageProps", {}).get("fixtures", {}).get("allMatches")
    if matches is None:
        raise ValueError("Could not find fixtures.allMatches in FotMob payload")
    return matches

def _extract_league_teams(data: Dict) -> List[Dict]:
    matches = _extract_all_matches(data)

    teams = {}
    for m in matches:
        home = m.get("home", {})
        away = m.get("away", {})

        if home.get("id"):
            teams[home["id"]] = {
                "id": home.get("id"),
                "name": home.get("name"),
                "shortName": home.get("shortName"),
            }

        if away.get("id"):
            teams[away["id"]] = {
                "id": away.get("id"),
                "name": away.get("name"),
                "shortName": away.get("shortName"),
            }

    return list(teams.values())


def _fotmob_status_to_state(status: Dict) -> str:
    reason_key = status.get("reason", {}).get("longKey")

    if reason_key == "postponed":
        return "postponed"
    if status.get("finished"):
        return "finished"
    if status.get("started"):
        return "live"
    if status.get("cancelled"):
        return "cancelled"
    return "scheduled"


def normalize_match(m: Dict) -> Dict:
    status = m.get("status", {})
    reason = status.get("reason", {})

    def safe_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    return {
        "match_id": safe_int(m.get("id")),
        "round": safe_int(m.get("round")),
        "round_name": m.get("roundName"),
        "home_team_id": safe_int(m.get("home", {}).get("id")),
        "home_team_name": m.get("home", {}).get("name"),
        "away_team_id": safe_int(m.get("away", {}).get("id")),
        "away_team_name": m.get("away", {}).get("name"),
        "kickoff_utc": status.get("utcTime"),
        "timezone": status.get("timezone"),
        "started": status.get("started"),
        "finished": status.get("finished"),
        "cancelled": status.get("cancelled"),
        "status_reason_short": reason.get("short"),
        "status_reason_long": reason.get("long"),
        "status_reason_key": reason.get("longKey"),
        "match_state": _fotmob_status_to_state(status),
        "page_url": m.get("pageUrl"),
        "score": status.get("scoreStr"),
    }


def _fetch_page(league_id: int, slug: str, page: int = 0) -> Dict:
    url = BASE_LEAGUE_URL.format(league_id=league_id, slug=slug, page=page)
    response = requests.get(url, headers=generate_headers(), timeout=10)
    return validate(response)


def _fetch_all_pages(league_id: int, slug: str, max_pages: int = 10) -> List[Dict]:
    all_matches = []
    seen_ids = set()

    for page in range(max_pages):
        data = _fetch_page(league_id=league_id, slug=slug, page=page)
        matches = _extract_all_matches(data)

        new_count = 0
        for m in matches:
            match_id = m.get("id")
            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)
            all_matches.append(m)
            new_count += 1

        if new_count == 0:
            break

    return all_matches


def _parse_utc(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(timezone.utc)


def get_fixture(fixture_id: int, league_id: int = 59, slug: str = "eliteserien") -> List[dict]:
    """
    Fetches a specific fixture by its ID from FotMob.
    auth is unused and kept only for interface compatibility.
    """
    matches = _fetch_all_pages(league_id=league_id, slug=slug)

    result = [normalize_match(m) for m in matches if int(m.get("id", -1)) == fixture_id]
    return result


def get_teams(auth: str, league_id: int, season: int, slug: str = "eliteserien") -> List[dict]:
    """
    Fetches teams from FotMob for a specific league.
    season is currently unused because the fixtures page payload does not require it directly.
    """
    data = _fetch_page(league_id=league_id, slug=slug, page=0)
    return _extract_league_teams(data)


def get_fixtures(x_days: int, league_id: int, slug: str = "eliteserien") -> List[Match]:
    """
    Fetches fixtures for the next x_days from FotMob for a specific league.
    season is currently unused.
    """
    now_utc = datetime.now(timezone.utc)
    end_utc = now_utc + timedelta(days=x_days)

    matches = _fetch_all_pages(league_id=league_id, slug=slug)

    filtered = []
    for m in matches:
        kickoff = _parse_utc(m.get("status", {}).get("utcTime"))
        if kickoff is None:
            continue
        if now_utc <= kickoff <= end_utc:
            filtered.append(normalize_match(m))
            
    matches = []
    for m in filtered:
        matches.append(Match(
            match_id=m["match_id"],
            message_id=-1,
            home_team=m["home_team_name"],
            away_team=m["away_team_name"],
            kick_off_time=m["kickoff_utc"],
            cancelled=m["cancelled"],
            league_id=league_id
        ))

    return matches


def get_fixture_result(match_id: int, league_id: int = 59, slug: str = "eliteserien") -> Result:
    """
    Fetches result/status for a specific match-id from FotMob.
    """
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
        result=result["score"]
    )






