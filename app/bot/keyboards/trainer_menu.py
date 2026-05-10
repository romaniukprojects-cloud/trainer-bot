from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_ADD_CLIENT = "➕ Додати клієнта"
BTN_REGISTER_PAYMENT = "💰 Зареєструвати оплату"
BTN_MARK_SESSION = "✅ Відмітити заняття"
BTN_OVERVIEW = "📋 Стан клієнтів"
BTN_SESSIONS_BY_DATE = "📅 По датах"
BTN_DELETE_CLIENT = "🗑 Видалити клієнта"
BTN_PAYMENT_DETAILS = "💳 Реквізити"

trainer_main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_ADD_CLIENT), KeyboardButton(text=BTN_REGISTER_PAYMENT)],
        [KeyboardButton(text=BTN_MARK_SESSION), KeyboardButton(text=BTN_OVERVIEW)],
        [KeyboardButton(text=BTN_SESSIONS_BY_DATE), KeyboardButton(text=BTN_PAYMENT_DETAILS)],
        [KeyboardButton(text=BTN_DELETE_CLIENT)],
    ],
    resize_keyboard=True,
)
