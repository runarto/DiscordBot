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




