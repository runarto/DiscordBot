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

def save_predictions_to_json(input_json_file_path, output_json_file_path, target_message):
    # Read and parse the input JSON file
    with open(input_json_file_path, 'r') as file:
        predictions = json.load(file)
        print(predictions)
        print("Read input file successfully")

    if target_message in predictions:
        print(f"Found target message: {target_message}")
        # Extract data for the target message
        data_to_save = {target_message: predictions[target_message]}

        # Initialize variable to hold the existing data
        existing_data = {}

        # Try to read the existing data from the output file
        try:
            with open(output_json_file_path, 'r') as outfile:
                existing_data = json.load(outfile)
            print("Read existing data from output file")
        except (FileNotFoundError, json.JSONDecodeError):
            print("Output file not found or is empty/invalid, starting fresh")
            pass

        # Append the new data to existing data
        existing_data.update(data_to_save)

        # Write the updated/initial data to the output JSON file
        with open(output_json_file_path, 'w') as outfile:
            json.dump(existing_data, outfile, indent=4)
            print("Written data to output file")

        # Remove the target message from the input data
        del predictions[target_message]
        print("Removed target message from input data")

        # Write the updated data back to the input JSON file
        with open(input_json_file_path, 'w') as file:
            json.dump(predictions, file, indent=4)
            print("Updated input file")
    else:
        print(f"Target message '{target_message}' not found in input file")



def read_predictions(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)




