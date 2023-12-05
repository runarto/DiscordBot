
import logic

import file_functions

from collections import defaultdict


def update_user_scores():
    try:
        predictions = file_functions.read_file("output_predictions.json")

        predictions = dict(sorted(predictions.items()))
        


        if not predictions:
            return {}, {}, 0
        actual_results = logic.get_match_results()
        num_of_games = len(actual_results)
        
        user_scores = file_functions.read_file(logic.user_scores) #Laster inn json fil med user_scores
       

        this_week_user_score = defaultdict(int)  # Using defaultdict for automatic handling of new keys

        for game_id, user_predictions in predictions.items():
            for prediction in user_predictions:
                username = prediction['username']

        # Initialize score for each user if not already present
                if username not in user_scores:
                    user_scores[username] = 0

        # Rest of your scoring logic
                actual_result = actual_results.get(game_id)
                actual_result = "🏠" if actual_result is True else ("✈️" if actual_result is False else "🏳️")
                predicted_result = prediction['reaction']

                if predicted_result == actual_result:
                    user_scores[username] += 1
                    this_week_user_score[username] += 1
        # If you want to track weekly participation even without correct answers:
                elif username not in this_week_user_score:
                    this_week_user_score[username] = 0


        actual_result = "🏠" if actual_result is True else ("✈️" if actual_result is False else "🏳️")
        
        return user_scores, dict(this_week_user_score), num_of_games

    except (FileNotFoundError, KeyError, TypeError) as e:
        print(f"An error occurred: {e}")
        # Return empty data or handle the error as needed
        return {}, {}, 0



#Sorterer 

def sort_user_scores(user_scores):
    if user_scores is None:
        return
    # Convert dictionary into a list of tuples and sort by score in descending order
    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores




def format_leaderboard_message():
    user_scores, this_week_user_scores, num_of_games = update_user_scores()
    
    if not user_scores and not this_week_user_scores:
        return "No scores available this week."

    message_parts = []

    if this_week_user_scores:
        sorted_this_week_user_scores = sort_user_scores(this_week_user_scores)

        message_parts.append(f"Av {num_of_games} mulige:")
        for username, score in sorted_this_week_user_scores:
            message_parts.append(f"{score} poeng: {username}")

        if sorted_this_week_user_scores:
            weekly_winner = sorted_this_week_user_scores[0][0]  # username of this week's top scorer
            message_parts.append(f"Gratulerer til ukas vinner @{weekly_winner}!\n")

    if user_scores:
        sorted_user_score = sort_user_scores(user_scores)
        message_parts.append("Total poeng:")
        for rank, (username, score) in enumerate(sorted_user_score, start=1):
            message_parts.append(f"{rank}. {username}: {score}p")

        file_functions.write_file(logic.user_scores, user_scores)

    return '\n'.join(message_parts)




format_leaderboard_message()