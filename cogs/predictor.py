import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from api.fotmob import get_remaining_fixtures
from misc.constants import LEAGUES, TEAMS
from predictor.simulator import Fixture, SeasonSimulator, TeamStanding, format_sim_result, standings_from_rows


class PredictorCog(commands.Cog, name="Predictor"):
    """Slash commands for match outcome predictions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _team_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=team, value=team)
            for team in TEAMS
            if current.lower() in team.lower()
        ][:25]

    @app_commands.command(name="predict", description="Predict the outcome of a match between two teams.")
    @app_commands.autocomplete(home_team=_team_autocomplete, away_team=_team_autocomplete)
    async def predict(self, interaction: discord.Interaction, home_team: str, away_team: str):
        predictor = getattr(self.bot, "predictor", None)
        if predictor is None:
            await interaction.response.send_message("Predictor is not available.", ephemeral=True)
            return

        if home_team == away_team:
            await interaction.response.send_message("Home and away team must be different.", ephemeral=True)
            return

        prediction = predictor.predict(home_team, away_team)
        if prediction is None:
            await interaction.response.send_message(
                f"Not enough historical data to predict **{home_team}** vs **{away_team}**.",
                ephemeral=True,
            )
            return

        outcome_labels = {"H": f"Hjemmeseier ({home_team})", "D": "Uavgjort", "A": f"Borteseier ({away_team})"}
        lines = [
            f"**{home_team}** vs **{away_team}**",
            f"H {prediction.home_prob:.0%} · U {prediction.draw_prob:.0%} · B {prediction.away_prob:.0%}",
            f"🤖 Tipping: **{outcome_labels[prediction.outcome]}** ({prediction.confidence:.0%})",
        ]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="simulate", description="Simuler resten av sesongen og vis sluttabell-prognose.")
    @app_commands.describe(league="Ligaen som skal simuleres")
    @app_commands.choices(league=[
        app_commands.Choice(name="Eliteserien", value="ELITE"),
        app_commands.Choice(name="OBOS-ligaen", value="OBOS"),
    ])
    async def simulate(self, interaction: discord.Interaction, league: str = "ELITE"):
        predictor = getattr(self.bot, "predictor", None)
        if predictor is None:
            await interaction.response.send_message("Predictor er ikke tilgjengelig.", ephemeral=True)
            return

        await interaction.response.defer()

        config = LEAGUES[league]
        league_id = config["id"]
        slug = config["slug"]
        season = config["season"]

        # Build current standings from cached historical data
        db = getattr(self.bot, "db", None)
        if db is None:
            await interaction.followup.send("Databasen er ikke tilgjengelig.", ephemeral=True)
            return

        all_rows = db.get_historical_matches()
        season_rows = [r for r in all_rows if r["league_id"] == league_id and r["season"] == season]
        standings = standings_from_rows(season_rows)

        if not standings:
            await interaction.followup.send(
                f"Ingen kampdata funnet for {config['name']} {season}.", ephemeral=True
            )
            return

        # Fetch remaining fixtures from FotMob (blocking network call → executor)
        loop = asyncio.get_event_loop()
        try:
            raw = await loop.run_in_executor(None, get_remaining_fixtures, league_id, slug)
        except Exception as e:
            await interaction.followup.send(f"Kunne ikke hente gjenstående kamper: {e}", ephemeral=True)
            return

        fixtures = [Fixture(home_team=f["home_team"], away_team=f["away_team"]) for f in raw]

        # Teams that haven't played yet won't appear in standings_from_rows.
        # Add them with zeroed stats so they're included in the simulation.
        known_teams = {s.team for s in standings}
        for f in fixtures:
            for team in (f.home_team, f.away_team):
                if team not in known_teams:
                    standings.append(TeamStanding(
                        team=team, played=0, won=0, drawn=0, lost=0,
                        goals_for=0, goals_against=0,
                    ))
                    known_teams.add(team)

        if not fixtures:
            await interaction.followup.send(
                f"Ingen gjenstående kamper funnet for {config['name']} {season}.", ephemeral=True
            )
            return

        # League-specific zone sizes and labels
        if league == "ELITE":
            top_n, bottom_m = 3, 2
            top_label, bottom_label = "Europa", "Nedrykk"
        else:
            top_n, bottom_m = 2, 3
            top_label, bottom_label = "Opprykk", "Nedrykk"

        simulator = SeasonSimulator(predictor)
        result = await loop.run_in_executor(
            None,
            lambda: simulator.simulate(standings, fixtures, top_n=top_n, bottom_m=bottom_m),
        )

        msg = format_sim_result(result, config["name"], top_label=top_label, bottom_label=bottom_label)
        await interaction.followup.send(msg)
