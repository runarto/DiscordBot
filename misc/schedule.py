from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import misc.utils as utils
from db.db_interface import DB
import pytz

import discord
import logging

class Schedule:
    def __init__(self, db: DB, channel: discord.TextChannel, logger: logging.Logger):
        self._db = db
        self._channel = channel
        self._logger = logger
        self._scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Oslo"))
        self._now = datetime.now(tz=pytz.timezone("Europe/Oslo"))

    def running(self):
        return self._scheduler.running

    def start(self):
        self._scheduler.start()
        self._schedule_all_matches()

    def shutdown(self, wait: bool = True):
        self._scheduler.shutdown(wait=wait)

    def _schedule_all_matches(self):
        matches = self._db.get_all_matches()
        for match in matches:
            try:

                if self._db.get_all_predictions_for_match(match.message_id):
                    self._logger.debug(f"Match {match.match_id} already has predictions stored, skipping scheduling.")
                    continue

                dt = datetime.fromisoformat(match.kick_off_time)
                job_time = dt + timedelta(minutes=1) 

                # Case 1: Job time is in the past, but no predictions stored
                if job_time < self._now:
                    job_time = self._now + timedelta(minutes=1)  # Schedule for 1 minute in the future
                # Case 2: Job time is in the future, but no predictions stored
                elif job_time > self._now:
                    job_time = job_time
                # Schedule the job      

                self._scheduler.add_job(
                    self._store_predictions_job,
                    trigger=DateTrigger(run_date=job_time),
                    args=[match.message_id],
                    id=str(match.match_id),
                    name=f"Store predictions for match {match.match_id}"
                )
                self._logger.debug(f"Scheduled predictions for match {match.match_id} at {job_time}")
            except Exception as e:
                self._logger.debug(f"Failed to schedule match {match.match_id}: {e}")

    async def _store_predictions_job(self, message_id: int):
        try:
            message = await self._channel.fetch_message(message_id)
            await utils.store_predictions(message, self._logger, self._db)
            self._logger.debug(f"Stored predictions for message {message_id}")
        except Exception as e:
            self._logger.debug(f"Failed to store predictions for message {message_id}: {e}")
