from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.client_menu import BTN_HISTORY
from app.db.models.client import Client
from app.db.repositories.sessions import get_recent_for_client
from app.utils.formatting import fmt_date_weekday

router = Router()

_STATUS_LABELS = {
    "attended": "✅ прийшов",
    "missed_no_notice": "🚫 не прийшов (без попередження)",
    "cancelled_in_advance": "🚫 скасував завчасно",
    "cancelled_by_trainer": "🚫 скасовано тренером",
    "pending_confirmation": "⏳ очікує підтвердження",
}


@router.message(F.text == BTN_HISTORY)
@router.message(Command("history"))
async def show_history(message: Message, session: AsyncSession, client: Client | None) -> None:
    if not client:
        await message.answer(texts.START_UNKNOWN)
        return

    records = await get_recent_for_client(session, client.id, limit=20)
    if not records:
        await message.answer(texts.HISTORY_EMPTY)
        return

    lines = [texts.HISTORY_HEADER]
    for r in records:
        dt = r.occurred_at or r.scheduled_at or r.created_at
        date_str = fmt_date_weekday(dt)
        label = _STATUS_LABELS.get(r.status.value, r.status.value)
        lines.append(f"{date_str} — {label}\n")

    await message.answer("".join(lines))
