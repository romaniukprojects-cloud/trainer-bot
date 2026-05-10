from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import sbd_date_choice_kb
from app.bot.keyboards.trainer_menu import BTN_SESSIONS_BY_DATE
from app.bot.states.trainer import SessionsByDateStates
from app.config import settings
from app.db.models.session_record import SessionStatus
from app.db.repositories.packages import get_active_for_client, get_consumed_count
from app.db.repositories.sessions import get_all_on_date
from app.utils.tz import now_kyiv

router = Router()

_STATUS_EMOJI = {
    SessionStatus.attended: "✅",
    SessionStatus.missed_no_notice: "🚫",
    SessionStatus.cancelled_in_advance: "🚫",
}


def _parse_date(text: str) -> datetime | None:
    tz = ZoneInfo(settings.timezone)
    today = now_kyiv().date()
    try:
        d = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        return datetime(d.year, d.month, d.day, tzinfo=tz)
    except ValueError:
        pass
    try:
        parsed = datetime.strptime(text.strip(), "%d.%m")
        d = today.replace(month=parsed.month, day=parsed.day)
        if d > today:
            d = d.replace(year=d.year - 1)
        return datetime(d.year, d.month, d.day, tzinfo=tz)
    except ValueError:
        pass
    return None


async def _render(db: AsyncSession, date_local: datetime) -> str:
    tz = ZoneInfo(settings.timezone)
    day_start = datetime(date_local.year, date_local.month, date_local.day, tzinfo=tz).astimezone(UTC)
    day_end = day_start + timedelta(days=1)
    rows = await get_all_on_date(db, day_start, day_end)
    date_str = date_local.strftime("%d.%m.%Y")
    if not rows:
        return texts.SBD_EMPTY.format(date=date_str)
    lines = [texts.SBD_HEADER.format(date=date_str)]
    pkg_cache: dict[int, str] = {}
    for record, client_name in rows:
        emoji = _STATUS_EMOJI.get(record.status, "•")
        client_id = record.client_id
        if client_id not in pkg_cache:
            pkgs = await get_active_for_client(db, client_id)
            if pkgs:
                used = await get_consumed_count(db, pkgs[0].id)
                pkg_cache[client_id] = f"{used}/{pkgs[0].total_sessions}"
            else:
                pkg_cache[client_id] = ""
        suffix = f" ({pkg_cache[client_id]})" if pkg_cache[client_id] else ""
        lines.append(f"{emoji} {client_name}{suffix}\n")
    lines.append(texts.SBD_TOTAL.format(count=len(rows)))
    return "".join(lines)


@router.message(F.text == BTN_SESSIONS_BY_DATE)
async def start(message: Message, state: FSMContext) -> None:
    await state.set_state(SessionsByDateStates.choosing)
    await message.answer(texts.SBD_CHOOSE_DATE, reply_markup=sbd_date_choice_kb())


@router.callback_query(SessionsByDateStates.choosing, F.data == "sbd_today")
async def cb_today(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    await state.clear()
    text = await _render(session, now_kyiv())
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        pass


@router.callback_query(SessionsByDateStates.choosing, F.data == "sbd_other")
async def cb_other(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SessionsByDateStates.enter_date)
    await callback.answer()
    try:
        await callback.message.edit_text(texts.SBD_ASK_DATE)
    except TelegramBadRequest:
        pass


@router.message(SessionsByDateStates.enter_date)
async def got_date(message: Message, state: FSMContext, session: AsyncSession) -> None:
    date = _parse_date(message.text or "")
    if date is None:
        await message.answer(texts.INVALID_DATE)
        return
    await state.clear()
    text = await _render(session, date)
    await message.answer(text)
