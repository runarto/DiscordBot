"""
Calibrates the Dixon-Coles ρ parameter by maximising log-likelihood of
actual match scores given the GoalsPredictor's trained λ values.
"""
import math
from typing import List, Optional

from predictor.base import HistoricalMatch
from predictor.goals import GoalsPredictor, _poisson_pmf, _dc_correction


def calibrate_rho(
    goals_pred: GoalsPredictor,
    matches: List[HistoricalMatch],
    rho_min: float = -0.50,
    rho_max: float = 0.05,
    steps: int = 110,
) -> float:
    """
    Grid-searches ρ in [rho_min, rho_max] and returns the value that maximises
    the sum of log P(actual_score | λ_home, λ_away, ρ) over all matches for
    which the predictor has sufficient data.

    Uses actual goals (not xG) since the DC correction applies to scorelines.
    """
    step_size = (rho_max - rho_min) / steps
    rho_range = [rho_min + i * step_size for i in range(steps + 1)]

    best_rho, best_ll = rho_range[0], -math.inf

    for rho in rho_range:
        ll = 0.0
        for m in matches:
            lams = goals_pred._compute_lambdas(m.home_team, m.away_team)
            if lams is None:
                continue
            lam_h, lam_a = lams
            x, y = int(m.home_goals), int(m.away_goals)
            if x > 10 or y > 10:
                continue
            p = (
                _poisson_pmf(lam_h, x)
                * _poisson_pmf(lam_a, y)
                * _dc_correction(x, y, lam_h, lam_a, rho)
            )
            if p > 1e-10:
                ll += math.log(p)

        if ll > best_ll:
            best_ll = ll
            best_rho = rho

    return best_rho
