from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import multi_mark_kb, next_status
from app.bot.keyboards.trainer_menu import BTN_MARK_SESSION, trainer_main_kb
from app.bot.states.trainer import MarkSessionStates
from app.db.models.session_record import SessionStatus
from app.db.repositories.clients import get_by_id
from app.services.clients import get_active_clients
from app.services.sessions import mark_attended

router = Router()

_STATUS_MAP = {
    "attended": SessionStatus.attended,
    "missed": SessionStatus.missed_no_notice,
    "cancelled": SessionStatus.cancelled_in_advance,
}
_STATUS_LABELS = {
    "attended": "прийшов ✅",
    "missed": "пропуск ⊘",
    "cancelled": "скасував завчасно 🚫",
}


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
    # Answer immediately so the spinner never hangs if the edit below raises.
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
        # Rapid double-tap: state already updated, keyboard unchanged — safe to ignore.
        pass


@router.callback_query(MarkSessionStates.marking, F.data == "save_mk")
async def save_sessions(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()

    data = await state.get_data()
    selections: dict[str, str | None] = data["selections"]

    lines = []
    for client_id_str, status_key in selections.items():
        if status_key is None:
            continue
        client = await get_by_id(session, int(client_id_str))
        _, consumed, total, is_dup = await mark_attended(session, client.id, _STATUS_MAP[status_key])
        label = _STATUS_LABELS[status_key]
        if is_dup:
            lines.append(f"<b>{client.full_name}</b> — {label} ⚠️ вже відмічено сьогодні")
        elif consumed is not None:
            lines.append(f"<b>{client.full_name}</b> — {label} ({consumed}/{total})")
        else:
            lines.append(f"<b>{client.full_name}</b> — {label} ⚠️ немає пакета")

    # Clear state only after all DB writes succeed.
    await state.clear()

    summary = "✅ Збережено:\n\n" + "\n".join(lines) if lines else texts.CANCEL_ACTION
    try:
        await callback.message.edit_text(summary)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)


@router.callback_query(MarkSessionStates.marking, F.data == "cancel_mk")
async def cancel_mark(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(texts.CANCEL_ACTION)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери дію:", reply_markup=trainer_main_kb)
