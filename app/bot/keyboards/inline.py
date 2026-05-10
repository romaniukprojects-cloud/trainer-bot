from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models.client import Client

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
WEEKDAY_NAMES_FULL = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]


# ─── quick text mark: disambiguation & confirm ───────────────────────────────

def sbd_date_choice_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Сьогодні", callback_data="sbd_today")
    builder.button(text="✏️ Інша дата", callback_data="sbd_other")
    builder.adjust(2)
    return builder.as_markup()


def date_choice_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Сьогодні", callback_data="date_today")
    builder.button(text="✏️ Інша дата", callback_data="date_other")
    builder.adjust(2)
    return builder.as_markup()


def disambiguate_kb(client_ids: list[int], client_names: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cid, name in zip(client_ids, client_names):
        builder.button(text=name, callback_data=f"disambig:{cid}")
    builder.button(text="❌ Пропустити", callback_data="disambig:skip")
    builder.adjust(1)
    return builder.as_markup()


def quick_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Підтвердити", callback_data="qm_confirm")
    builder.button(text="❌ Скасувати", callback_data="qm_cancel")
    builder.adjust(2)
    return builder.as_markup()


def quick_multi_kb(
    selections: dict[str, str | None],
    names: dict[str, str],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    active = sum(1 for v in selections.values() if v is not None)
    for cid_str, status in selections.items():
        name = names.get(cid_str, cid_str)
        builder.button(
            text=f"{_EMOJI[status]} {name}",
            callback_data=f"qm_toggle:{cid_str}",
        )
    if active > 0:
        builder.button(text=f"💾 Зберегти ({active})", callback_data="qm_save")
    builder.button(text="❌ Скасувати", callback_data="qm_cancel")
    builder.adjust(1)
    return builder.as_markup()

# ─── single-client picker (used for payment) ────────────────────────────────

def client_picker_kb(clients: list[Client], prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in clients:
        builder.button(text=c.full_name, callback_data=f"{prefix}:{c.id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── multi-select session marking ────────────────────────────────────────────

_CYCLE: dict[str | None, str | None] = {
    None: "attended",
    "attended": "missed",
    "missed": None,
}
_EMOJI: dict[str | None, str] = {
    None: "☐",
    "attended": "✅",
    "missed": "🚫",
}


def next_status(current: str | None) -> str | None:
    return _CYCLE[current]


# ─── schedule management ──────────────────────────────────────────────────────

def schedule_view_kb(has_slots: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Додати слот", callback_data="sched_add")
    if has_slots:
        builder.button(text="🗑 Видалити слот", callback_data="sched_remove")
    builder.adjust(2)
    return builder.as_markup()


def weekday_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, name in enumerate(WEEKDAY_NAMES):
        builder.button(text=name, callback_data=f"sched_weekday:{i}")
    builder.adjust(4)
    return builder.as_markup()


def slots_list_kb(slots) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        label = f"{WEEKDAY_NAMES[slot.weekday]} {slot.time_local.strftime('%H:%M')}"
        builder.button(text=label, callback_data=f"sched_del_slot:{slot.id}")
    builder.button(text="❌ Скасувати", callback_data="sched_cancel_remove")
    builder.adjust(1)
    return builder.as_markup()


def sched_confirm_kb(session_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Прийшов", callback_data=f"sched_confirm:{session_id}:attended")
    builder.button(text="🚫 Пропуск", callback_data=f"sched_confirm:{session_id}:missed")
    builder.adjust(2)
    return builder.as_markup()


def cancel_training_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Так, скасувати", callback_data="ct_confirm")
    builder.button(text="❌ Ні", callback_data="ct_cancel")
    builder.adjust(2)
    return builder.as_markup()


def multi_mark_kb(
    clients: list[Client],
    selections: dict[str, str | None],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    selected_count = sum(1 for v in selections.values() if v is not None)
    for c in clients:
        status = selections.get(str(c.id))
        builder.button(
            text=f"{_EMOJI[status]} {c.full_name}",
            callback_data=f"toggle_mk:{c.id}",
        )
    if selected_count > 0:
        builder.button(text=f"💾 Зберегти ({selected_count})", callback_data="save_mk")
    builder.button(text="❌ Скасувати", callback_data="cancel_mk")
    builder.adjust(1)
    return builder.as_markup()
