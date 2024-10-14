import logic
import json
import os








def StorePredictions(PredictionsFile, target_message, prediction):

    # Read the predictions file
    predictions = read_file(PredictionsFile)

    # Add the target message to the predictions
    predictions[target_message] = prediction

    # Write the updated predictions to the file
    write_file(PredictionsFile, predictions)

    return predictions[target_message]




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


def write_file(file_path, new_data):
    try:
        # Step 1: Read existing data
        with open(file_path, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, initialize an empty structure
        data = {} if isinstance(new_data, dict) else []

    # Step 2: Merge new data
    if isinstance(data, list) and isinstance(new_data, list):
        data.extend(new_data)  # Append to list
    elif isinstance(data, dict) and isinstance(new_data, dict):
        data.update(new_data)  # Update dictionary
    else:
        raise ValueError("Data in file and new data must be of the same type (both list or both dict)")

    # Step 3: Write updated data back to file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def clear_file(file, data):
    with open(file, 'w') as file:
        json.dump(data, file, indent=4)