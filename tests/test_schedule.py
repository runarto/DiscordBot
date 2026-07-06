import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from misc.schedule import Schedule


def test_store_predictions_job_fetches_from_stored_channel_id(db):
    default_channel = MagicMock()
    default_channel.id = 1
    default_channel.fetch_message = AsyncMock()

    thread_channel = MagicMock()
    thread_channel.id = 2
    thread_channel.fetch_message = AsyncMock(return_value=SimpleNamespace(id=101))

    bot = MagicMock()
    bot.fetch_channel = AsyncMock(return_value=thread_channel)

    schedule = Schedule(db=db, channel=default_channel, logger=MagicMock(), bot=bot)

    with patch("misc.schedule.utils.store_predictions", new=AsyncMock()) as store_predictions:
        asyncio.run(schedule._store_predictions_job(message_id=101, channel_id=2))

    bot.fetch_channel.assert_awaited_once_with(2)
    thread_channel.fetch_message.assert_awaited_once_with(101)
    default_channel.fetch_message.assert_not_awaited()
    store_predictions.assert_awaited_once()


def test_store_predictions_job_uses_default_channel_for_legacy_rows(db):
    default_channel = MagicMock()
    default_channel.id = 1
    default_channel.fetch_message = AsyncMock(return_value=SimpleNamespace(id=101))

    bot = MagicMock()
    bot.fetch_channel = AsyncMock()

    schedule = Schedule(db=db, channel=default_channel, logger=MagicMock(), bot=bot)

    with patch("misc.schedule.utils.store_predictions", new=AsyncMock()) as store_predictions:
        asyncio.run(schedule._store_predictions_job(message_id=101))

    bot.fetch_channel.assert_not_awaited()
    default_channel.fetch_message.assert_awaited_once_with(101)
    store_predictions.assert_awaited_once()
