"""
Dry-run of World Cup results processing.

Reads unprocessed WC matches + their predictions from the DB,
fetches results from FotMob, and prints what points would be awarded —
without writing anything to the database or Discord.

Run from the repo root:
    python scripts/dry_run_wc_results.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from collections import Counter, defaultdict
from dotenv import load_dotenv
from db.db_interface import DB
from api.fotmob import get_fixture_result
from misc.utils import interpret_result
from misc.constants import LEAGUES

load_dotenv()

LEAGUE_KEY = "WORLD_CUP"
LEAGUE_CONFIG = LEAGUES[LEAGUE_KEY]
LEAGUE_ID = LEAGUE_CONFIG["id"]
SLUG = LEAGUE_CONFIG["slug"]

_OUTCOMES = ("H", "D", "A")
_LABEL = {"H": "Hjemmeseier (H)", "D": "Uavgjort (U)", "A": "Borteseier (B)"}


def wc_points_by_outcome(predictions) -> dict[str, int]:
    counts = Counter(p.prediction for p in predictions if p.prediction in _OUTCOMES)
    ranked = sorted({c for c in counts.values() if c > 0}, reverse=True)
    return {outcome: ranked.index(count) + 1 for outcome, count in counts.items()}


def main():
    db = DB("infobase.db")
    # Use ALL WC matches that have predictions stored, regardless of processed flag.
    # The startup migration stamped processed=1 on all past matches before results
    # were ever sent, so we must bypass that filter here.
    all_matches = db.get_matches_by_league(LEAGUE_ID)
    matches = [m for m in all_matches if db.get_all_predictions_for_match(m.message_id)]

    if not matches:
        print("No WC matches with predictions found in the database.")
        return

    print(f"Found {len(matches)} WC match(es) with predictions.\n")

    weekly_points: dict[str, int] = defaultdict(int)
    processed_count = 0
    skipped_count = 0

    for match in matches:
        predictions = db.get_all_predictions_for_match(match.message_id)

        print(f"[{match.match_id}] {match.home_team} vs {match.away_team} ({match.kick_off_time})")

        try:
            fixture = get_fixture_result(match_id=match.match_id, league_id=LEAGUE_ID, slug=SLUG)
        except Exception as e:
            print(f"  ERROR fetching result: {e}\n")
            skipped_count += 1
            continue

        status = fixture.status.get("short", "?")
        score = fixture.result
        print(f"  Status: {status}  Score: {score}")

        if status != "FT":
            print("  Not finished yet, skipping.\n")
            skipped_count += 1
            continue

        result = interpret_result(score)
        print(f"  Outcome: {_LABEL.get(result, result)}")

        counts = Counter(p.prediction for p in predictions if p.prediction in _OUTCOMES)
        points_map = wc_points_by_outcome(predictions)

        print(f"  Votes: H={counts.get('H',0)}  U={counts.get('D',0)}  B={counts.get('A',0)}")
        print(f"  Points if correct: H={points_map.get('H','—')}  U={points_map.get('D','—')}  B={points_map.get('A','—')}")

        winners = []
        for p in predictions:
            if p.prediction == result:
                pts = points_map.get(result, 1)
                user = db.get_user(p.user_id)
                name = user.user_display_name if user else p.user_id
                weekly_points[name] += pts
                winners.append(f"{name} (+{pts}p)")

        if winners:
            print(f"  Earns points: {', '.join(winners)}")
        else:
            print("  No correct predictions.")

        processed_count += 1
        print()

    print("=" * 50)
    print(f"Matches processed: {processed_count}  |  Skipped: {skipped_count}")

    if weekly_points:
        print("\nWeekly totals (what would be awarded):")
        for name, pts in sorted(weekly_points.items(), key=lambda x: -x[1]):
            print(f"  {name}: {pts}p")

        top = max(weekly_points.values())
        winners = [n for n, p in weekly_points.items() if p == top]
        print(f"\nWould-be winner(s): {', '.join(winners)} ({top}p)")
    else:
        print("\nNo points would be awarded.")


if __name__ == "__main__":
    main()
