from difflib import SequenceMatcher
from datetime import datetime
import api.discord as discord_api
import api.rapid_sports as sports_api
import discord
from discord.ext import commands
import logging


def check_similarity(input1, input2):
    return SequenceMatcher(None, input1, input2).ratio()

def split_message_blocks(lines: list[str], max_length: int = 2000) -> list[str]:
    blocks = []
    current_block = ""

    for line in lines:
        if len(current_block) + len(line) + 1 > max_length:
            blocks.append(current_block.rstrip())
            current_block = ""
        current_block += line + "\n"

    if current_block:
        blocks.append(current_block.rstrip())

    return blocks

def map_teams_to_emojis(bot, db, auth):
    teams = sports_api.get_teams(auth)['response']
    emojis = discord_api.get_emojis(bot)

    for team in teams:
        team_name_api = team['team']['name']
        team_name_norsk = str(input("Enter the Norwegian name for the team '{}': ".format(team_name_api)))
        team_emoji = None
        highest_ratio = 0

        for emoji in emojis:
            similarity = check_similarity(emoji.name.lower(), team_name_norsk.lower())
            if similarity > highest_ratio:
                highest_ratio = similarity
                team_emoji = f"<:{emoji.name}:{emoji.id}>"

        if team_emoji is None:
            team_emoji = input(f"No emoji found for '{team_name_norsk}'. Please enter an emoji: ")
        
        print(repr(team_name_api), repr(team_name_norsk), repr(team_emoji))
        print(f"Type of team_name_api: {type(team_name_api)}")
        print(f"Type of team_name_norsk: {type(team_name_norsk)}")
        print(f"Type of team_emoji: {type(team_emoji)}")
        print("Inserting:", team_name_api, team_name_norsk, team_emoji)
        db.insert_team(team_name_api, team_name_norsk, team_emoji)

def map_roles_to_emojis(bot, db):
    """Maps roles to emojis based on similarity of names, and writes it to DB."""
    roles = discord_api.get_roles(bot)
    emojis = discord_api.get_emojis(bot)

    threshold = 0.7

    for role in roles:
        best_match = None
        highest_ratio = 0
        

        for emoji in emojis:
            similarity = check_similarity(emoji.name.lower(), role.name.lower())

            if similarity > highest_ratio and similarity >= threshold:
                highest_ratio = similarity
                best_match = emoji

        if best_match:
            db.insert_team_emoji(role.name, f"<:{best_match.name}:{best_match.id}>")


def fetch_user_data(bot, db):
    """
        Fetches username, user-id and top emoji from the guilds and inserts it into the database.
    """
    non_permitted_roles = []
    for guild in bot.guilds: 
        for role in guild.roles:
            if role.position > 120 or role.name == "@everyone":
                non_permitted_roles.append(role.id)

        for user in guild.members:
            if user.bot:
                continue
            for role in reversed(user.roles):
                if role.id in non_permitted_roles:
                    continue
                else:
                    db.insert_user(user.id, user.name, user.display_name, role.name)
                    break


async def store_predictions(message: discord.Message, logger: logging.Logger, db):
    """
    Stores predictions from a message in the database.
    Reactions are assumed to represent:
        - First reaction: "H" (Home win)
        - Second reaction: "D" (Draw)
        - Third reaction: "A" (Away win)
    """
    match_id = message.id
    prediction_labels = ["H", "D", "A"]

    reactions = message.reactions[:3]  # Make sure only first 3 are processed

    for i, reaction in enumerate(reactions):
        if i >= len(prediction_labels):
            break

        prediction_value = prediction_labels[i]
        async for user in reaction.users():
            if user.bot:
                continue
            try:
                logger.debug(f"Inserting prediction for user {user.id}: {str(reaction.emoji)}")
                db.insert_prediction(match_id, str(user.id), prediction_value)
            except Exception as e:
                logger.error(f"Failed to insert prediction for user {user.id}: {e}")
