import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.base import AsyncSessionLocal
from app.db.repositories import packages as pkg_repo
from app.db.repositories.clients import get_by_id as get_client

logger = logging.getLogger(__name__)

_TEXT_CLIENT = (
    "⚠️ У вас залишилось <b>1 заняття</b> з поточного пакету.\n\n"
    "Пакет дійсний до: <b>{expires}</b>\n\n"
    "Будь ласка, оплатіть новий пакет занять.\n\n"
    "Реквізити тренера:\n{payment_details}"
)
_TEXT_CLIENT_NO_EXPIRES = (
    "⚠️ У вас залишилось <b>1 заняття</b> з поточного пакету.\n\n"
    "Будь ласка, оплатіть новий пакет занять.\n\n"
    "Реквізити тренера:\n{payment_details}"
)
_TEXT_CLIENT_NO_DETAILS = (
    "⚠️ У вас залишилось <b>1 заняття</b> з поточного пакету.\n\n"
    "Будь ласка, зв'яжіться з тренером для оплати наступного пакета."
)
_TEXT_TRAINER_NOTIFIED = (
    "ℹ️ <b>{name}</b> використав(ла) 9/10 занять.\n"
    "Нагадування про оплату надіслано клієнту."
)
_TEXT_TRAINER_NO_TELEGRAM = (
    "⚠️ <b>{name}</b> використав(ла) 9/10 занять.\n"
    "Клієнт не підключений до бота — нагадайте про оплату вручну."
)
_TEXT_TRAINER_HAS_NEXT = (
    "ℹ️ <b>{name}</b> використав(ла) 9/10 занять.\n"
    "У клієнта вже є наступний пакет — нагадування пропущено."
)


async def payment_reminder_job(
    client_id: int,
    payment_details: str | None,
    expires_at_str: str | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        client = await get_client(session, client_id)
        if client is None:
            logger.warning("payment_reminder: client %d not found", client_id)
            return

        active_packages = await pkg_repo.get_active_for_client(session, client_id)

        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            if len(active_packages) > 1:
                await bot.send_message(
                    settings.trainer_telegram_id,
                    _TEXT_TRAINER_HAS_NEXT.format(name=client.full_name),
                )
                logger.info("payment_reminder skipped for %s (has next package)", client.full_name)
                return

            if client.telegram_user_id:
                if payment_details and expires_at_str:
                    text = _TEXT_CLIENT.format(expires=expires_at_str, payment_details=payment_details)
                elif payment_details:
                    text = _TEXT_CLIENT_NO_EXPIRES.format(payment_details=payment_details)
                else:
                    text = _TEXT_CLIENT_NO_DETAILS
                await bot.send_message(client.telegram_user_id, text)
                await bot.send_message(
                    settings.trainer_telegram_id,
                    _TEXT_TRAINER_NOTIFIED.format(name=client.full_name),
                )
                logger.info("payment_reminder sent to client %s", client.full_name)
            else:
                await bot.send_message(
                    settings.trainer_telegram_id,
                    _TEXT_TRAINER_NO_TELEGRAM.format(name=client.full_name),
                )
                logger.info("payment_reminder sent to trainer for %s (no telegram)", client.full_name)

        except Exception:
            logger.exception("payment_reminder failed for client_id=%d", client_id)
        finally:
            await bot.session.close()
