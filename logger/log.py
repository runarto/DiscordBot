import logging


class DiscordLogHandler(logging.Handler):
    def __init__(self, bot, channel_id):
        super().__init__(level=logging.INFO)
        self.bot = bot
        self.channel_id = channel_id

    async def send_to_discord(self, message):
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            await channel.send(message)

    def emit(self, record):
        log_entry = self.format(record)
        if self.bot.is_ready():
            coro = self.send_to_discord(f"`[LOG]` {log_entry}")
            self.bot.loop.create_task(coro)
