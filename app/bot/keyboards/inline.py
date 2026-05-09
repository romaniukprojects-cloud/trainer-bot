from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models.client import Client


# ─── quick text mark: disambiguation & confirm ───────────────────────────────

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
    "missed": "cancelled",
    "cancelled": None,
}
_EMOJI: dict[str | None, str] = {
    None: "☐",
    "attended": "✅",
    "missed": "⊘",
    "cancelled": "🚫",
}


def next_status(current: str | None) -> str | None:
    return _CYCLE[current]


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
