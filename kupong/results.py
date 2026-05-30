import discord
import os
import logging
import asyncio

from collections import Counter, defaultdict
from api.fotmob import get_fixture_result
from misc.utils import split_message_blocks, interpret_result
from misc.constants import LEAGUES
from db.db_interface import DB
from discord.ext import commands

_PREDICTION_OUTCOMES = ("H", "D", "A")
_WORLD_CUP_LEAGUE_KEY = "WORLD_CUP"


def world_cup_points_by_outcome(predictions) -> dict[str, int]:
    """
    Returns VM points per predicted outcome based on popularity.

    Most picked correct outcome gives 1 point, second-most gives 2, and
    least-picked gives 3. Ties share the same point value.
    """
    counts = Counter(
        prediction.prediction
        for prediction in predictions
        if prediction.prediction in _PREDICTION_OUTCOMES
    )
    ranked_counts = sorted({count for count in counts.values() if count > 0}, reverse=True)
    return {
        outcome: ranked_counts.index(count) + 1
        for outcome, count in counts.items()
    }


class Results:
    def __init__(self, bot: commands.Bot, db: DB, channel: discord.TextChannel, logger: logging.Logger, league_key: str):
        self._bot = bot
        self._auth = os.getenv('API_TOKEN')
        self._db = db
        self._channel = channel
        self._league_key = league_key
        self._league_config = LEAGUES[league_key]
        self._league_id = self._league_config["id"]
        self._matches = self._db.get_matches_by_league(self._league_id)
        self._old_scores = self._db.get_scores_by_league(self._league_id)
        self._previous_ranks = self._get_ranks()
        self._match_results = {}

    def _get_ranks(self) -> dict[int, int]:
        users = []
        for score in self._old_scores:
            user = self._db.get_user(score.user_id)
            if user:
                users.append((score.user_id, score.points, score.weekly_wins))

        users.sort(key=lambda x: (-x[1], -x[2]))  # sort by points DESC, wins DESC

        ranks = {}
        for i, (user_id, _, _) in enumerate(users):
            ranks[user_id] = i + 1
        return ranks


    def _fetch_match_results(self):
        """Fetches match results and stores them in a dictionary."""
        for match in self._matches:
            result = self._determine_fixture_result(match.match_id)
            if result != "NA":
                self._match_results[match.match_id] = result

    def _determine_fixture_result(self, match_id: int) -> str:
        fixture = get_fixture_result(match_id=match_id, league_id=self._league_id, slug=self._league_config["slug"])
        if fixture.status["short"] != "FT":
            return "NA"

        return interpret_result(fixture.result)
            
    def _increment_score(self):
        """Increments the score for users based on match results."""

        bot_user_id = str(self._bot.user.id)

        fixtures = self._matches
        for fixture in fixtures:
            predictions = self._db.get_all_predictions_for_match(fixture.message_id)
            result = self._match_results.get(fixture.match_id, "NA")
            if result == "NA":
                continue

            points_by_outcome = (
                world_cup_points_by_outcome(predictions)
                if self._league_key == _WORLD_CUP_LEAGUE_KEY
                else {}
            )

            for prediction in predictions:
                if prediction.prediction == result:
                    points = points_by_outcome.get(result, 1)
                    self._db.upsert_score(prediction.user_id, self._league_id, points_delta=points)

            # Score the bot from its stored prediction
            bot_pred = (
                None
                if self._league_key == _WORLD_CUP_LEAGUE_KEY
                else self._db.get_bot_prediction(fixture.match_id, self._league_id)
            )
            if bot_pred and bot_pred["outcome"] == result:
                if not self._db.get_user(bot_user_id):
                    self._db.insert_user(bot_user_id, self._bot.user.name, "🤖 Bot", None)
                self._db.upsert_score(bot_user_id, self._league_id, points_delta=1)

        weekly_scores = self._get_weekly_scores()

        if not weekly_scores:
            return

        # Determine max score and corresponding users
        max_score = max(weekly_scores.keys())
        top_users = weekly_scores[max_score]

        # Award weekly wins
        for user_id in top_users:
            self._db.upsert_score(user_id, self._league_id, win_delta=1)


    def _get_weekly_scores(self):
        old_scores = self._old_scores
        new_scores = self._db.get_scores_by_league(self._league_id)

        # Map old scores by user_id
        old_dict = {s.user_id: s.points for s in old_scores}

        weekly_points_to_users = defaultdict(list)

        for new in new_scores:
            old_points = old_dict.get(new.user_id, 0)  # defaults to 0 for new users
            weekly_points = new.points - old_points

            if weekly_points > 0:
                weekly_points_to_users[weekly_points].append(new.user_id)

        return dict(weekly_points_to_users)
    
    async def _format_weekly_leaderboard(self) -> str:
        weekly_scores = self._get_weekly_scores()
        if not weekly_scores:
            return "Ingen poeng ble delt ut denne uka."

        lines = []
        resolved_names: dict[str, str] = {}
        num_fixtures = len(self._match_results)

        # Sort scores descending
        lines.append(f"**Av {num_fixtures} mulige:**")
        for score in sorted(weekly_scores.keys(), reverse=True):
            user_ids = weekly_scores[score]
            names = []

            for uid in user_ids:
                try:
                    user = self._db.get_user(uid)
                    user_name = user.user_name
                    display_name = user.user_display_name 
                except AttributeError:
                    user = await self._bot.fetch_user(uid)
                    user_name = user.name
                    display_name = user.display_name

                resolved_names[uid] = user_name
                names.append(display_name)

            lines.append(f"{score} poeng: {', '.join(names)}")

        # Mention winners with @user_display_name
        top_score = max(weekly_scores.keys())
        top_user_ids = weekly_scores[top_score]
        users = await asyncio.gather(*(self._bot.fetch_user(uid) for uid in top_user_ids))
        mentions = [user.mention for user in users]

        if len(mentions) == 1:
            mention_str = mentions[0]
        elif len(mentions) == 2:
            mention_str = f"{mentions[0]} og {mentions[1]}"
        else:
            mention_str = ', '.join(mentions[:-1]) + f" og {mentions[-1]}"

        lines.append(f"\nGratulerer til ukas vinner(e) {mention_str}!")

        return split_message_blocks(lines)

    
    def _format_total_leaderboard(self) -> list[str]:
        scores = self._db.get_scores_by_league(self._league_id)
        leaderboard = []
        for score in scores:
            user = self._db.get_user(score.user_id)
            if user:
                emoji = f"{user.user_emoji}" if user.user_emoji else ""
                leaderboard.append((score.points, score.weekly_wins, emoji, user.user_display_name, user.user_id))

        # Sort by points DESC, then weekly_wins DESC
        leaderboard.sort(key=lambda x: (-x[0], -x[1]))

        league_name = self._league_config["name"]
        lines = [f"**Totale poeng ({league_name}):**"]

        rank = 1
        prev_points = None
        prev_wins = None
        for i, (points, weekly_wins, emoji, name, user_id) in enumerate(leaderboard):
            if (points, weekly_wins) != (prev_points, prev_wins):
                rank = i + 1
                prev_points, prev_wins = points, weekly_wins

            movement = ""
            if self._previous_ranks and user_id in self._previous_ranks:
                diff = self._previous_ranks[user_id] - rank
                if diff > 0:
                    movement = f" (+{diff})"
                elif diff < 0:
                    movement = f" ({diff})"
                else:
                    movement = " (0)"

            if weekly_wins > 0:
                lines.append(f"{rank} - {emoji} {name}: {points}p (us: {weekly_wins}) {movement}")
            else:
                lines.append(f"{rank} - {emoji} {name}: {points}p {movement}")

        return split_message_blocks(lines)
    

    async def send_leaderboard(self):
        """Sends the leaderboard to the specified channel."""
        total_chunks = self._format_total_leaderboard()
        for chunk in total_chunks:
            await self._channel.send(chunk)

    async def send_results(self):
        """Sends the match results to the specified channel."""
        self._fetch_match_results()
        self._increment_score()
        weekly_chunks = await self._format_weekly_leaderboard()
        total_chunks = self._format_total_leaderboard()

        for chunk in weekly_chunks:
            await self._channel.send(chunk)

        for chunk in total_chunks:
            await self._channel.send(chunk)
