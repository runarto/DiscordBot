# =============================================================================
# cogs/kupong.py - Kupong and results commands
import discord
from discord.ext import commands
from discord import app_commands
from kupong.kupong import Kupong
from kupong.results import Results
import misc.utils as utils
from db.db_interface import DB

class KupongCog(commands.Cog, name="Kupong"):
    """Commands for managing kuponger and results"""
    
    def __init__(self, bot: commands.Bot, db: DB):
        self.bot = bot
        self.db = db


    @app_commands.command(name='send_kupong', description='Send ukens kupong for de neste dagene.')
    @app_commands.default_permissions(manage_messages=True)
    async def send_ukens_kupong(self, interaction: discord.Interaction, days: int, channel: discord.TextChannel):

        await interaction.response.defer(ephemeral=True)
        kup = Kupong(days=days, db=self.db, channel=channel, logger=self.bot.logger)
        await kup.send_kupong()
        if self.bot.scheduler.running:
            self.bot.scheduler.shutdown(wait=False)
        self.bot.scheduler.start()
        self.bot.logger.info(f"Ukens kupong for the next {days} days sent to {channel.mention}.")
        await interaction.followup.send(f"Ukens kupong for de neste {days} dagene er sendt til {channel.mention}.", ephemeral=True)


    @app_commands.command(name='send_resultater', description='Send ukens resultater for de siste kampene.')
    @app_commands.default_permissions(manage_messages=True)
    async def send_ukens_resultater(self, interaction: discord.Interaction, channel: discord.TextChannel):

        await interaction.response.defer(ephemeral=True)
        await utils.backup_database(self.db_path)
        res = Results(bot=self.bot, db=self.db, channel=channel, logger=self.bot.logger)
        await res.send_results()
        self.bot.logger.info(f"Ukens resultater sent to {channel.mention}.")
        await interaction.followup.send(f"Ukens resultater har blitt sendt til {channel.mention}.", ephemeral=True)


    @app_commands.command(name='send_leaderboard', description='Send the total leaderboard.')
    @app_commands.default_permissions(manage_messages=True)
    async def send_leaderboard(self, interaction: discord.Interaction, channel: discord.TextChannel):

        await interaction.response.defer(ephemeral=True)
        res = Results(bot=self.bot, db=self.db, channel=channel, logger=self.bot.logger)
        await res.send_leaderboard()
        self.bot.logger.info(f"Leaderboard sent to {channel.mention}.")
        await interaction.followup.send(f"Leaderboard has been sent to {channel.mention}.", ephemeral=True)


    @app_commands.command(name='store_predictions', description='Store predictions for a specific match.')
    @app_commands.default_permissions(manage_messages=True)
    async def store_predictions(self, interaction: discord.Interaction, content: str, channel: discord.TextChannel):

        await interaction.response.defer(ephemeral=True)
        target_message = await utils.get_message(self.db, channel, content)
        if not target_message:
            await interaction.followup.send("No match found with the specified content.", ephemeral=True)
            return
        
        await utils.backup_database(self.db_path)
        await utils.store_predictions(target_message, self.bot.logger, self.db)
        self.bot.logger.info(f"Stored predictions for message {target_message.id}.")
        await interaction.followup.send(f"Predictions for message {target_message.id} have been stored.", ephemeral=True)


    @app_commands.command(name='delete_messages', description='Delete the match messages and flush the matches table.')
    @app_commands.default_permissions(manage_messages=True)
    async def delete_match_messages(self, interaction: discord.Interaction, channel: discord.TextChannel):

        await interaction.response.defer(ephemeral=True)
        info = self.db.get_all_matches()
        message_ids = [match.message_id for match in info]

        for msg_id in message_ids:
            message = await channel.fetch_message(msg_id)
            await message.delete()

        self.db.flush_table("matches")
        
        self.bot.logger.info(f"All match messages deleted in {channel.mention}. Table 'matches' flushed.")
        await interaction.followup.send(f"All match messages have been deleted in {channel.mention}.", ephemeral=True)


    @app_commands.command(name='find_cheaters', description='Finds users who reacted after start time for a given game.')
    @app_commands.default_permissions(manage_messages=True)
    async def find_cheaters(self, interaction: discord.Interaction, message_channel: discord.TextChannel, target_channel: discord.TextChannel, content: str):

        await interaction.response.defer(ephemeral=True)
        target_message = await utils.get_message(self.db, message_channel, content)

        if not target_message:
            await interaction.followup.send("No match found with the specified content.", ephemeral=True)
            return
        
        # --- 1. Stored predictions ---
        stored_preds_raw = self.db.get_all_predictions_for_match(target_message.id)
        stored_predictions = {pred.user_id: pred.prediction for pred in stored_preds_raw}

        # --- 2. Current reactions from message ---

        reaction_map = {
            0: "H",
            1: "D",
            2: "A"
        }

        # --- 2. Current reactions from message ---
        current_reactions = {}
        for idx, reaction in enumerate(target_message.reactions[:3]):  
            mapped_prediction = reaction_map.get(idx, None)
            if not mapped_prediction:
                continue  # skip if we somehow go out of bounds

            async for user in reaction.users():
                if not user.bot:
                    current_reactions.setdefault(str(user.id), set()).add(mapped_prediction)

        # --- 3. Compare ---
        cheaters = []

        for user_id, reacted_emojis in current_reactions.items():
            stored = stored_predictions.get(user_id)

            if not stored:
                # User reacted but was not in stored predictions
                cheaters.append((user_id, "🆕 Reagerte sent... juks."))
            elif reacted_emojis != {stored}:
                # User changed or added different emoji(s)
                reacted_str = ", ".join(reacted_emojis)
                cheaters.append((user_id, f"🔁 Endra reaksjon (hadde: {stored}, nå: {reacted_str})... juks."))

        # --- 4. Report ---
        if cheaters:
            report = "\n".join([f"<@{uid}> - {reason}" for uid, reason in cheaters])
            await target_channel.send(f"🚨 **Juksere avslørt:**\n{report}")
            
        await interaction.followup.send("✅ Cheater report sent.", ephemeral=True)




async def setup(bot):
    await bot.add_cog(KupongCog(bot))