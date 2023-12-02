import discord
import logic
import asyncio
import json

TOKEN = 'secret'

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def run_bot():

    @client.event
    async def on_ready():
        print(f'We have logged in as {client.user}')
    
        channel_id = SOME_ID  # Replace with your Discord channel ID
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
    client.run(TOKEN)


async def check_reactions():
    for message_id, match_id in logic.tracked_messages.items():
        # Fetch the message object from its ID
        channel = client.get_channel(1180502757162102804)
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            print(f"Message with ID {message_id} not found.")
            continue

        # Iterate over each reaction in the message
        for reaction in message.reactions:
            users = await reaction.users().flatten()
            for user in users:
                if not user.bot:  # Exclude bots
                    update_json_file(match_id, user.name, user.id, reaction.emoji)






def update_json_file(match_id, user_name, user_id, reaction):
    file_path = 'reactions_data.json'
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []

    # Append new reaction data
    data.append({
        'match_id': match_id,
        'user_name': user_name,
        'user_id': user_id,
        'reaction': str(reaction)
    })

    # Write the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


        


