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
        
"""
def run_bot():
    scheduler.start()
    client.run(perms.TOKEN)
"""

async def on_reaction_add(reaction, user):
    # Ignore the bot's own reactions
    
    if user == client.user:
            return
    
    message_content = reaction.message.content
    datetime_str = message_content.split('\n')[0].strip()
    
    # Parse the datetime string into a datetime object
    match_start = parser.isoparse(datetime_str)

    # Check if current time is before the match start time
    if datetime.datetime.now(datetime.timezone.utc) < match_start:

        if reaction.message.author == client.user:
            # Check if the user already reacted with a different emoji
            if (await user_already_reacted(reaction, user)):
                return
            else:
                file_functions.save_reaction_data(str(reaction.emoji), user.name, reaction.message.content)
                print(f"Reaction added by {user.name}: {reaction.emoji} from message {reaction.message.content}")
    else:
        print(f"User {user.name} tried to react with {reaction.emoji} on the message {reaction.message.content}, but the game was already started\n.")
        await reaction.remove(user)
