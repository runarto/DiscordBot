import json
import re
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# --- FotMob URL templates ---

BASE_LEAGUE_URL = "https://www.fotmob.com/nb/leagues/{league_id}/fixtures/{slug}?group=by-date&page={page}"
BASE_LEAGUE_SEASON_URL = "https://www.fotmob.com/nb/leagues/{league_id}/fixtures/{slug}?group=by-date&page={page}&season={season}"


# --- HTTP utilities ---

def generate_headers(_: Optional[str] = None) -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8",
    }


def validate(response: requests.Response) -> Dict:
    response.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Could not find __NEXT_DATA__ in FotMob response")
    return json.loads(match.group(1))


# --- FotMob page fetchers ---

def fetch_page(league_id: int, slug: str, page: int = 0) -> Dict:
    url = BASE_LEAGUE_URL.format(league_id=league_id, slug=slug, page=page)
    return validate(requests.get(url, headers=generate_headers(), timeout=10))


def fetch_all_pages(league_id: int, slug: str, max_pages: int = 10) -> List[Dict]:
    all_matches = []
    seen_ids = set()
    for page in range(max_pages):
        data = fetch_page(league_id=league_id, slug=slug, page=page)
        matches = extract_all_matches(data)
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


def fetch_season_pages(league_id: int, slug: str, season: int, max_pages: int = 20) -> List[Dict]:
    all_matches = []
    seen_ids = set()
    for page in range(max_pages):
        url = BASE_LEAGUE_SEASON_URL.format(league_id=league_id, slug=slug, season=season, page=page)
        data = validate(requests.get(url, headers=generate_headers(), timeout=10))
        matches = extract_all_matches(data)
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


# --- FotMob data extraction / parsing ---

def extract_all_matches(data: Dict) -> List[Dict]:
    matches = data.get("props", {}).get("pageProps", {}).get("fixtures", {}).get("allMatches")
    if matches is None:
        raise ValueError("Could not find fixtures.allMatches in FotMob payload")
    return matches


def extract_league_teams(data: Dict) -> List[Dict]:
    matches = extract_all_matches(data)
    teams = {}
    for m in matches:
        home = m.get("home", {})
        away = m.get("away", {})
        if home.get("id"):
            teams[home["id"]] = {"id": home.get("id"), "name": home.get("name"), "shortName": home.get("shortName")}
        if away.get("id"):
            teams[away["id"]] = {"id": away.get("id"), "name": away.get("name"), "shortName": away.get("shortName")}
    return list(teams.values())


def fotmob_status_to_state(status: Dict) -> str:
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
        "match_state": fotmob_status_to_state(status),
        "page_url": m.get("pageUrl"),
        "score": status.get("scoreStr"),
    }


def parse_utc(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_score(score_str: Optional[str]) -> Optional[Tuple[int, int]]:
    if not score_str:
        return None
    try:
        home, away = (int(x.strip()) for x in score_str.split("-"))
        return home, away
    except (ValueError, AttributeError):
        return None


# --- api-sports.io (RapidSports) utilities ---

def generate_api_sports_headers(auth: str) -> dict:
    return {"x-apisports-key": auth}


def validate_json(response: requests.Response) -> Dict:
    response.raise_for_status()
    return response.json()


# --- xgscore.io utilities ---

_XGSCORE_NAME_MAP: Dict[str, str] = {
    "Bodø-Glimt":   "Bodø/Glimt",
    "HamKam":       "Hamarkameratene",
    "Haugesund":    "FK Haugesund",
    "Odd":          "Odds Ballklubb",
    "Stromsgodset": "Strømsgodset",
}


def normalise_xgscore_name(name: str) -> str:
    return _XGSCORE_NAME_MAP.get(name, name)
