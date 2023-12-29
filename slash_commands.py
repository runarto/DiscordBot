from importFile import *
from discord import Option
from predictionbot import *
from file_functions import *
from perms import *




bot = commands.Bot(command_prefix='/', intents=intents)

@bot.command(name='leaderboard', description="Vis ledertavlen")
async def total_leaderboard(ctx):
    # Sort user scores by points (descending order)
    scores = file_functions.user_scores
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Format the leaderboard message
    leaderboard_message = "Tippekupongen 2024:\n"
    for rank, (user, score) in enumerate(sorted_scores, start=1):
        leaderboard_message += f"{rank}. {user}: {score} points\n"

    # Send the leaderboard message to the Discord channel
    await ctx.send(leaderboard_message)





@bot.slash_command(guild_ids=[guild_id], description="Send ukens kupong")
async def send_ukens_kupong(ctx, days: Option(int, "Enter the number of days")):
    # Check if the command is being used in the allowed channel
    if ctx.channel_id != channel_id:
        await ctx.respond("This command can only be used in a specific channel.")
        return
    
    

    with open(logic.predictions_file, 'w') as file: #Tømmer input_predictions-fila
        json.dump({}, file)
        print("Dumped old predictions 1/2\n")
    try:
        channel = client.get_channel(channel_id)
        if channel:

            with open(logic.output_predictions_file, 'w') as file: #Tømmer output_predictions
                json.dump({}, file)
            
            print("Dumped old predictions 2/2\n")

            fixtures = logic.get_matches(days) #Henter inn kamper de neste x dagene

            data = []
            for fixture in fixtures: #Itererer omver kampenee
                print(fixture)
                # Format the message with fixture details
                message_content = f"{fixture['home_team']} vs {fixture['away_team']}" #Genererer melding

                # Send the message to the channel
                message = await channel.send(message_content) #Sender melding om kamp
                data.append((message.id ,fixture['match_id']))

                await message.add_reaction('🏠') #Legger til reaksjoner. 
                await message.add_reaction('🏳️') #Benytter disse tre fast for å gjøre det lettere
                await message.add_reaction('✈️')
            
            file_functions.write_file(logic.tracked_messages, data) #Lagrer meldinger i en JSON. 
            date_start, hour_start, minute_start, messages_id = get_day_hour_minute(days)
            update_jobs(date_start, hour_start, minute_start, messages_id)
        
        else:
            print(f"Could not find channel with ID {channel_id}")
    except discord.errors.Forbidden:
        print(f"Missing permissions to send message in channel {channel_id}")
    except Exception as e:
        print(f"An error occurred: {e}")


@bot.slash_command(guild_ids=[guild_id], description="Vis resultatene fra forrige uke, og totale resultater")
async def send_leaderboard_message(ctx, days: Option(int, "Enter the number of days")):
    try:
        message = format_leaderboard_message(days)
        if message and message.strip():
            await ctx.respond(message)
        else:
            await ctx.respond("Leaderboard message is empty.")
    except discord.errors.Forbidden:
        await ctx.respond("Missing permissions to send message.")
    except Exception as e:
        await ctx.respond(f"An error occurred: {e}")
