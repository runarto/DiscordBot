import json

def check_multiple_reactions(file):

    # Denne funksjonen sjekker hvorvidt en bruker har reagert mer enn én gang. 
    # Kan benyttes til å implementere en funksjon for fjerning av reaksjoner i Discord eller JSON
    try:
        with open(file, 'r') as file:
            if file.read(1):  # Read the first character to check if the file is empty
                file.seek(0)  # Reset file read position
                data = json.load(file)
            else:
                print(f"The file {file} is empty.")
                return
    except FileNotFoundError:
        print(f"File not found: {file}")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from the file: {file}")
        print(f"JSON error: {e}")
        return
    
    print("Now here\n")
    list_of_users = []
    for message_content, reactions in data.items():
        user_reactions = {}
        for reaction in reactions:
            username = reaction['username']
            reaction_type = reaction['reaction']
            if username not in user_reactions:
                user_reactions[username] = []
            user_reactions[username].append(reaction_type)

        # Check if any user reacted with multiple types

        for username, user_reaction_types in user_reactions.items():
            if len(user_reaction_types) > 1:
                list_of_users.append((message_content, username))
    return list_of_users




def remove_duplicate_reactions_per_message(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from the file: {file_path}")
        print(f"JSON error: {e}")
        return

    updated_data = {}
    for message_content, reactions in data.items():
        user_reaction_seen = set()
        filtered_reactions = []

        for reaction in reactions:
            username = reaction['username']
            # If we've seen the user already for this message, skip
            if username in user_reaction_seen:
                continue

            # Add to filtered reactions and mark user as seen
            filtered_reactions.append(reaction)
            user_reaction_seen.add(username)

        updated_data[message_content] = filtered_reactions

    # Write the updated data back to the JSON file
    with open(file_path, 'w') as file:
        json.dump(updated_data, file, indent=4)

    print("Duplicate reactions removed per message.")
        
