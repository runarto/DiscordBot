import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from predictor.base import BasePredictor


@dataclass
class TeamStanding:
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


@dataclass
class Fixture:
    home_team: str
    away_team: str


@dataclass
class SimResult:
    n_sims: int
    standings: List[TeamStanding]  # initial standings, sorted by points desc
    avg_pts: Dict[str, float]
    title_pct: Dict[str, float]
    top_n_pct: Dict[str, float]
    bottom_m_pct: Dict[str, float]
    top_n: int
    bottom_m: int


def standings_from_rows(rows: List[Dict]) -> List[TeamStanding]:
    """
    Builds a sorted standings list from raw historical_match DB rows
    (already filtered to the desired league and season by the caller).
    """
    stats: Dict[str, Dict] = defaultdict(lambda: {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0})

    for row in rows:
        home = row["home_team"]
        away = row["away_team"]
        hg = row["home_goals"]
        ag = row["away_goals"]

        stats[home]["gf"] += hg
        stats[home]["ga"] += ag
        stats[away]["gf"] += ag
        stats[away]["ga"] += hg

        if hg > ag:
            stats[home]["w"] += 1
            stats[away]["l"] += 1
        elif hg < ag:
            stats[away]["w"] += 1
            stats[home]["l"] += 1
        else:
            stats[home]["d"] += 1
            stats[away]["d"] += 1

    standings = [
        TeamStanding(
            team=team,
            played=s["w"] + s["d"] + s["l"],
            won=s["w"],
            drawn=s["d"],
            lost=s["l"],
            goals_for=s["gf"],
            goals_against=s["ga"],
        )
        for team, s in stats.items()
    ]

    standings.sort(
        key=lambda s: (s.points, s.goal_diff, s.goals_for),
        reverse=True,
    )
    return standings


class SeasonSimulator:

    def __init__(self, predictor: BasePredictor, n_sims: int = 10_000):
        self._predictor = predictor
        self._n_sims = n_sims

    def simulate(
        self,
        standings: List[TeamStanding],
        fixtures: List[Fixture],
        top_n: int = 3,
        bottom_m: int = 2,
    ) -> SimResult:
        teams = [s.team for s in standings]
        n_teams = len(teams)
        base_pts = {s.team: s.points for s in standings}
        base_gd = {s.team: s.goal_diff for s in standings}
        base_gf = {s.team: s.goals_for for s in standings}

        # Precompute match probabilities once to avoid repeated predictor calls
        probs = []
        for f in fixtures:
            pred = self._predictor.predict(f.home_team, f.away_team)
            if pred is not None:
                probs.append((f.home_team, f.away_team, pred.home_prob, pred.draw_prob))
            else:
                probs.append((f.home_team, f.away_team, 1 / 3, 1 / 3))

        pts_sum: Dict[str, float] = defaultdict(float)
        title_count: Dict[str, int] = defaultdict(int)
        top_count: Dict[str, int] = defaultdict(int)
        bottom_count: Dict[str, int] = defaultdict(int)

        for _ in range(self._n_sims):
            pts = dict(base_pts)

            for home, away, hp, dp in probs:
                r = random.random()
                if r < hp:
                    pts[home] = pts.get(home, 0) + 3
                elif r < hp + dp:
                    pts[home] = pts.get(home, 0) + 1
                    pts[away] = pts.get(away, 0) + 1
                else:
                    pts[away] = pts.get(away, 0) + 3

            ranked = sorted(
                teams,
                key=lambda t: (pts.get(t, 0), base_gd[t], base_gf[t]),
                reverse=True,
            )

            for i, t in enumerate(ranked):
                pts_sum[t] += pts.get(t, 0)
                if i == 0:
                    title_count[t] += 1
                if i < top_n:
                    top_count[t] += 1
                if i >= n_teams - bottom_m:
                    bottom_count[t] += 1

        n = self._n_sims
        return SimResult(
            n_sims=n,
            standings=standings,
            avg_pts={t: pts_sum[t] / n for t in teams},
            title_pct={t: title_count[t] / n for t in teams},
            top_n_pct={t: top_count[t] / n for t in teams},
            bottom_m_pct={t: bottom_count[t] / n for t in teams},
            top_n=top_n,
            bottom_m=bottom_m,
        )


def format_sim_result(
    result: SimResult,
    league_name: str,
    top_label: str = "Europa",
    bottom_label: str = "Nedrykk",
) -> str:
    """
    Returns a Discord code-block table of simulation results, sorted by
    average simulated final points. Zone separators divide the European
    qualification places from the mid-table, and mid-table from the
    relegation zone.
    """
    n_teams = len(result.standings)
    top_n = result.top_n
    bottom_m = result.bottom_m

    sorted_teams = sorted(
        result.standings,
        key=lambda s: result.avg_pts[s.team],
        reverse=True,
    )

    n_str = f"{result.n_sims:,}".replace(",", "\u202f")  # narrow no-break space
    title_line = f"{league_name} \u2013 Sesongprognose ({n_str} sim.)"

    W = 18  # team name column width
    header = f"{'#':>2}  {'Lag':<{W}}  {'Pts':>3}  {'Snitt':>5}  {'1.plass':>7}  {top_label:>7}  {bottom_label:>7}"
    sep = "\u2500" * len(header)
    zone_sep = "\u00b7" * len(header)

    rows = []
    for i, s in enumerate(sorted_teams, 1):
        t = s.team
        if i == top_n + 1:
            rows.append(zone_sep)
        if i == n_teams - bottom_m + 1:
            rows.append(zone_sep)

        title_s = f"{result.title_pct[t]:.1%}" if result.title_pct[t] >= 0.001 else "  -  "
        top_s = f"{result.top_n_pct[t]:.1%}" if result.top_n_pct[t] >= 0.001 else "  -  "
        bot_s = f"{result.bottom_m_pct[t]:.1%}" if result.bottom_m_pct[t] >= 0.001 else "  -  "

        rows.append(
            f"{i:>2}  {t:<{W}}  {s.points:>3}  {result.avg_pts[t]:>5.1f}"
            f"  {title_s:>7}  {top_s:>7}  {bot_s:>7}"
        )

    body = "\n".join([title_line, "", header, sep] + rows)
    return f"```\n{body}\n```"
