import json

# Load data from the provided JSON files
with open('jsonfiles/user_scores_Eliteserien.json', 'r') as f:
    user_scores = json.load(f)

with open('jsonfiles/weekly_winners.json', 'r') as f:
    weekly_winners = json.load(f)

# Function to sort user scores
def sort_user_scores(user_scores, weekly_winners):
    return sorted(
        user_scores.items(),
        key=lambda item: (item[1], weekly_winners.get(item[0].strip('<@!>'), 0)),
        reverse=True
    )

# Sort the user scores
sorted_user_score = sort_user_scores(user_scores, weekly_winners)

# Generate message parts with rank calculation
message_parts = ["Totale poeng:"]
previous_score = None
previous_weekly_wins = None
current_rank = 0

for index, (user_id, score) in enumerate(sorted_user_score, start=1):
    weekly_win_count = weekly_winners.get(user_id.strip('<@!>'), 0)

    # Determine rank
    if score != previous_score or weekly_win_count != previous_weekly_wins:
        current_rank = index

    # Append to message parts
    if user_id.strip('<@!>') in weekly_winners:
        message_parts.append(f"{current_rank}. {user_id}: {score}p (us: {weekly_win_count})")
    else:
        message_parts.append(f"{current_rank}. {user_id}: {score}p")

    # Update previous score and weekly wins
        previous_score = score
        previous_weekly_wins = weekly_win_count

# Output the generated message
for part in message_parts:
    print(part)
