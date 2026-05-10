from datetime import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import (
    WEEKDAY_NAMES_FULL,
    client_picker_kb,
    schedule_view_kb,
    sched_confirm_kb,
    slots_list_kb,
    weekday_kb,
)
from app.bot.keyboards.trainer_menu import BTN_SCHEDULE, trainer_main_kb
from app.bot.states.trainer import ScheduleStates
from app.db.models.session_record import SessionStatus
from app.db.repositories.clients import get_by_id
from app.db.repositories.schedule_slots import (
    create_slot,
    deactivate_slot,
    get_for_client,
)
from app.services.clients import get_active_clients
from app.services.schedule import confirm_session

router = Router()

_STATUS_LABELS = {
    SessionStatus.attended: "✅ прийшов",
    SessionStatus.missed_no_notice: "⊘ пропуск",
    SessionStatus.cancelled_in_advance: "🚫 скасував",
}


def _build_schedule_text(client_name: str, slots) -> str:
    text = texts.SCHEDULE_HEADER.format(name=client_name)
    if slots:
        for s in slots:
            text += texts.SCHEDULE_SLOT_LINE.format(
                weekday=WEEKDAY_NAMES_FULL[s.weekday],
                time=s.time_local.strftime("%H:%M"),
            )
    else:
        text += texts.SCHEDULE_NO_SLOTS
    return text


# ─── Entry ───────────────────────────────────────────────────────────────────

@router.message(F.text == BTN_SCHEDULE)
async def start_schedule(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.NO_ACTIVE_CLIENTS, reply_markup=trainer_main_kb)
        return
    await state.set_state(ScheduleStates.select_client)
    await message.answer(
        texts.SCHEDULE_SELECT_CLIENT,
        reply_markup=client_picker_kb(clients, "sched_client"),
    )


# ─── Client selected → show schedule ─────────────────────────────────────────

@router.callback_query(ScheduleStates.select_client, F.data.startswith("sched_client:"))
async def show_schedule(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    client_id = int(callback.data.split(":")[1])
    client = await get_by_id(session, client_id)
    if client is None:
        return

    slots = await get_for_client(session, client_id)
    await state.set_state(ScheduleStates.viewing)
    await state.update_data(client_id=client_id, client_name=client.full_name)

    text = _build_schedule_text(client.full_name, slots)
    try:
        await callback.message.edit_text(text, reply_markup=schedule_view_kb(bool(slots)))
    except TelegramBadRequest:
        pass


# ─── Add slot: pick weekday ───────────────────────────────────────────────────

@router.callback_query(ScheduleStates.viewing, F.data == "sched_add")
async def add_slot_weekday(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ScheduleStates.add_weekday)
    try:
        await callback.message.edit_text(texts.SCHEDULE_ADD_WEEKDAY, reply_markup=weekday_kb())
    except TelegramBadRequest:
        pass


@router.callback_query(ScheduleStates.add_weekday, F.data.startswith("sched_weekday:"))
async def add_slot_time(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    weekday = int(callback.data.split(":")[1])
    await state.update_data(weekday=weekday)
    await state.set_state(ScheduleStates.add_time)
    try:
        await callback.message.edit_text(texts.SCHEDULE_ADD_TIME)
    except TelegramBadRequest:
        pass


@router.message(ScheduleStates.add_time)
async def save_slot_time(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = (message.text or "").strip()
    try:
        t = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        await message.answer(texts.SCHEDULE_INVALID_TIME)
        return

    data = await state.get_data()
    client_id = data["client_id"]
    weekday = data["weekday"]
    client_name = data["client_name"]

    await create_slot(session, client_id=client_id, weekday=weekday, time_local=t)
    await session.commit()

    wd = WEEKDAY_NAMES_FULL[weekday]
    await state.set_state(ScheduleStates.viewing)
    await message.answer(
        texts.SCHEDULE_SLOT_ADDED.format(weekday=wd, time=t.strftime("%H:%M")),
        reply_markup=trainer_main_kb,
    )


# ─── Remove slot ─────────────────────────────────────────────────────────────

@router.callback_query(ScheduleStates.viewing, F.data == "sched_remove")
async def remove_slot_pick(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    data = await state.get_data()
    client_id = data["client_id"]
    slots = await get_for_client(session, client_id)

    if not slots:
        try:
            await callback.message.edit_text(texts.SCHEDULE_NO_SLOTS)
        except TelegramBadRequest:
            pass
        return

    await state.set_state(ScheduleStates.remove_slot)
    try:
        await callback.message.edit_text(
            texts.SCHEDULE_SELECT_FOR_REMOVE,
            reply_markup=slots_list_kb(slots),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(ScheduleStates.remove_slot, F.data.startswith("sched_del_slot:"))
async def do_remove_slot(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    slot_id = int(callback.data.split(":")[1])
    await deactivate_slot(session, slot_id)
    await session.commit()

    data = await state.get_data()
    client_id = data["client_id"]
    client_name = data["client_name"]

    slots = await get_for_client(session, client_id)
    await state.set_state(ScheduleStates.viewing)
    text = _build_schedule_text(client_name, slots)
    try:
        await callback.message.edit_text(
            texts.SCHEDULE_SLOT_REMOVED + "\n\n" + text,
            reply_markup=schedule_view_kb(bool(slots)),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(ScheduleStates.remove_slot, F.data == "sched_cancel_remove")
async def cancel_remove_slot(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    data = await state.get_data()
    client_id = data["client_id"]
    client_name = data["client_name"]

    slots = await get_for_client(session, client_id)
    await state.set_state(ScheduleStates.viewing)
    text = _build_schedule_text(client_name, slots)
    try:
        await callback.message.edit_text(text, reply_markup=schedule_view_kb(bool(slots)))
    except TelegramBadRequest:
        pass


# ─── Confirm auto-scheduled session (stateless — trainer taps from any context) ──

@router.callback_query(F.data.startswith("sched_confirm:"))
async def confirm_auto_session(
    callback: CallbackQuery, session: AsyncSession, is_trainer: bool
) -> None:
    await callback.answer()
    if not is_trainer:
        return

    parts = callback.data.split(":")
    session_id = int(parts[1])
    status_str = parts[2]

    status_map = {
        "attended": SessionStatus.attended,
        "missed": SessionStatus.missed_no_notice,
        "cancelled": SessionStatus.cancelled_in_advance,
    }
    status = status_map.get(status_str)
    if status is None:
        return

    rec, consumed, total = await confirm_session(session, session_id, status)

    if rec is None or rec.status != status:
        try:
            await callback.message.edit_text(texts.SCHED_CONFIRM_ALREADY)
        except TelegramBadRequest:
            pass
        return

    client = await get_by_id(session, rec.client_id)
    name = client.full_name if client else "?"
    pkg_text = f"\nВикористано: <b>{consumed}/{total}</b>" if consumed is not None else ""
    result_text = f"✅ <b>{name}</b> — {_STATUS_LABELS.get(status, status_str)}{pkg_text}"

    try:
        await callback.message.edit_text(result_text)
    except TelegramBadRequest:
        pass
