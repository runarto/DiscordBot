import discord
import logic
import asyncio
import json

TOKEN = 'api'
channel_id = 123

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

    channel = client.get_channel(channel_id)
    
    if channel is None:
        print(f"Couldn't find the channel {channel_id}")
        return

    fixtures = logic.get_matches()  # Fetch the upcoming fixtures
    if fixtures:
        for fixture in fixtures:
            string_check = fixture['home_team'] + " " + fixture['away_team']
            if string_check in logic.tracked_messages.values():
                print("Games already printed.\n")
            else: 
            # Format the message with fixture details
                message_content = f"📅 {fixture['date']}\n⚽ {fixture['home_team']} vs {fixture['away_team']}"
            # Send the message to the channel
                message = await channel.send(message_content)
                logic.tracked_messages[message.id] = fixture['home_team'] + " " + fixture['away_team']

                home_team = fixture['home_team']
                away_team = fixture['away_team']
        
                #await message.add_reaction(logic.emoji_dictionary[home_team])
                await message.add_reaction('🏠')
                await message.add_reaction('🏳️')
                await message.add_reaction('✈️')
               # await message.add_reaction(logic.emoji_dictionary[away_team])
    
    else:
        print("No upcoming fixtures found or there was an error fetching them.")

    print("I am here\n")
      # Replace 'YOUR_BOT_TOKEN' with your actual Discord bot token


@client.event
async def on_reaction_add(reaction, user):
    if  reaction.message.author == client.user:
        save_reaction_data(str(reaction.emoji), user.name, reaction.message.content)




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



async def remove_extra_reactions(client, channel_id, file):
    multiple_reactors = check_multiple_reactions(file)
    if multiple_reactors is None:
        return

    channel = client.get_channel(channel_id)

    for message_content, username in multiple_reactors:
        try:
            message = await channel.fetch_message(message_content.id)
        except discord.NotFound:
            print(f"Message with ID {message_content} not found.")
            continue

        for reaction in message.reactions:
            users = await reaction.users().flatten()
            for user in users:
                if user.name == username:
                    await reaction.remove(user)

                

client.run(TOKEN)

