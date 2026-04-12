from typing import List, Optional, Tuple

from predictor.base import BasePredictor, HistoricalMatch, Prediction


class EnsemblePredictor(BasePredictor):
    """
    Combines multiple predictors via a weighted average of their H/D/A probabilities.

    Predictors that return None for a given matchup (insufficient data) are
    excluded from that matchup's blend so the remaining predictors still contribute.
    If all predictors return None, predict() returns None.
    """

    def __init__(self, predictors: List[Tuple[BasePredictor, float]]):
        """
        predictors: list of (predictor, weight) pairs.
                    Weights need not sum to 1 — they are normalised at prediction time.
        """
        self._predictors = predictors

    def train(self, matches: List[HistoricalMatch]) -> None:
        for predictor, _ in self._predictors:
            predictor.train(matches)

    def predict(self, home_team: str, away_team: str) -> Optional[Prediction]:
        home_prob = draw_prob = away_prob = 0.0
        total_weight = 0.0

        for predictor, weight in self._predictors:
            p = predictor.predict(home_team, away_team)
            if p is None:
                continue
            home_prob += weight * p.home_prob
            draw_prob += weight * p.draw_prob
            away_prob += weight * p.away_prob
            total_weight += weight

        if total_weight == 0.0:
            return None

        home_prob /= total_weight
        draw_prob /= total_weight
        away_prob /= total_weight

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
