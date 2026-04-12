from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from predictor.base import BasePredictor, HistoricalMatch, Prediction


class FormPredictor(BasePredictor):
    """
    Predicts match outcomes from three form signals, each blended by weight:

    1. Overall recent form — each team's last N matches regardless of venue,
       capturing momentum and streaks.
    2. H2H overall — all historical meetings between the two teams regardless
       of which was home, from the home team's perspective.
    3. H2H at venue — meetings where today's home team was also home, giving
       a venue-specific head-to-head signal.

    Older matches are discounted exponentially within each signal.
    """

    def __init__(
        self,
        form_window: int = 6,
        decay_factor: float = 0.85,
        w_form: float = 0.5,
        w_h2h_overall: float = 0.3,
        w_h2h_venue: float = 0.2,
    ):
        """
        form_window:    number of recent matches considered for overall form
        decay_factor:   multiplier applied per match back in time (0 < decay < 1)
        w_form:         weight for overall recent form signal
        w_h2h_overall:  weight for H2H overall signal
        w_h2h_venue:    weight for H2H at this venue signal
        """
        self._form_window   = form_window
        self._decay_factor  = decay_factor
        self._w_form        = w_form
        self._w_h2h_overall = w_h2h_overall
        self._w_h2h_venue   = w_h2h_venue

        # All matches per team (chronological), storing (match, team_perspective)
        # where team_perspective is "home" or "away" so we know which outcome = win.
        self._all_history: Dict[str, List[Tuple[HistoricalMatch, str]]] = defaultdict(list)

        # Venue-specific H2H: keyed by (home_team, away_team)
        self._h2h_venue: Dict[Tuple[str, str], List[HistoricalMatch]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, matches: List[HistoricalMatch]) -> None:
        self._all_history.clear()
        self._h2h_venue.clear()

        for m in sorted(matches, key=lambda x: x.date):
            self._all_history[m.home_team].append((m, "home"))
            self._all_history[m.away_team].append((m, "away"))
            self._h2h_venue[(m.home_team, m.away_team)].append(m)

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, home_team: str, away_team: str) -> Optional[Prediction]:
        home_history = self._all_history.get(home_team, [])
        away_history = self._all_history.get(away_team, [])

        if len(home_history) < 2 or len(away_history) < 2:
            return None

        # --- 1. Overall recent form ---
        # Home team: their win/draw/loss rate from their own perspective
        home_win  = self._overall_rate(home_history, "win")
        home_draw = self._overall_rate(home_history, "draw")
        home_loss = self._overall_rate(home_history, "loss")

        # Away team: their win/draw/loss rate from their own perspective
        away_win  = self._overall_rate(away_history, "win")
        away_draw = self._overall_rate(away_history, "draw")
        away_loss = self._overall_rate(away_history, "loss")

        # Combine: home team wins if they win AND away team loses, etc.
        form_h = (home_win  + away_loss) / 2
        form_d = (home_draw + away_draw) / 2
        form_a = (home_loss + away_win)  / 2
        form_h, form_d, form_a = self._normalize(form_h, form_d, form_a)

        home_prob, draw_prob, away_prob = form_h, form_d, form_a
        total_w = self._w_form

        # --- 2. H2H overall (both directions, from home team's perspective) ---
        h2h_all = self._h2h_all_matches(home_team, away_team)
        if len(h2h_all) >= 2:
            h2h_h, h2h_d, h2h_a = self._h2h_probs_from_home_perspective(h2h_all, home_team)
            home_prob += self._w_h2h_overall * h2h_h
            draw_prob += self._w_h2h_overall * h2h_d
            away_prob += self._w_h2h_overall * h2h_a
            total_w   += self._w_h2h_overall

        # --- 3. H2H at this venue ---
        h2h_venue = self._h2h_venue.get((home_team, away_team), [])
        if len(h2h_venue) >= 2:
            vh = self._weighted_outcome_rate(h2h_venue, "H")
            vd = self._weighted_outcome_rate(h2h_venue, "D")
            va = self._weighted_outcome_rate(h2h_venue, "A")
            vh, vd, va = self._normalize(vh, vd, va)
            home_prob += self._w_h2h_venue * vh
            draw_prob += self._w_h2h_venue * vd
            away_prob += self._w_h2h_venue * va
            total_w   += self._w_h2h_venue

        if total_w == 0:
            return None
        home_prob /= total_w
        draw_prob /= total_w
        away_prob /= total_w
        home_prob, draw_prob, away_prob = self._normalize(home_prob, draw_prob, away_prob)

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

    def _overall_rate(self, history: List[Tuple[HistoricalMatch, str]], result: str) -> float:
        """
        Exponentially weighted rate of `result` ("win"/"draw"/"loss") in the
        team's last form_window matches, from the team's own perspective.
        """
        recent = history[-self._form_window:]
        total = hits = 0.0
        for i, (m, perspective) in enumerate(reversed(recent)):
            w = self._decay_factor ** i
            total += w
            outcome = m.outcome  # "H", "D", or "A" from home team's perspective
            won  = (perspective == "home" and outcome == "H") or (perspective == "away" and outcome == "A")
            drew = outcome == "D"
            lost = (perspective == "home" and outcome == "A") or (perspective == "away" and outcome == "H")
            if (result == "win" and won) or (result == "draw" and drew) or (result == "loss" and lost):
                hits += w
        return hits / total if total > 0 else 0.0

    def _h2h_all_matches(self, home_team: str, away_team: str) -> List[Tuple[HistoricalMatch, bool]]:
        """
        All historical meetings between the two teams, annotated with whether
        home_team was the home side in that match.
        """
        result = []
        for m in self._h2h_venue.get((home_team, away_team), []):
            result.append((m, True))   # home_team was home
        for m in self._h2h_venue.get((away_team, home_team), []):
            result.append((m, False))  # home_team was away
        result.sort(key=lambda x: x[0].date)
        return result

    def _h2h_probs_from_home_perspective(
        self,
        h2h_all: List[Tuple[HistoricalMatch, bool]],
        home_team: str,
    ) -> Tuple[float, float, float]:
        """
        Weighted H/D/A rates for home_team across all historical meetings,
        regardless of which side was home.
        """
        recent = h2h_all[-self._form_window:]
        h = d = a = total = 0.0
        for i, (m, home_team_was_home) in enumerate(reversed(recent)):
            w = self._decay_factor ** i
            total += w
            if m.outcome == "D":
                d += w
            elif (m.outcome == "H") == home_team_was_home:
                h += w   # home_team won
            else:
                a += w   # home_team lost
        if total == 0:
            return 1/3, 1/3, 1/3
        return self._normalize(h / total, d / total, a / total)

    def _weighted_outcome_rate(self, matches: List[HistoricalMatch], outcome: str) -> float:
        """Exponentially weighted rate of `outcome` in the most recent form_window matches."""
        recent = matches[-self._form_window:]
        total = hits = 0.0
        for i, m in enumerate(reversed(recent)):
            w = self._decay_factor ** i
            total += w
            if m.outcome == outcome:
                hits += w
        return hits / total if total > 0 else 0.0

    @staticmethod
    def _normalize(h: float, d: float, a: float) -> Tuple[float, float, float]:
        total = h + d + a
        if total == 0:
            return 1/3, 1/3, 1/3
        return h / total, d / total, a / total
