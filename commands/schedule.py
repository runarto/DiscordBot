from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from misc.utils import store_predictions
import pytz

import discord
import logging

class Schedule:
    def __init__(self, db, channel: discord.TextChannel, logger: logging.Logger):
        self._db = db
        self._channel = channel
        self._logger = logger
        self._scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Oslo"))

    def start(self):
        self._scheduler.start()
        self._schedule_all_matches()

    def _schedule_all_matches(self):
        matches = self._db.get_all_matches()
        for match in matches:
            try:
                dt = datetime.fromisoformat(match.kick_off_time)
                job_time = dt + timedelta(minutes=1)  # adjust if you want to wait longer

                if job_time < datetime.now(tz=pytz.timezone("Europe/Oslo")):
                    continue  # skip past matches

                self._scheduler.add_job(
                    self._store_predictions_job,
                    trigger=DateTrigger(run_date=job_time),
                    args=[match.message_id],
                    id=str(match.match_id),
                    name=f"Store predictions for match {match.match_id}"
                )
                self._logger.info(f"Scheduled predictions for match {match.match_id} at {job_time}")
            except Exception as e:
                self._logger.error(f"Failed to schedule match {match.match_id}: {e}")

    async def _store_predictions_job(self, message_id: int):
        try:
            message = await self._channel.fetch_message(message_id)
            await store_predictions(message, self._logger, self._db)
            self._logger.info(f"Stored predictions for message {message_id}")
        except Exception as e:
            self._logger.error(f"Failed to store predictions for message {message_id}: {e}")
