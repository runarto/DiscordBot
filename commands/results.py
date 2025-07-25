import discord
import os
import logging

from collections import defaultdict
from api.rapid_sports import get_fixture_result
from misc.utils import split_message_blocks


class Results:
    def __init__(self, db, channel: discord.TextChannel, logger: logging.Logger):
        self._auth = os.getenv('API_TOKEN')
        self._db = db
        self._channel = channel
        self.old_scores = self._db.get_all_scores()
        self._previous_ranks = self._get_ranks()
        self.match_results = {}
        self.num_fixtures = None

    def _get_ranks(self) -> dict[int, int]:
        scores = self._db.get_all_scores()
        users = []
        for score in scores:
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
        matches = self._db.get_all_matches()
        self.num_fixtures = len(matches)
        for match in matches:
            result = self._determine_fixture_result(match.match_id)
            if result != "NA":
                self.match_results[match.match_id] = result

    def _determine_fixture_result(self, fixture_id):
        score = get_fixture_result(self._auth, fixture_id)['response']['score']['fulltime']
        home, away = score['home'], score['away']

        match (home, away):
            case (h, a) if h > a:
                return "H"
            case (h, a) if h < a:
                return "A"
            case (h, a) if h == a:
                return "D"
            case _:
                return "NA"
            
    def _increment_score(self):
        """Increments the score for users based on match results."""


        fixtures = self._db.get_all_matches()
        self.num_fixtures = len(fixtures)
        for fixture in fixtures:
            predictions = self.db.get_all_predictions_for_match(fixture.match_id)
            result = self.match_results.get(fixture.match_id, "NA")
            if result == "NA":
                continue

            for prediction in predictions:
                if prediction.prediction == result:
                    self._db.upsert_score(prediction.user_id, points_delta=1)

            weekly_scores = self._get_weekly_scores()

        if not weekly_scores:
            return

        # Determine max score and corresponding users
        max_score = max(weekly_scores.keys())
        top_users = weekly_scores[max_score]

        # Award weekly wins
        for user_id in top_users:
            self._db.upsert_score(user_id, win_delta=1)


    def _get_weekly_scores(self):
        old_scores = self.old_scores
        new_scores = self._db.get_all_scores()

        # Map old scores by user_id
        old_dict = {s.user_id: s.points for s in old_scores}

        weekly_points_to_users = defaultdict(list)

        for new in new_scores:
            old_points = old_dict.get(new.user_id, 0)  # defaults to 0 for new users
            weekly_points = new.points - old_points

            if weekly_points > 0:
                weekly_points_to_users[weekly_points].append(new.user_id)

        return dict(weekly_points_to_users)
    
    def _format_weekly_leaderboard(self) -> str:
        weekly_scores = self._get_weekly_scores()
        if not weekly_scores:
            return "Ingen poeng ble delt ut denne uka."

        lines = []
        resolved_names: dict[str, str] = {}

        # Sort scores descending
        lines.append(f"**Av {self.num_fixtures} mulige:**")
        for score in sorted(weekly_scores.keys(), reverse=True):
            user_ids = weekly_scores[score]
            names = []

            for uid in user_ids:
                user = self._db.get_user(uid)
                name = user.user_name

                resolved_names[uid] = name
                names.append(name)

            lines.append(f"{score} poeng: {', '.join(names)}")

        # Mention winners with @user_display_name
        top_score = max(weekly_scores.keys())
        top_user_ids = weekly_scores[top_score]
        mentions = ', '.join(f"@{resolved_names[uid]}" for uid in top_user_ids)

        lines.append(f"\nGratulerer til ukas vinnere {mentions}!")

        return split_message_blocks(lines)

    
    def _format_total_leaderboard(self) -> list[str]:
        scores = self._db.get_all_scores()  # list of Score(user_id, points, weekly_wins)
        leaderboard = []
        for score in scores:
            user = self._db.get_user(score.user_id)
            if user:
                emoji = f"{user.user_emoji}" if user.user_emoji else ""
                leaderboard.append((score.points, score.weekly_wins, emoji, user.user_display_name, user.user_id))

        # Sort by points DESC, then weekly_wins DESC
        leaderboard.sort(key=lambda x: (-x[0], -x[1]))

        lines = ["**Totale poeng:**"]

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
                    movement = f" (-{diff})"
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
        weekly_chunks = self._format_weekly_leaderboard()
        total_chunks = self._format_total_leaderboard()

        for chunk in weekly_chunks:
            await self.channel.send(chunk)

        for chunk in total_chunks:
            await self.channel.send(chunk)

    









