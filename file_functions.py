import json
import logic


def remove_reaction_data(reaction_type, username, message_content):
    try:
        # Load existing data
        with open(logic.predictions_file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print("File not found. No data to remove.")
        return

    # Check if the message content is in the data
    if message_content in data:
        # Filter out the reaction data to be removed
        data[message_content] = [reaction for reaction in data[message_content]
                                 if not (reaction['username'] == username and reaction['reaction'] == reaction_type)]

        # If the list for this message is now empty, remove the key entirely
        if not data[message_content]:
            del data[message_content]

        # Save the updated data
        with open(logic.predictions_file, 'w') as file:
            json.dump(data, file, indent=4)
    else:
        print("Message content not found in data.")



def save_reaction_data(reaction_type, username, message_content):
    
    # Structure to hold the new reaction data
    new_reaction_data = {
        'username': username,
        'reaction': reaction_type
    }

    try:
        # Load existing data
        with open(logic.predictions_file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        # Initialize data as an empty dictionary if file doesn't exist
        data = {}

    # Check if the message content is already a key in the data
    if message_content in data:
        # Append new reaction data to the existing list for this message
        data[message_content].append(new_reaction_data)
    else:
        # Otherwise, create a new entry for this message
        data[message_content] = [new_reaction_data]

    # Save the updated data
    with open(logic.predictions_file, 'w') as file:
        json.dump(data, file, indent=4)




import json
import sqlite3

def save_predictions_to_db(json_file_path, db_path, target_message):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            message TEXT,
            username TEXT,
            reaction TEXT
        )
    ''')

    # Read and parse the JSON file
    with open(json_file_path, 'r') as file:
        predictions = json.load(file)

    # Check if the target message exists in the JSON data
    if target_message in predictions:
        # Insert data for the target message into the table
        for reaction in predictions[target_message]:
            cursor.execute('''
                INSERT INTO predictions (message, username, reaction) 
                VALUES (?, ?, ?)
            ''', (target_message, reaction['username'], reaction['reaction']))

    # Commit changes and close the connection
    conn.commit()
    conn.close()

# Example usage
save_predictions_to_db('predictions.json', 'predictions.db', 'Message content 1')

