import math
from collections import defaultdict
from datetime import datetime, timezone
from itertools import groupby
from typing import Dict, List, Optional

from predictor.base import BasePredictor, HistoricalMatch, Prediction
from misc.constants import LEAGUES

_INITIAL_RATING     = 1500.0  # all teams start here; the gap between leagues emerges from results

_LEAGUE_WEIGHTS: Dict[int, float] = {
    LEAGUES["ELITE"]["id"]: 1.0,
    LEAGUES["OBOS"]["id"]:  0.79,
    LEAGUES["Cupen"]["id"]: 0.7,   # 206 — cross-league cup matches calibrate the strength gap
}

# Cup league IDs are excluded from team-league attribution and regression logic.
# Cup matches still update ELO ratings directly but should not be treated as
# league transitions (to avoid spurious regression and wrong initial-rating assignment).
_CUP_LEAGUE_IDS: set = {LEAGUES["Cupen"]["id"]}

_K_FACTOR          = 6.5
_THETA             = 200.0   # scaling divisor in probability formula
_K_DRAW            = 0.22    # draw constant in three-way probability split
_SEASON_REGRESS    = 0.15    # end-of-season pull toward league mean (prevents OBOS pool inflation)


class EloPredictor(BasePredictor):
    """
    ELO rating system ported from football-prediksjons-modell.

    Faithful adaptation of EloRatingSystem with the following changes:
      - League IDs mapped to this project's values (59 / 203 instead of 103 / 104)
      - team_strengths (home/away win rates for HFA) computed from HistoricalMatch
        objects during train() rather than fetched from a separate database
      - Reference date for time decay is datetime.now() so 2025 data is always
        weighted more heavily than 2024 data regardless of when the bot runs
      - No h2h_adjustment (set to 0) and no form bonus — those are simulation
        features in the original that don't apply to single-match prediction
      - After training, empirical average ELO per league is computed and exposed
        via league_avg_elos for use by other predictors (e.g. GoalsPredictor)
    """

    def __init__(self, k_factor: float = _K_FACTOR):
        self._k_factor = k_factor
        self._ratings: Dict[str, float] = {}
        self._home_strengths: Dict[str, float] = {}  # home win rate per team
        self._away_strengths: Dict[str, float] = {}  # away win rate per team
        self._league_avg_elos: Dict[int, float] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def ratings(self) -> Dict[str, float]:
        return dict(self._ratings)

    @property
    def league_avg_elos(self) -> Dict[int, float]:
        """Empirical average ELO per league, computed after training."""
        return dict(self._league_avg_elos)

    def train(self, matches: List[HistoricalMatch]) -> None:
        sorted_matches = sorted(matches, key=lambda x: x.date)

        # Track each team's final league for league_avg_elos (step 4).
        # Cup matches are skipped so teams are attributed to their actual league.
        team_latest_league: Dict[str, int] = {}
        for m in sorted_matches:
            if m.league_id is not None and m.league_id not in _CUP_LEAGUE_IDS:
                team_latest_league[m.home_team] = m.league_id
                team_latest_league[m.away_team] = m.league_id

        all_teams = {t for m in sorted_matches for t in (m.home_team, m.away_team)}

        # --- 1. Two-pass initialisation ---
        # Pass A: flat start → discover empirical league gap via season-by-season
        # processing with end-of-season mean reversion.
        self._ratings = {team: _INITIAL_RATING for team in all_teams}
        self._run_season_pass(sorted_matches)

        league_teams: Dict[int, List[str]] = defaultdict(list)
        for team, league_id in team_latest_league.items():
            league_teams[league_id].append(team)
        data_derived_initials = {
            league_id: sum(self._ratings[t] for t in teams) / len(teams)
            for league_id, teams in league_teams.items()
            if teams
        }

        # Pass B: reset to data-derived league averages, retrain with reversion.
        self._ratings = {
            team: data_derived_initials.get(team_latest_league.get(team), _INITIAL_RATING)
            for team in all_teams
        }

        # --- 2. Compute home/away win rates (used for HFA calculation) ---
        home_stats: Dict[str, Dict] = defaultdict(lambda: {"wins": 0, "n": 0})
        away_stats: Dict[str, Dict] = defaultdict(lambda: {"wins": 0, "n": 0})
        for m in sorted_matches:
            home_stats[m.home_team]["n"] += 1
            away_stats[m.away_team]["n"] += 1
            if m.outcome == "H":
                home_stats[m.home_team]["wins"] += 1
            elif m.outcome == "A":
                away_stats[m.away_team]["wins"] += 1

        self._home_strengths = {
            t: s["wins"] / s["n"] for t, s in home_stats.items() if s["n"] > 0
        }
        self._away_strengths = {
            t: s["wins"] / s["n"] for t, s in away_stats.items() if s["n"] > 0
        }

        # --- 3. Process matches with end-of-season mean reversion ---
        self._run_season_pass(sorted_matches)

        # --- 4. Derive empirical average ELO per league ---
        self._league_avg_elos = {
            league_id: sum(self._ratings[t] for t in teams) / len(teams)
            for league_id, teams in league_teams.items()
            if teams
        }

    def _run_season_pass(self, sorted_matches: List[HistoricalMatch]) -> None:
        """Process matches season-by-season, applying end-of-season mean reversion.

        After each season's matches are processed, every team is pulled 15%
        toward their current league's mean rating.  This prevents a team that
        dominates one league from floating far above mid-table teams in the
        stronger league, while still rewarding genuine outperformance.
        """
        team_current_league: Dict[str, int] = {}

        for _year, season_iter in groupby(sorted_matches, key=lambda m: m.date.year):
            season = list(season_iter)

            for m in season:
                if m.league_id is not None and m.league_id not in _CUP_LEAGUE_IDS:
                    team_current_league[m.home_team] = m.league_id
                    team_current_league[m.away_team] = m.league_id
                self._process_match(m)

            # Compute per-league means from teams seen so far
            league_teams: Dict[int, List[str]] = defaultdict(list)
            for team, league_id in team_current_league.items():
                if team in self._ratings:
                    league_teams[league_id].append(team)

            for league_id, teams in league_teams.items():
                mean = sum(self._ratings[t] for t in teams) / len(teams)
                for team in teams:
                    self._ratings[team] += _SEASON_REGRESS * (mean - self._ratings[team])

    def predict(self, home_team: str, away_team: str) -> Optional[Prediction]:
        if home_team not in self._ratings or away_team not in self._ratings:
            return None

        r_home = self._ratings[home_team]
        r_away = self._ratings[away_team]
        home_advantage = self._hfa(home_team, away_team)

        probs = self._calculate_match_probabilities(r_home, r_away, home_advantage)
        outcome = max(probs, key=probs.get)

        return Prediction(
            home_team=home_team,
            away_team=away_team,
            outcome=outcome,
            confidence=probs[outcome],
            home_prob=probs["H"],
            draw_prob=probs["D"],
            away_prob=probs["A"],
        )

    # ------------------------------------------------------------------
    # Core logic (mirrors EloRatingSystem methods exactly)
    # ------------------------------------------------------------------

    def _process_match(self, m: HistoricalMatch) -> None:
        """Mirror of EloRatingSystem.process_game()."""
        home, away = m.home_team, m.away_team

        if home not in self._ratings:
            self._ratings[home] = _INITIAL_RATING
        if away not in self._ratings:
            self._ratings[away] = _INITIAL_RATING

        r_home = self._ratings[home]
        r_away = self._ratings[away]

        home_advantage = self._hfa(home, away)

        # Expected scores — calculate_expected_score()
        expected_home = self._calculate_expected_score(r_home, r_away, home_advantage)
        expected_away = 1.0 - expected_home

        # Actual scores (binary, matching the 0.12 threshold from the original)
        diff = m.home_goals - m.away_goals
        if diff > 0:
            actual_home, actual_away = 1.0, 0.0
        elif diff < 0:
            actual_home, actual_away = 0.0, 1.0
        else:
            actual_home = actual_away = 0.5

        # League weight → adjusted K → decay factor
        league_weight = _LEAGUE_WEIGHTS.get(m.league_id, 1.0) if m.league_id is not None else 1.0
        adjusted_k = self._k_factor * league_weight
        decay_factor = self._get_decay_factor(adjusted_k, m.date)

        # Goal difference multiplier (from process_game())
        goal_diff = abs(m.home_goals - m.away_goals)
        goal_multiplier = math.log(goal_diff + 5) if goal_diff > 0 else 1.0
        goal_multiplier *= 2.2 / ((abs(r_home - r_away) * 0.001) + 2.2)

        final_k = self._k_factor * goal_multiplier

        self._ratings[home] = r_home + final_k * decay_factor * (actual_home - expected_home)
        self._ratings[away] = r_away + final_k * decay_factor * (actual_away - expected_away)

    def _hfa(self, home_team: str, away_team: str) -> float:
        """Home field advantage in ELO points, mirroring process_game() HFA block."""
        hfa = self._home_strengths.get(home_team, 0.5) * 100
        afa = self._away_strengths.get(away_team, 0.5) * 100
        return hfa + (hfa - afa) / 2

    def _calculate_expected_score(self, rating_a: float, rating_b: float, hfa: float) -> float:
        """Mirror of EloRatingSystem.calculate_expected_score()."""
        exponent = (rating_b - rating_a + hfa) / 400.0
        return 1.0 / (1.0 + 10.0 ** exponent)

    def _get_decay_factor(self, adjusted_k: float, match_date: datetime) -> float:
        """Mirror of helper.get_decay_factor() with use_fixed_reference_date=False."""
        ref = datetime.now(timezone.utc)
        if match_date.tzinfo is None:
            match_date = match_date.replace(tzinfo=timezone.utc)
        days = max((ref - match_date).days, 1)
        return adjusted_k / math.log(days + 10)

    def _calculate_match_probabilities(
        self,
        rating_home: float,
        rating_away: float,
        home_advantage: float,
        h2h_adjustment: float = 0.0,
    ) -> Dict[str, float]:
        """Mirror of EloRatingSystem.calculate_match_probabilities()."""
        delta_R = rating_home + home_advantage + h2h_adjustment - rating_away
        exp_pos = math.exp(delta_R / _THETA)
        exp_neg = math.exp(-delta_R / _THETA)
        denominator = exp_pos + exp_neg + _K_DRAW
        return {
            "H": exp_pos / denominator,
            "D": _K_DRAW / denominator,
            "A": exp_neg / denominator,
        }
