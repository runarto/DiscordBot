"""
async def check_reactions(ctx):
    for message.id in logic.tracked_messages:
        # Fetch the message object from its ID
        channel = client.get_channel(1180502757162102804)  # Replace with your channel ID
        try:
            message = await channel.fetch_message(message.id)
        except discord.NotFound:
            print(f"Message with ID {message.id} not found.")
            continue

        # Iterate over each reaction in the message
        for reaction in message.reactions:
            users = await reaction.users().flatten()
            user_names = [user.name for user in users if not user.bot]  # Exclude bots

    
    




def save_prediction(ctx, ser_id, match_id, prediction):
    try:
        # Load existing predictions
        with open(predictions_file, 'r') as file:
            predictions = json.load(file)
    except FileNotFoundError:
        predictions = {}

    # Update the prediction
    predictions[str(user_id)] = {'match_id': match_id, 'prediction': prediction}

    # Save predictions back to the file
    with open(predictions_file, 'w') as file:
        json.dump(predictions, file)

client.run('YOUR_BOT_TOKEN')

# Function to check match results and update scores
async def check_match_results(ctx):
    # Code to check match results and update user scores

# Function to announce scores
async def announce_scores(ctx):
    # Code to announce the scores in the Discord channel

client.run('your token')  # Replace 'your token' with your actual Discord bot token
"""