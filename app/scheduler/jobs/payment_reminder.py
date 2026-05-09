import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings

logger = logging.getLogger(__name__)

_TEXT = (
    "⚠️ <b>{name}</b> використав(ла) 9 із 10 занять.\n"
    "Час нагадати про оплату наступного пакета!"
)


async def payment_reminder_job(client_name: str) -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await bot.send_message(
            settings.trainer_telegram_id,
            _TEXT.format(name=client_name),
        )
        logger.info("payment_reminder sent for %s", client_name)
    except Exception:
        logger.exception("payment_reminder failed for %s", client_name)
    finally:
        await bot.session.close()
