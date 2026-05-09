from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.client_menu import BTN_BALANCE
from app.db.models.client import Client
from app.db.repositories.packages import get_active_for_client, get_consumed_count
from app.utils.formatting import days_until, fmt_date

router = Router()


@router.message(F.text == BTN_BALANCE)
@router.message(Command("balance"))
async def show_balance(message: Message, session: AsyncSession, client: Client | None) -> None:
    if not client:
        await message.answer(texts.START_UNKNOWN)
        return

    packages = await get_active_for_client(session, client.id)
    if not packages:
        await message.answer(texts.BALANCE_NO_PACKAGE)
        return

    lines = [texts.BALANCE_HEADER]
    for pkg in packages:
        used = await get_consumed_count(session, pkg.id)
        lines.append(
            texts.BALANCE_ACTIVE.format(
                used=used,
                total=pkg.total_sessions,
                expires=fmt_date(pkg.expires_at),
                days=days_until(pkg.expires_at),
            )
        )

    await message.answer("".join(lines))
