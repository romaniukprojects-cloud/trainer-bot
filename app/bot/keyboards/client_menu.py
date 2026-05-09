from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_BALANCE = "💳 Мій баланс"
BTN_HISTORY = "📖 Історія"

client_main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_BALANCE), KeyboardButton(text=BTN_HISTORY)],
    ],
    resize_keyboard=True,
)
