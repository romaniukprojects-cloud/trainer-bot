import json
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.trainer_menu import BTN_CORRECTIONS, trainer_main_kb
from app.config import settings
from app.db.models.audit_log import AuditLog
from app.db.models.package import Package, PackageStatus
from app.db.models.session_record import SessionRecord, SessionStatus
from app.db.repositories import audit_log as audit_repo
from app.db.repositories import packages as pkg_repo

router = Router()

_STATUS_LABELS = {
    "attended": "✅ прийшов",
    "missed": "🚫 пропуск",
}


def _kyiv_date_str(occurred_at_str: str, fmt: str = "%d.%m") -> str:
    try:
        dt = datetime.fromisoformat(occurred_at_str)
        return dt.astimezone(ZoneInfo(settings.timezone)).strftime(fmt)
    except Exception:
        return "?"


def _corrections_kb(entries: list[AuditLog]) -> InlineKeyboardMarkup:
    buttons = []
    for entry in entries:
        payload = json.loads(entry.payload_json)
        name = payload.get("client_name", "?")
        status_key = payload.get("status", "attended")
        status_icon = "✅" if status_key == "attended" else "🚫"
        date_str = _kyiv_date_str(payload.get("occurred_at", ""))
        label = f"{status_icon} {name} / {date_str}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"correct:{entry.id}")])
    buttons.append([InlineKeyboardButton(text="❌ Закрити", callback_data="correct_close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _confirm_kb(audit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Так, скасувати", callback_data=f"correct_do:{audit_id}"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="correct_back"),
        ]
    ])


@router.message(F.text == BTN_CORRECTIONS)
async def show_corrections(message: Message, session: AsyncSession) -> None:
    entries = await audit_repo.get_last_n(session, n=10)
    if not entries:
        await message.answer(texts.CORRECTIONS_EMPTY, reply_markup=trainer_main_kb)
        return
    await message.answer(texts.CORRECTIONS_HEADER, reply_markup=_corrections_kb(entries))


@router.callback_query(F.data.startswith("correct:"))
async def on_correct_select(callback: CallbackQuery, session: AsyncSession) -> None:
    audit_id = int(callback.data.split(":")[1])
    entry = await session.get(AuditLog, audit_id)
    if entry is None:
        await callback.answer("Запис не знайдено.", show_alert=True)
        return

    payload = json.loads(entry.payload_json)
    name = payload.get("client_name", "?")
    status_key = payload.get("status", "attended")
    status_label = _STATUS_LABELS.get(status_key, status_key)
    date_str = _kyiv_date_str(payload.get("occurred_at", ""), "%d.%m.%Y")

    text = texts.CORRECTIONS_CONFIRM.format(name=name, status=status_label, date=date_str)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=_confirm_kb(audit_id))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("correct_do:"))
async def on_correct_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    audit_id = int(callback.data.split(":")[1])
    entry = await session.get(AuditLog, audit_id)
    if entry is None:
        await callback.answer("Запис не знайдено.", show_alert=True)
        return

    payload = json.loads(entry.payload_json)
    name = payload.get("client_name", "?")
    date_str = _kyiv_date_str(payload.get("occurred_at", ""))

    rec = await session.get(SessionRecord, entry.entity_id)
    if rec is None:
        await callback.answer("Заняття не знайдено.", show_alert=True)
        return

    if rec.status not in (SessionStatus.attended, SessionStatus.missed_no_notice):
        await callback.answer()
        try:
            await callback.message.edit_text(texts.CORRECTIONS_ALREADY_CANCELLED)
        except TelegramBadRequest:
            pass
        await callback.message.answer("Вибери дію:", reply_markup=trainer_main_kb)
        return

    rec.status = SessionStatus.cancelled_by_trainer

    if rec.package_id:
        pkg = await session.get(Package, rec.package_id)
        if pkg and pkg.status == PackageStatus.exhausted:
            consumed = await pkg_repo.get_consumed_count(session, pkg.id)
            if consumed < pkg.total_sessions:
                pkg.status = PackageStatus.active

    await session.commit()
    await callback.answer()
    try:
        await callback.message.edit_text(texts.CORRECTIONS_DONE.format(name=name, date=date_str))
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери дію:", reply_markup=trainer_main_kb)


@router.callback_query(F.data == "correct_back")
async def on_correct_back(callback: CallbackQuery, session: AsyncSession) -> None:
    entries = await audit_repo.get_last_n(session, n=10)
    await callback.answer()
    try:
        if entries:
            await callback.message.edit_text(texts.CORRECTIONS_HEADER, reply_markup=_corrections_kb(entries))
        else:
            await callback.message.edit_text(texts.CORRECTIONS_EMPTY)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "correct_close")
async def on_correct_close(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
