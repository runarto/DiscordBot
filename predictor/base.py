from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class HistoricalMatch:
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    date: datetime
    league_id: Optional[int] = None
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None

    @property
    def effective_home_goals(self) -> float:
        """xG when available and valid, otherwise actual goals."""
        if self.home_xg is not None and self.home_xg > 0:
            return self.home_xg
        return float(self.home_goals)

    @property
    def effective_away_goals(self) -> float:
        """xG when available and valid, otherwise actual goals."""
        if self.away_xg is not None and self.away_xg > 0:
            return self.away_xg
        return float(self.away_goals)

    @property
    def outcome(self) -> str:
        if self.home_goals > self.away_goals:
            return "H"
        if self.home_goals < self.away_goals:
            return "A"
        return "D"


@dataclass
class Prediction:
    home_team: str
    away_team: str
    outcome: str       # "H", "D", or "A"
    confidence: float  # probability of the predicted outcome (0.0–1.0)
    home_prob: float
    draw_prob: float
    away_prob: float


class BasePredictor(ABC):
    @abstractmethod
    def train(self, matches: List[HistoricalMatch]) -> None:
        """Feed historical match data to build the model."""
        ...

    @abstractmethod
    def predict(self, home_team: str, away_team: str) -> Optional[Prediction]:
        """Return a prediction for a matchup, or None if there is insufficient data."""
        ...
