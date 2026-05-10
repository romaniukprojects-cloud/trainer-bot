from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import disambiguate_kb, quick_multi_kb
from app.bot.keyboards.trainer_menu import trainer_main_kb
from app.bot.states.trainer import QuickMarkStates
from app.db.models.client import Client
from app.db.models.session_record import SessionStatus
from app.db.repositories.clients import get_by_id
from app.services.clients import get_active_clients
from app.services.name_parser import parse_text
from app.services.sessions import mark_attended

router = Router()

_STATUS_KEY = {
    SessionStatus.attended: "attended",
    SessionStatus.missed_no_notice: "missed",
    SessionStatus.cancelled_in_advance: "cancelled",
}
_STATUS_MAP = {
    "attended": SessionStatus.attended,
    "missed": SessionStatus.missed_no_notice,
    "cancelled": SessionStatus.cancelled_in_advance,
}
_STATUS_LABELS = {
    "attended": "✅ прийшов",
    "missed": "⊘ пропуск",
    "cancelled": "🚫 скасував",
}

_CYCLE = {
    None: "attended",
    "attended": "missed",
    "missed": "cancelled",
    "cancelled": None,
}


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def handle_free_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    is_trainer: bool,
) -> None:
    if not is_trainer:
        return

    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.NO_ACTIVE_CLIENTS)
        return

    entries = parse_text(message.text, clients)
    if not any(e.matches for e in entries):
        await message.answer(texts.QUICK_MARK_NO_MATCH)
        return

    resolved: list[dict] = []
    pending: list[dict] = []
    unrecognized: list[str] = []

    for entry in entries:
        if entry.is_resolved:
            c = entry.matches[0]
            resolved.append({
                "client_id": c.id,
                "status": _STATUS_KEY.get(entry.status, "attended"),
                "name": c.full_name,
            })
        elif entry.is_ambiguous:
            pending.append({
                "token": entry.clean_name,
                "candidate_ids": [c.id for c in entry.matches],
                "candidate_names": [c.full_name for c in entry.matches],
                "status": _STATUS_KEY.get(entry.status, "attended"),
            })
        else:
            unrecognized.append(entry.token)

    await state.update_data(resolved=resolved, pending=pending, unrecognized=unrecognized)

    if pending:
        await state.set_state(QuickMarkStates.disambiguating)
        await _ask_disambiguation(message, pending[0])
    else:
        await state.set_state(QuickMarkStates.confirming)
        await _show_multi_select(message, resolved, unrecognized)


async def _ask_disambiguation(msg_or_cb: Message | CallbackQuery, item: dict) -> None:
    text = texts.QUICK_MARK_AMBIGUOUS.format(token=item["token"])
    kb = disambiguate_kb(item["candidate_ids"], item["candidate_names"])
    if isinstance(msg_or_cb, Message):
        await msg_or_cb.answer(text, reply_markup=kb)
    else:
        await msg_or_cb.message.edit_text(text, reply_markup=kb)


async def _show_multi_select(
    msg_or_cb: Message | CallbackQuery,
    resolved: list[dict],
    unrecognized: list[str],
    edit: bool = False,
) -> None:
    selections = {str(item["client_id"]): item["status"] for item in resolved}
    names = {str(item["client_id"]): item["name"] for item in resolved}

    header = "📋 <b>Відмітити заняття:</b>\n\nТапни на ім'я — змінить статус по колу."
    if unrecognized:
        header += "\n\n❓ <b>Не розпізнано:</b> " + ", ".join(f"«{t}»" for t in unrecognized)

    kb = quick_multi_kb(selections, names)
    if edit and isinstance(msg_or_cb, CallbackQuery):
        await msg_or_cb.message.edit_text(header, reply_markup=kb)
    elif isinstance(msg_or_cb, Message):
        await msg_or_cb.answer(header, reply_markup=kb)
    else:
        await msg_or_cb.message.edit_text(header, reply_markup=kb)


@router.callback_query(QuickMarkStates.disambiguating, F.data.startswith("disambig:"))
async def resolve_ambiguity(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    data = await state.get_data()
    pending: list[dict] = data["pending"]
    resolved: list[dict] = data["resolved"]
    unrecognized: list[str] = data["unrecognized"]
    current = pending[0]

    choice = callback.data.split(":")[1]
    if choice != "skip":
        client: Client | None = await get_by_id(session, int(choice))
        if client:
            resolved.append({
                "client_id": client.id,
                "status": current["status"],
                "name": client.full_name,
            })
    else:
        unrecognized.append(current["token"])

    pending = pending[1:]
    await state.update_data(resolved=resolved, pending=pending, unrecognized=unrecognized)
    await callback.answer()

    if pending:
        await _ask_disambiguation(callback, pending[0])
    else:
        await state.set_state(QuickMarkStates.confirming)
        await _show_multi_select(callback, resolved, unrecognized, edit=True)


@router.callback_query(QuickMarkStates.confirming, F.data.startswith("qm_toggle:"))
async def toggle_status(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    resolved: list[dict] = data["resolved"]
    unrecognized: list[str] = data.get("unrecognized", [])

    cid_str = callback.data.split(":")[1]
    for item in resolved:
        if str(item["client_id"]) == cid_str:
            item["status"] = _CYCLE[item["status"]]
            break

    await state.update_data(resolved=resolved)

    selections = {str(item["client_id"]): item["status"] for item in resolved}
    names = {str(item["client_id"]): item["name"] for item in resolved}

    header = "📋 <b>Відмітити заняття:</b>\n\nТапни на ім'я — змінить статус по колу."
    if unrecognized:
        header += "\n\n❓ <b>Не розпізнано:</b> " + ", ".join(f"«{t}»" for t in unrecognized)

    await callback.message.edit_text(header, reply_markup=quick_multi_kb(selections, names))
    await callback.answer()


@router.callback_query(QuickMarkStates.confirming, F.data == "qm_save")
async def save_quick_mark(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    data = await state.get_data()
    resolved: list[dict] = data["resolved"]
    await state.clear()

    lines = ["✅ <b>Збережено:</b>\n\n"]
    for item in resolved:
        if item["status"] is None:
            continue
        _, consumed, total, is_dup = await mark_attended(
            session,
            item["client_id"],
            _STATUS_MAP[item["status"]],
        )
        label = _STATUS_LABELS.get(item["status"], item["status"])
        if is_dup:
            lines.append(f"<b>{item['name']}</b> — {label} ⚠️ вже відмічено сьогодні\n")
        elif consumed is not None:
            lines.append(f"<b>{item['name']}</b> — {label} ({consumed}/{total})\n")
        else:
            lines.append(f"<b>{item['name']}</b> — {label} ⚠️ немає пакета\n")

    await callback.message.edit_text("".join(lines))
    await callback.answer()
    await callback.message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)


@router.callback_query(QuickMarkStates.confirming, F.data == "qm_cancel")
async def cancel_quick_mark(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.CANCEL_ACTION)
    await callback.answer()
    await callback.message.answer("Вибери дію:", reply_markup=trainer_main_kb)
