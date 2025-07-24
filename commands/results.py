import discord
import os

from collections import defaultdict
from api.rapid_sports import get_fixture_result
from misc.utils import split_message_blocks


class Results:
    def __init__(self, db, channel: discord.TextChannel):
        self._auth = os.getenv('API_TOKEN')
        self._db = db
        self._channel = channel
        self.old_scores = self._db.get_all_scores()
        self.match_results = {}
        self.num_fixtures = None
        self._fetch_match_results()

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
    
    def _format_total_leaderboard(self, db) -> list[str]:
        scores = db.get_all_scores()  # list of Score(user_id, points, weekly_wins)

        leaderboard = []
        for score in scores:
            user = db.get_user(score.user_id)
            if user:
                emoji = f"{user.user_emoji}" if user.user_emoji else ""
                name = user.user_display_name
                leaderboard.append((score.points, score.weekly_wins, emoji, name))

        # Sort by points DESC, then weekly_wins DESC
        leaderboard.sort(key=lambda x: (-x[0], -x[1]))

        lines = ["**Totale poeng:**"]

        rank = 1
        prev_points = None
        prev_wins = None
        for i, (points, weekly_wins, emoji, name) in enumerate(leaderboard):
            # If points and weekly_wins match previous, keep same rank
            if (points, weekly_wins) != (prev_points, prev_wins):
                rank = i + 1  # update visible rank
                prev_points, prev_wins = points, weekly_wins

            lines.append(f"{rank} - {emoji} {name}: {points}p (us: {weekly_wins})")

        return split_message_blocks(lines)


    async def send(self):
        weekly_chunks = self._format_weekly_leaderboard(self.weekly_scores, self._db)
        total_chunks = self._format_total_leaderboard(self._db)

        for chunk in weekly_chunks:
            await self.channel.send(chunk)

        for chunk in total_chunks:
            await self.channel.send(chunk)







        if not self.match_results:
            await self._interaction.response.send_message("No match results available.")
            return

        result_messages = []
        for match_id, result in self.match_results.items():
            match = self._db.get_match_by_id(match_id)
            if match:
                result_messages.append(f"{match.home_team} vs {match.away_team}: {result}")

        result_text = "\n".join(result_messages)
        await self._interaction.response.send_message(f"Match Results:\n{result_text}")

        # Increment scores after sending results
        self._increment_score()





