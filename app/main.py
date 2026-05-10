import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import common
from app.bot.handlers.client import balance, history
from app.bot.handlers.trainer import add_client, delete_client, mark_session, overview, payment, payment_details, quick_mark, schedule, sessions_by_date
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.config import settings
from app.scheduler.jobs.auto_finalize import auto_finalize_job
from app.scheduler.jobs.confirmation_reminder import confirmation_reminder_job
from app.scheduler.jobs.expire_packages import expire_packages_job
from app.scheduler.jobs.prepare_auto_sessions import prepare_auto_sessions_job
from app.scheduler.scheduler import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # DbSessionMiddleware must be registered first (runs first, creates session)
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(AuthMiddleware())

    dp.include_router(common.router)
    dp.include_router(add_client.router)
    dp.include_router(delete_client.router)
    dp.include_router(payment.router)
    dp.include_router(mark_session.router)
    dp.include_router(overview.router)
    dp.include_router(sessions_by_date.router)
    dp.include_router(payment_details.router)
    dp.include_router(balance.router)
    dp.include_router(history.router)
    dp.include_router(schedule.router)
    dp.include_router(quick_mark.router)  # fallback: must be last

    scheduler.add_job(
        expire_packages_job,
        trigger="cron",
        hour=0,
        minute=5,
        id="expire_packages",
        replace_existing=True,
    )
    scheduler.add_job(
        prepare_auto_sessions_job,
        trigger="cron",
        hour=1,
        minute=0,
        id="prepare_auto_sessions",
        replace_existing=True,
    )
    scheduler.add_job(
        confirmation_reminder_job,
        trigger="cron",
        minute=0,
        id="confirmation_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        auto_finalize_job,
        trigger="interval",
        minutes=30,
        id="auto_finalize",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")

    logger.info("Starting bot (trainer_id=%s)", settings.trainer_telegram_id)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
