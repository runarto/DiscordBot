"""
Multinomial logistic regression predictor trained on rolling match statistics.

Features (12) are derived purely from historical goals, xG, and results —
no external data required. The model is trained look-ahead-safely: features
for match M are computed using only matches that occurred before M.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from predictor.base import BasePredictor, HistoricalMatch, Prediction

_WINDOW_SHORT = 5   # rolling window for goals / xG / ppg
_WINDOW_DRAW  = 10  # rolling window for draw rate
_MIN_MATCHES  = 3   # minimum prior matches to produce a feature vector


# ---------------------------------------------------------------------------
# Feature helpers
# ---------------------------------------------------------------------------

def _team_recent(history: List[HistoricalMatch], team: str, n: int) -> List[HistoricalMatch]:
    matches = [m for m in history if m.home_team == team or m.away_team == team]
    return sorted(matches, key=lambda m: m.date)[-n:]


def _goals_for(matches: List[HistoricalMatch], team: str) -> float:
    if not matches:
        return 0.0
    return sum(
        m.home_goals if m.home_team == team else m.away_goals
        for m in matches
    ) / len(matches)


def _goals_against(matches: List[HistoricalMatch], team: str) -> float:
    if not matches:
        return 0.0
    return sum(
        m.away_goals if m.home_team == team else m.home_goals
        for m in matches
    ) / len(matches)


def _xg_for(matches: List[HistoricalMatch], team: str) -> float:
    if not matches:
        return 0.0
    total = 0.0
    for m in matches:
        if m.home_team == team:
            total += m.home_xg if (m.home_xg is not None and m.home_xg > 0) else float(m.home_goals)
        else:
            total += m.away_xg if (m.away_xg is not None and m.away_xg > 0) else float(m.away_goals)
    return total / len(matches)


def _xg_against(matches: List[HistoricalMatch], team: str) -> float:
    if not matches:
        return 0.0
    total = 0.0
    for m in matches:
        if m.home_team == team:
            total += m.away_xg if (m.away_xg is not None and m.away_xg > 0) else float(m.away_goals)
        else:
            total += m.home_xg if (m.home_xg is not None and m.home_xg > 0) else float(m.home_goals)
    return total / len(matches)


def _ppg(matches: List[HistoricalMatch], team: str) -> float:
    if not matches:
        return 1.0
    pts = 0.0
    for m in matches:
        if m.outcome == "H":
            pts += 3.0 if m.home_team == team else 0.0
        elif m.outcome == "A":
            pts += 3.0 if m.away_team == team else 0.0
        else:
            pts += 1.0
    return pts / len(matches)


def _draw_rate(matches: List[HistoricalMatch]) -> float:
    if not matches:
        return 0.27
    return sum(1 for m in matches if m.outcome == "D") / len(matches)


def _season_points(history: List[HistoricalMatch], team: str, year: int, league_id: Optional[int]) -> float:
    pts = 0.0
    for m in history:
        if m.date.year != year:
            continue
        if league_id is not None and m.league_id != league_id:
            continue
        if m.home_team != team and m.away_team != team:
            continue
        if m.outcome == "H":
            pts += 3.0 if m.home_team == team else 0.0
        elif m.outcome == "A":
            pts += 3.0 if m.away_team == team else 0.0
        else:
            pts += 1.0
    return pts


def extract_features(
    history: List[HistoricalMatch],
    home_team: str,
    away_team: str,
    match_date: Optional[datetime] = None,
    match_league_id: Optional[int] = None,
) -> Optional[List[float]]:
    """
    Compute a 15-element feature vector for (home_team, away_team) from `history`.
    Returns None if either team has fewer than _MIN_MATCHES appearances.

    match_date is used to determine the current season year for points tally.
    When omitted (live prediction), the most recent year in history is used.
    """
    h_short = _team_recent(history, home_team, _WINDOW_SHORT)
    a_short = _team_recent(history, away_team, _WINDOW_SHORT)
    h_draw  = _team_recent(history, home_team, _WINDOW_DRAW)
    a_draw  = _team_recent(history, away_team, _WINDOW_DRAW)

    if len(h_short) < _MIN_MATCHES or len(a_short) < _MIN_MATCHES:
        return None

    if match_date is not None:
        year = match_date.year
    elif history:
        year = max(m.date.year for m in history)
    else:
        year = datetime.now().year

    h_sp = _season_points(history, home_team, year, match_league_id)
    a_sp = _season_points(history, away_team, year, match_league_id)

    return [
        _goals_for(h_short, home_team),       # 0  home goals scored (last 5)
        _goals_against(h_short, home_team),   # 1  home goals conceded (last 5)
        _goals_for(a_short, away_team),        # 2  away goals scored (last 5)
        _goals_against(a_short, away_team),   # 3  away goals conceded (last 5)
        _xg_for(h_short, home_team),           # 4  home xG scored (last 5)
        _xg_against(h_short, home_team),      # 5  home xG conceded (last 5)
        _xg_for(a_short, away_team),           # 6  away xG scored (last 5)
        _xg_against(a_short, away_team),      # 7  away xG conceded (last 5)
        _ppg(h_short, home_team),              # 8  home points per game (last 5)
        _ppg(a_short, away_team),              # 9  away points per game (last 5)
        _draw_rate(h_draw),                    # 10 home draw rate (last 10)
        _draw_rate(a_draw),                    # 11 away draw rate (last 10)
        h_sp,                                  # 12 home cumulative season points
        a_sp,                                  # 13 away cumulative season points
        h_sp - a_sp,                           # 14 season points difference
    ]


# ---------------------------------------------------------------------------
# Predictor
# ---------------------------------------------------------------------------

class MLPredictor(BasePredictor):

    def __init__(self, C: float = 1.0):
        self._model = LogisticRegression(
            solver="lbfgs",
            max_iter=2000,
            C=C,
        )
        self._scaler = StandardScaler()
        self._matches: List[HistoricalMatch] = []
        self._fitted = False

    def train(self, matches: List[HistoricalMatch]) -> None:
        self._matches = sorted(matches, key=lambda m: m.date)

        X, y = [], []
        for i, m in enumerate(self._matches):
            prior = self._matches[:i]
            feats = extract_features(
                prior,
                m.home_team,
                m.away_team,
                match_date=m.date,
                match_league_id=m.league_id,
            )
            if feats is None:
                continue
            X.append(feats)
            y.append(m.outcome)

        if len(X) < 50:
            self._fitted = False
            return

        self._scaler.fit(X)
        self._model.fit(self._scaler.transform(X), y)
        self._fitted = True

    def predict(self, home_team: str, away_team: str) -> Optional[Prediction]:
        if not self._fitted:
            return None

        feats = extract_features(self._matches, home_team, away_team)
        if feats is None:
            return None

        probs_arr = self._model.predict_proba(self._scaler.transform([feats]))[0]
        prob_map: Dict[str, float] = dict(zip(self._model.classes_, probs_arr))

        home_prob = prob_map.get("H", 0.0)
        draw_prob = prob_map.get("D", 0.0)
        away_prob = prob_map.get("A", 0.0)

        probs = {"H": home_prob, "D": draw_prob, "A": away_prob}
        outcome = max(probs, key=probs.get)

        return Prediction(
            home_team=home_team,
            away_team=away_team,
            outcome=outcome,
            confidence=probs[outcome],
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
        )
