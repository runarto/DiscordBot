import json
import logic
import os


def remove_reaction_data(reaction_type, user_id, message_content):
    try:
        # Load existing data
        data = read_file(logic.predictions_file)

    except FileNotFoundError:
        print("File not found. No data to remove.")
        return

    # Check if the message content is in the data
    if message_content in data:
        # Filter out the reaction data to be removed
        data[message_content] = [reaction for reaction in data[message_content]
                                 if not (reaction['username'] == user_id and reaction['reaction'] == reaction_type)]

        # If the list for this message is now empty, remove the key entirely
        if not data[message_content]:
            del data[message_content]

        # Save the updated data
        write_file(logic.predictions_file, data)
    
    else:
        print("Message content not found in data.")



def save_reaction_data(reaction_type, user_id, user_nick, message_content):
    
    # Structure to hold the new reaction data
    new_reaction_data = {
        'user_id': user_id,
        'user_nick': user_nick,
        'reaction': reaction_type
    }

    try:
        # Load existing data
        data = read_file(logic.predictions_file)
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
    write_file(logic.predictions_file, data)








def save_predictions_to_json(input_json_file_path, output_json_file_path, target_message):
    # Read and parse the input JSON file
    predictions = read_file(input_json_file_path)

    if target_message in predictions: #Itererer over meldinger som ligger i predictions
        print(f"Found target message: {target_message}")
        # Extract data for the target message
        data_to_save = {target_message: predictions[target_message]} 

        # Initialize variable to hold the existing data
        existing_data = {}

        # Try to read the existing data from the output file
        try:
            existing_data = read_file(output_json_file_path)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Output file not found or is empty/invalid, starting fresh")
            pass

        # Append the new data to existing data
        existing_data.update(data_to_save)

        # Write the updated/initial data to the output JSON file
        write_file(output_json_file_path, existing_data)

        # Remove the target message from the input data
        del predictions[target_message]
        print("Removed target message from input data")

        # Write the updated data back to the input JSON file
        write_file(input_json_file_path, predictions)
        
    else:
        print(f"Target message '{target_message}' not found in input file")




def read_file(file_path):
    # Check if file does not exist, and create it if necessary
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            json.dump({}, file)  # Create an empty JSON file

    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}  # Return an empty dictionary if the file is empty or invalid JSON
    except FileNotFoundError:
        # This exception should not occur now since we created the file earlier,
        # but it's still good practice to handle it just in case.
        return {}


def write_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
