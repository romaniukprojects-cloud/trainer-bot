from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import date_choice_kb, multi_mark_kb, next_status
from app.bot.keyboards.trainer_menu import BTN_MARK_SESSION, trainer_main_kb
from app.bot.states.trainer import MarkSessionStates
from app.config import settings
from app.db.models.session_record import SessionStatus
from app.db.repositories.clients import get_by_id
from app.services.clients import get_active_clients
from app.services.sessions import mark_attended
from app.utils.tz import now_kyiv

router = Router()

_STATUS_MAP = {
    "attended": SessionStatus.attended,
    "missed": SessionStatus.missed_no_notice,
}
_STATUS_LABELS = {
    "attended": "прийшов ✅",
    "missed": "пропуск 🚫",
}


def _parse_date(text: str) -> datetime | None:
    tz = ZoneInfo(settings.timezone)
    today = now_kyiv().date()
    for fmt in ("%d.%m.%Y", "%d.%m"):
        try:
            parsed = datetime.strptime(text.strip(), fmt)
            if fmt == "%d.%m.%Y":
                d = parsed.date()
            else:
                d = today.replace(month=parsed.month, day=parsed.day)
                if d > today:
                    d = d.replace(year=d.year - 1)
            return datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz).astimezone(UTC)
        except ValueError:
            continue
    return None


@router.message(F.text == BTN_MARK_SESSION)
async def start_mark(message: Message, state: FSMContext, session: AsyncSession) -> None:
    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.NO_ACTIVE_CLIENTS)
        return
    selections: dict[str, str | None] = {str(c.id): None for c in clients}
    await state.set_state(MarkSessionStates.marking)
    await state.update_data(selections=selections, client_ids=[c.id for c in clients])
    await message.answer(texts.MULTI_MARK_PROMPT, reply_markup=multi_mark_kb(clients, selections))


@router.callback_query(MarkSessionStates.marking, F.data.startswith("toggle_mk:"))
async def toggle_client(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()

    client_id_str = callback.data.split(":")[1]
    data = await state.get_data()
    selections: dict[str, str | None] = data["selections"]
    selections[client_id_str] = next_status(selections.get(client_id_str))
    await state.update_data(selections=selections)

    clients = [await get_by_id(session, cid) for cid in data["client_ids"]]
    try:
        await callback.message.edit_reply_markup(reply_markup=multi_mark_kb(clients, selections))
    except TelegramBadRequest:
        pass


@router.callback_query(MarkSessionStates.marking, F.data == "save_mk")
async def ask_date(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(MarkSessionStates.choosing_date)
    try:
        await callback.message.edit_text(texts.SESSION_ASK_DATE, reply_markup=date_choice_kb())
    except TelegramBadRequest:
        pass


@router.callback_query(MarkSessionStates.choosing_date, F.data == "date_today")
async def date_today(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    await _do_save(callback, state, session, occurred_at=datetime.now(UTC))


@router.callback_query(MarkSessionStates.choosing_date, F.data == "date_other")
async def date_other(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(MarkSessionStates.enter_date)
    try:
        await callback.message.edit_text(texts.SBD_ASK_DATE)
    except TelegramBadRequest:
        pass


@router.message(MarkSessionStates.enter_date)
async def got_date(message: Message, state: FSMContext, session: AsyncSession) -> None:
    occurred_at = _parse_date(message.text or "")
    if occurred_at is None:
        await message.answer(texts.INVALID_DATE)
        return
    await _do_save_from_message(message, state, session, occurred_at)


async def _do_save(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    occurred_at: datetime,
) -> None:
    data = await state.get_data()
    selections: dict[str, str | None] = data["selections"]
    lines = await _build_lines(session, selections, occurred_at)
    await state.clear()
    summary = "✅ Збережено:\n\n" + "\n".join(lines) if lines else texts.CANCEL_ACTION
    try:
        await callback.message.edit_text(summary)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)


async def _do_save_from_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    occurred_at: datetime,
) -> None:
    data = await state.get_data()
    selections: dict[str, str | None] = data["selections"]
    lines = await _build_lines(session, selections, occurred_at)
    await state.clear()
    summary = "✅ Збережено:\n\n" + "\n".join(lines) if lines else texts.CANCEL_ACTION
    await message.answer(summary, reply_markup=trainer_main_kb)


async def _build_lines(
    session: AsyncSession,
    selections: dict[str, str | None],
    occurred_at: datetime,
) -> list[str]:
    lines = []
    for client_id_str, status_key in selections.items():
        if status_key is None:
            continue
        client = await get_by_id(session, int(client_id_str))
        _, consumed, total, is_dup = await mark_attended(
            session, client.id, _STATUS_MAP[status_key], occurred_at=occurred_at
        )
        label = _STATUS_LABELS[status_key]
        if is_dup:
            lines.append(f"<b>{client.full_name}</b> — {label} ⚠️ вже відмічено")
        elif consumed is not None:
            lines.append(f"<b>{client.full_name}</b> — {label} ({consumed}/{total})")
        else:
            lines.append(f"<b>{client.full_name}</b> — {label} ⚠️ немає пакета")
    return lines


@router.callback_query(MarkSessionStates.marking, F.data == "cancel_mk")
async def cancel_mark(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(texts.CANCEL_ACTION)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери дію:", reply_markup=trainer_main_kb)
