from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import misc.utils as utils
from db.db_interface import DB
import pytz

import discord
from discord.ext import commands
import logging

_OSLO = pytz.timezone("Europe/Oslo")

class Schedule:
    def __init__(self, db: DB, channel: discord.TextChannel, logger: logging.Logger, bot: commands.Bot):
        self._db = db
        self._channel = channel
        self._logger = logger
        self._bot = bot
        self._scheduler = AsyncIOScheduler(timezone=_OSLO)
        self._now = datetime.now(tz=_OSLO)

    def running(self):
        return self._scheduler.running

    def start(self):
        self._scheduler.start()
        self._schedule_all_matches()
        self._scheduler.add_job(
            self._auto_kupong_job,
            trigger=IntervalTrigger(minutes=30),
            id="auto_kupong_wc",
            name="Auto-post new World Cup matches",
            replace_existing=True,
            next_run_time=datetime.now(tz=_OSLO),
        )

    def reschedule(self):
        self._now = datetime.now(tz=_OSLO)
        self._schedule_all_matches()

    def shutdown(self, wait: bool = False):
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
                    name=f"Store predictions for match {match.match_id}",
                    replace_existing=True,
                    misfire_grace_time=300
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

    async def _auto_kupong_job(self):
        try:
            from kupong.kupong import Kupong
            kupong = Kupong(
                days=2,
                db=self._db,
                channel=self._channel,
                logger=self._logger,
                league_key="WORLD_CUP",
                predictor=None,
            )
            count = await kupong.post_new_fixtures()
            if count > 0:
                self._logger.info(f"Auto-posted {count} new World Cup fixture(s).")
                self._schedule_all_matches()
            else:
                self._logger.debug("Auto-kupong: no new World Cup fixtures to post.")
        except Exception as e:
            self._logger.error(f"Auto-kupong job failed: {e}", exc_info=True)

