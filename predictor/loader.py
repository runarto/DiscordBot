from typing import Dict, List

from predictor.base import HistoricalMatch


def from_fotmob(matches: List[Dict]) -> List[HistoricalMatch]:
    """
    Converts the raw dicts returned by api.fotmob.get_historical_matches
    into HistoricalMatch objects for use with any BasePredictor.
    """
    result = []
    for m in matches:
        try:
            result.append(HistoricalMatch(
                home_team=m["home_team"],
                away_team=m["away_team"],
                home_goals=m["home_goals"],
                away_goals=m["away_goals"],
                date=m["date"],
                league_id=m.get("league_id"),
                home_xg=m.get("home_xg"),
                away_xg=m.get("away_xg"),
            ))
        except (KeyError, TypeError):
            continue
    return result
