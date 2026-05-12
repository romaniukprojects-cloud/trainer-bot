from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_ADD_CLIENT = "➕ Додати клієнта"
BTN_REGISTER_PAYMENT = "💰 Зареєструвати оплату"
BTN_MARK_SESSION = "✅ Відмітити заняття"
BTN_OVERVIEW = "📋 Стан клієнтів"
BTN_SESSIONS_BY_DATE = "📅 По датах"
BTN_DELETE_CLIENT = "🗑 Видалити клієнта"
BTN_PAYMENT_DETAILS = "💳 Реквізити"
BTN_SCHEDULE = "📆 Розклад"
BTN_CANCEL_TRAINING = "🚫 Скасувати тренування"
BTN_CORRECTIONS = "✏️ Виправити заняття"
BTN_INCOME = "💵 Дохід за період"

trainer_main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_ADD_CLIENT), KeyboardButton(text=BTN_REGISTER_PAYMENT)],
        [KeyboardButton(text=BTN_MARK_SESSION), KeyboardButton(text=BTN_OVERVIEW)],
        [KeyboardButton(text=BTN_SESSIONS_BY_DATE), KeyboardButton(text=BTN_SCHEDULE)],
        [KeyboardButton(text=BTN_PAYMENT_DETAILS), KeyboardButton(text=BTN_DELETE_CLIENT)],
        [KeyboardButton(text=BTN_CANCEL_TRAINING), KeyboardButton(text=BTN_CORRECTIONS)],
        [KeyboardButton(text=BTN_INCOME)],
    ],
    resize_keyboard=True,
)
