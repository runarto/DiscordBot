import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from predictor.base import BasePredictor, HistoricalMatch, Prediction

_MAX_GOALS = 10   # upper bound for Poisson score grid
_DC_RHO    = -0.13  # Dixon-Coles correlation parameter (estimated in original paper)

# Fallback averages if a league has no data
_DEFAULT_HOME_AVG = 1.5
_DEFAULT_AWAY_AVG = 1.1
_DEFAULT_AVGS = {"home": _DEFAULT_HOME_AVG, "away": _DEFAULT_AWAY_AVG}
_DEFAULT_DRAW_TENDENCY = 1.0


def _poisson_pmf(lam: float, k: int) -> float:
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _dc_correction(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """
    Dixon-Coles correction factor τ(x, y) for low-scoring outcomes.
    With rho < 0 this increases the probability of 0-0 and 1-1 draws
    and decreases 1-0 and 0-1, correcting the independence assumption
    of the plain Poisson model.
    """
    if x == 0 and y == 0:
        return 1.0 - lam * mu * rho
    if x == 1 and y == 0:
        return 1.0 + mu * rho
    if x == 0 and y == 1:
        return 1.0 + lam * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


class GoalsPredictor(BasePredictor):
    """
    Poisson-based match outcome model.

    Attack and defense strengths are computed per team relative to the league
    average of the league they played in, so Eliteserien and OBOS-ligaen
    averages are kept separate.

    Each team's strength indices are normalised against their own league's
    averages, not the home team's league. When the two teams are from different
    leagues, a quality scaling factor (set via set_league_quality()) adjusts
    the expected goals to account for the strength gap between leagues:

        quality_scale = quality[home_league] / quality[away_league]
        λ_home = home_attack × away_defense × home_league_home_avg × quality_scale
        λ_away = away_attack × home_defense × home_league_away_avg / quality_scale

    quality values are in [0, 1] with 1.0 = strongest league. When both teams
    are from the same league, quality_scale = 1.0 and behaviour is unchanged.

    H/D/A probabilities are derived by summing the joint Poisson probability
    mass over all (i, j) score pairs up to _MAX_GOALS.
    """

    def __init__(self, min_matches: int = 3, rho: float = _DC_RHO, xg_blend: float = 1.0):
        self._min_matches = min_matches
        self._rho = rho
        # xg_blend: weight given to xG vs actual goals when xG is available.
        # 1.0 = pure xG, 0.0 = pure goals, 0.6 = 60% xG + 40% goals.
        self._xg_blend = xg_blend
        # Per-team home/away stats (goals scored/conceded, match count)
        self._home_stats: Dict[str, Dict] = {}
        self._away_stats: Dict[str, Dict] = {}
        # Per-league goal averages: {league_id: {"home": float, "away": float}}
        self._league_avgs: Dict[int, Dict[str, float]] = {}
        # Most recent league each team has appeared in
        self._team_league: Dict[str, int] = {}
        # Relative league quality: {league_id: float in (0, 1]}, strongest = 1.0
        # Empty dict means no cross-league adjustment is applied.
        self._league_quality: Dict[int, float] = {}
        # Per-team draw tendency relative to league average (1.0 = average)
        self._draw_tendency: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _blend(self, xg: Optional[float], goals: int) -> float:
        """Returns blended effective goals: alpha*xG + (1-alpha)*goals when xG is valid."""
        if xg is not None and xg > 0:
            return self._xg_blend * xg + (1.0 - self._xg_blend) * goals
        return float(goals)

    @staticmethod
    def _time_weight(match_date: datetime) -> float:
        """Matches decay in influence the further back in time they are, mirroring
        the EloPredictor's K-factor decay: w = 1 / log(days + 10)."""
        ref = datetime.now(timezone.utc)
        if match_date.tzinfo is None:
            match_date = match_date.replace(tzinfo=timezone.utc)
        days = max((ref - match_date).days, 1)
        return 1.0 / math.log(days + 10)

    def train(self, matches: List[HistoricalMatch]) -> None:
        # Weighted sums: each goal contribution is scaled by the match's time weight.
        # "n" is a raw match count kept only for the min_matches eligibility check.
        home_stats: Dict[str, Dict] = defaultdict(lambda: {"scored": 0.0, "conceded": 0.0, "weight": 0.0, "n": 0})
        away_stats: Dict[str, Dict] = defaultdict(lambda: {"scored": 0.0, "conceded": 0.0, "weight": 0.0, "n": 0})
        # league_id -> weighted goal totals
        league_totals: Dict[int, Dict] = defaultdict(lambda: {"home_goals": 0.0, "away_goals": 0.0, "weight": 0.0})
        # Track the most recent league per team (by date)
        team_latest: Dict[str, Tuple] = {}  # team -> (date, league_id)

        for m in sorted(matches, key=lambda x: x.date):
            w = self._time_weight(m.date)
            hg = self._blend(m.home_xg, m.home_goals)
            ag = self._blend(m.away_xg, m.away_goals)

            home_stats[m.home_team]["scored"]   += hg * w
            home_stats[m.home_team]["conceded"] += ag * w
            home_stats[m.home_team]["weight"]   += w
            home_stats[m.home_team]["n"]        += 1

            away_stats[m.away_team]["scored"]   += ag * w
            away_stats[m.away_team]["conceded"] += hg * w
            away_stats[m.away_team]["weight"]   += w
            away_stats[m.away_team]["n"]        += 1

            if m.league_id is not None:
                league_totals[m.league_id]["home_goals"] += hg * w
                league_totals[m.league_id]["away_goals"] += ag * w
                league_totals[m.league_id]["weight"]     += w

                for team in (m.home_team, m.away_team):
                    prev = team_latest.get(team)
                    if prev is None or m.date > prev[0]:
                        team_latest[team] = (m.date, m.league_id)

        self._home_stats = dict(home_stats)
        self._away_stats = dict(away_stats)
        self._team_league = {team: info[1] for team, info in team_latest.items()}

        self._league_avgs = {}
        for league_id, totals in league_totals.items():
            w = totals["weight"]
            self._league_avgs[league_id] = {
                "home": totals["home_goals"] / w if w > 0 else _DEFAULT_HOME_AVG,
                "away": totals["away_goals"] / w if w > 0 else _DEFAULT_AWAY_AVG,
            }

        # Per-team draw tendency (uses actual goals, not xG)
        draw_stats: Dict[str, Dict] = defaultdict(lambda: {"draws": 0.0, "weight": 0.0})
        for m in sorted(matches, key=lambda x: x.date):
            w = self._time_weight(m.date)
            is_draw = float(m.home_goals == m.away_goals)
            draw_stats[m.home_team]["draws"]  += is_draw * w
            draw_stats[m.home_team]["weight"] += w
            draw_stats[m.away_team]["draws"]  += is_draw * w
            draw_stats[m.away_team]["weight"] += w

        total_w = sum(v["weight"] for v in draw_stats.values())
        total_d = sum(v["draws"]  for v in draw_stats.values())
        league_draw_rate = (total_d / total_w) if total_w > 0 else 0.22

        self._draw_tendency = {
            team: (s["draws"] / s["weight"]) / league_draw_rate
            if s["weight"] > 0 and league_draw_rate > 0 else _DEFAULT_DRAW_TENDENCY
            for team, s in draw_stats.items()
        }

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def set_league_quality(self, quality: Dict[int, float]) -> None:
        """
        Set relative league quality factors, normalised so the strongest league = 1.0.
        Typically derived from empirical average ELO ratings after training.
        Call this after train() when cross-league predictions are expected.
        """
        self._league_quality = dict(quality)

    def _compute_lambdas(self, home_team: str, away_team: str) -> Optional[Tuple[float, float]]:
        h = self._home_stats.get(home_team)
        a = self._away_stats.get(away_team)
        if h is None or a is None:
            return None
        if h["n"] < self._min_matches or a["n"] < self._min_matches:
            return None

        home_league_id = self._team_league.get(home_team)
        away_league_id = self._team_league.get(away_team)
        home_avgs = self._league_avgs.get(home_league_id, _DEFAULT_AVGS)
        away_avgs = self._league_avgs.get(away_league_id, _DEFAULT_AVGS)

        home_attack  = (h["scored"]   / h["weight"]) / home_avgs["home"]
        home_defense = (h["conceded"] / h["weight"]) / home_avgs["away"]
        away_attack  = (a["scored"]   / a["weight"]) / away_avgs["away"]
        away_defense = (a["conceded"] / a["weight"]) / away_avgs["home"]

        quality_scale = 1.0
        if home_league_id != away_league_id and self._league_quality:
            q_home = self._league_quality.get(home_league_id, 1.0)
            q_away = self._league_quality.get(away_league_id, 1.0)
            quality_scale = q_home / q_away

        lambda_home = home_attack * away_defense * home_avgs["home"] * quality_scale
        lambda_away = away_attack * home_defense * home_avgs["away"] / quality_scale
        return lambda_home, lambda_away

    def predict(self, home_team: str, away_team: str) -> Optional[Prediction]:
        lambdas = self._compute_lambdas(home_team, away_team)
        if lambdas is None:
            return None
        lambda_home, lambda_away = lambdas

        home_prob, draw_prob, away_prob = self._outcome_probs(lambda_home, lambda_away, self._rho)

        # Draw tendency: boost/reduce draw probability based on how often each
        # team historically draws relative to the league average.
        home_tend = self._draw_tendency.get(home_team, _DEFAULT_DRAW_TENDENCY)
        away_tend = self._draw_tendency.get(away_team, _DEFAULT_DRAW_TENDENCY)
        combined  = (home_tend + away_tend) / 2.0
        adj_draw  = draw_prob * combined
        delta     = adj_draw - draw_prob
        total_ha  = home_prob + away_prob
        if total_ha > 0:
            home_prob -= delta * home_prob / total_ha
            away_prob -= delta * away_prob / total_ha
            home_prob  = max(home_prob, 0.0)
            away_prob  = max(away_prob, 0.0)
        draw_prob = max(adj_draw, 0.0)

        total = home_prob + draw_prob + away_prob
        if total > 0:
            home_prob /= total
            draw_prob /= total
            away_prob /= total

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

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _outcome_probs(lam_h: float, lam_a: float, rho: float = _DC_RHO) -> Tuple[float, float, float]:
        home_prob = draw_prob = away_prob = 0.0
        for i in range(_MAX_GOALS + 1):
            p_i = _poisson_pmf(lam_h, i)
            for j in range(_MAX_GOALS + 1):
                p = p_i * _poisson_pmf(lam_a, j) * _dc_correction(i, j, lam_h, lam_a, rho)
                if i > j:
                    home_prob += p
                elif i < j:
                    away_prob += p
                else:
                    draw_prob += p
        # Renormalise — the correction breaks exact summation to 1
        total = home_prob + draw_prob + away_prob
        if total > 0:
            home_prob /= total
            draw_prob /= total
            away_prob /= total
        return home_prob, draw_prob, away_prob
