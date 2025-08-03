from difflib import SequenceMatcher
from datetime import datetime
import api.discord as discord_api
import api.rapid_sports as sports_api
import discord
import logging
import os
import shutil
from discord.ext import commands
from db.db_interface import DB
from typing import List



def check_similarity(input1: str, input2: str) -> float:
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

def map_teams_to_emojis(bot: commands.Bot, db: DB, auth: str):
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

def map_roles_to_emojis(bot: commands.Bot, db: DB) -> dict[str, str]:
    """Maps roles to emojis based on similarity of names, and writes it to DB."""
    roles = discord_api.get_roles(bot)
    emojis = discord_api.get_emojis(bot)

    threshold = 0.63

    mapping = {}

    for role in roles:
        best_match = None
        highest_ratio = 0
        

        for emoji in emojis:
            similarity = check_similarity(emoji.name.lower(), role.name.lower())

            if similarity > highest_ratio and similarity >= threshold:
                highest_ratio = similarity
                best_match = emoji

        if best_match:
            mapping[role.name] = f"<:{best_match.name}:{best_match.id}>"
            db.insert_team_emoji(role.name, f"<:{best_match.name}:{best_match.id}>")

    return mapping


def map_users(bot: commands.Bot, db: DB):
    """
        Fetches username, user-id and top emoji from the guilds and inserts it into the database.
        If user has no mapped role, inserts None for emoji.
    """
    mapping = db.get_team_emojis()
    role_to_emoji = {item.role_name: item.emoji for item in mapping}

    for guild in bot.guilds: 
        for user in guild.members:
            if user.bot:
                continue
            
            role_emoji = None  # Default to None
            
            # Try to find a mapped role
            for role in reversed(user.roles):
                if role.name in role_to_emoji:
                    role_emoji = role_to_emoji[role.name]
                    break
            # Insert user regardless of whether we found a mapped role
            db.insert_user(user.id, user.name, user.display_name, role_emoji)


async def store_predictions(message: discord.Message, logger: logging.Logger, db: DB):
    """
    Stores predictions from a message in the database.
    Reactions are assumed to represent:
        - First reaction: "H" (Home win)
        - Second reaction: "D" (Draw)
        - Third reaction: "A" (Away win)
    """
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
                db.insert_prediction(message.id, str(user.id), prediction_value)
            except Exception as e:
                logger.error(f"Failed to insert prediction for user {user.id}: {e}")

    logger.info(f"Stored predictions for message {message.id} with content: {message.content}")


async def backup_database(source_path: str, backup_dir: str = "./backups") -> str:
    """
    Creates a timestamped backup of the database file.
    Returns the path to the created backup.
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
    shutil.copyfile(source_path, backup_path)

async def get_message(db: DB, channel: discord.TextChannel, content: str = None, message_id: str = None) -> discord.Message:
    match_info = db.get_all_matches()
    for match in match_info:
        message = await channel.fetch_message(match.message_id)
        if (message.content == content) or (message_id and str(message.id) == message_id):
            return message
        
    return None


async def format_cheater_report_for_matches(db: DB, message_channel: discord.TextChannel, content: str = None) -> List[str]:
    """
    Returns a formatted string report of cheaters for each match.
    Only includes matches where cheaters are found.
    """

    if content is not None:
        # Check only the specified match
        target_message = await get_message(db, message_channel, content)
        if not target_message:
            return []

        cheater_report = await find_cheaters_for_message(target_message, db)
        if not cheater_report:
            return []
        
        return [f"**Kamp {target_message.content}**:\n{cheater_report}"]

    matches = db.get_all_matches()
    report_blocks = []

    for match in matches:
        message = await message_channel.fetch_message(match.message_id)
        cheater_report = await find_cheaters_for_message(message, db)
        if not cheater_report:
            continue
        block = f"**Kamp {message.content}**:\n{cheater_report}"
        report_blocks.append(block)

    return report_blocks    

        
async def find_cheaters_for_message(target_message, db):
    """
    Compares stored predictions with current reactions for a message and returns a list of cheaters.
    Each cheater is represented as a tuple: (user_id, reason).
    """
    # --- 1. Stored predictions ---
    stored_preds_raw = db.get_all_predictions_for_match(target_message.id)
    stored_predictions = {pred.user_id: pred.prediction for pred in stored_preds_raw}

    # --- 2. Current reactions from message ---
    reaction_map = {0: "H", 1: "D", 2: "A"}
    current_reactions = {}
    for idx, reaction in enumerate(target_message.reactions[:3]):
        mapped_prediction = reaction_map.get(idx, None)
        if not mapped_prediction:
            continue
        async for user in reaction.users():
            if not user.bot:
                current_reactions.setdefault(str(user.id), set()).add(mapped_prediction)

    # --- 3. Compare ---
    cheaters = []
    for user_id, reacted_emojis in current_reactions.items():
        stored = stored_predictions.get(user_id)
        if not stored:
            cheaters.append((user_id, "🆕 Reagerte etter kampstart."))
        elif reacted_emojis != {stored}:
            reacted_str = ", ".join(reacted_emojis)
            cheaters.append((user_id, f"🔁 Endra reaksjon (hadde: {stored}, nå: {reacted_str})"))

    # --- 4. Report ---
    if cheaters:
        return "\n".join((f"<@{uid}> - {reason}" for uid, reason in cheaters))
    else :
        return None