from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_ADD_CLIENT = "➕ Додати клієнта"
BTN_REGISTER_PAYMENT = "💰 Зареєструвати оплату"
BTN_MARK_SESSION = "✅ Відмітити заняття"
BTN_OVERVIEW = "📋 Стан клієнтів"

trainer_main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_ADD_CLIENT), KeyboardButton(text=BTN_REGISTER_PAYMENT)],
        [KeyboardButton(text=BTN_MARK_SESSION), KeyboardButton(text=BTN_OVERVIEW)],
    ],
    resize_keyboard=True,
)
