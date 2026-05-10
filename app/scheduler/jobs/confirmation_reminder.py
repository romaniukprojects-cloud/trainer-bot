import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot import texts
from app.bot.keyboards.inline import WEEKDAY_NAMES_FULL, sched_confirm_kb
from app.config import settings
from app.db.base import AsyncSessionLocal
from app.db.repositories.clients import get_by_id
from app.db.repositories.sessions import find_pending_in_window

logger = logging.getLogger(__name__)


async def confirmation_reminder_job() -> None:
    now = datetime.now(UTC)
    window_start = now + timedelta(minutes=30)
    window_end = now + timedelta(minutes=90)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        async with AsyncSessionLocal() as session:
            sessions = await find_pending_in_window(session, window_start, window_end)
            for rec in sessions:
                client = await get_by_id(session, rec.client_id)
                if client is None:
                    continue

                kyiv = ZoneInfo(settings.timezone)
                scheduled_kyiv = rec.scheduled_at.astimezone(kyiv)
                weekday_name = WEEKDAY_NAMES_FULL[scheduled_kyiv.weekday()]
                time_str = scheduled_kyiv.strftime("%H:%M")

                text = texts.SCHED_CONFIRM_PROMPT.format(
                    name=client.full_name,
                    weekday=weekday_name,
                    time=time_str,
                )
                await bot.send_message(
                    settings.trainer_telegram_id,
                    text,
                    reply_markup=sched_confirm_kb(rec.id),
                )
                logger.info(
                    "confirmation_reminder sent for session %d (%s)", rec.id, client.full_name
                )
    except Exception:
        logger.exception("confirmation_reminder_job failed")
    finally:
        await bot.session.close()
