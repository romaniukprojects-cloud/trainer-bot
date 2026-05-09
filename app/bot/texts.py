# /start
START_TRAINER = "Привіт, тренер! 👋\nВибери дію з меню або напиши імена клієнтів, щоб швидко відмітити заняття."
START_UNKNOWN = "Привіт! Зверніться до вашого тренера для підключення."
START_CLIENT = "Привіт! Вибери дію:"
START_CLIENT_LINKED = "✅ Акаунт підключено! Тепер ти можеш переглядати свій баланс."
START_CODE_INVALID = "❌ Посилання недійсне або застаріло. Попросіть тренера надіслати нове."

# Generic
CANCEL_ACTION = "Дію скасовано."
UNKNOWN_COMMAND = "Не зрозумів. Скористайтеся меню."

# Add client
ASK_CLIENT_NAME = "Введіть повне ім'я клієнта:"
ASK_CLIENT_PHONE = "Телефон клієнта (або /skip):"
ASK_CLIENT_ALIASES = "Псевдоніми через кому (або /skip):\n<i>Наприклад: Маринка, Марина К.</i>"
CLIENT_ADDED = (
    "✅ Клієнта <b>{name}</b> додано!\n\n"
    "Посилання для прив'язки Telegram (дійсне 24 год):\n"
    "<code>{link}</code>\n\n"
    "Перешліть його клієнту."
)

# Register payment
ASK_PAYMENT_CLIENT = "Виберіть клієнта для реєстрації оплати:"
ASK_PAYMENT_AMOUNT = "Введіть суму оплати (грн):\n<i>Наприклад: 1500</i>"
ASK_PAYMENT_DATE = "Дата оплати:"
ASK_PAYMENT_DATE_MANUAL = (
    "Введіть дату у форматі <code>ДД.ММ</code> або <code>ДД.ММ.РРРР</code>:\n"
    "<i>Наприклад: 25.04 або 25.04.2025</i>"
)
INVALID_DATE = "❌ Невірна дата. Введіть у форматі ДД.ММ або ДД.ММ.РРРР"
PAYMENT_REGISTERED = (
    "✅ Оплату зареєстровано!\n\n"
    "<b>{name}</b>: {price} грн\n"
    "Пакет до: <b>{expires}</b>"
)
INVALID_AMOUNT = "❌ Невірна сума. Введіть число, наприклад: <code>1500</code>"
NO_ACTIVE_CLIENTS = "Клієнтів поки немає. Спочатку додайте клієнта через «➕ Додати клієнта»."

# Mark session (multi-select)
MULTI_MARK_PROMPT = (
    "Натискай на клієнтів щоб відмітити:\n\n"
    "☐ — не відмічено (пропустити)\n"
    "✅ — прийшов\n"
    "⊘ — не прийшов (без попередження)\n"
    "🚫 — скасував завчасно\n\n"
    "Кожен наступний тап змінює статус по колу."
)
ASK_SESSION_CLIENT = "Виберіть клієнта:"
ASK_SESSION_STATUS = "Статус заняття для <b>{name}</b>:"
SESSION_MARKED = (
    "✅ Відмічено!\n\n"
    "<b>{name}</b> — {status}\n"
    "Використано: <b>{used}/{total}</b>"
)
SESSION_MARKED_NO_PACKAGE = (
    "⚠️ Відмічено: <b>{name}</b> — {status}\n"
    "Активного пакета немає, заняття не списано."
)

# Overview
OVERVIEW_HEADER = "📋 <b>Стан клієнтів</b>\n\n"
OVERVIEW_CLIENT_ACTIVE = "{name} — {used}/{total}, до {expires} ({days} дн.)\n"
OVERVIEW_CLIENT_NO_PACKAGE = "{name} — <i>немає пакета</i>\n"
OVERVIEW_EMPTY = "Клієнтів ще немає."

# Client history
HISTORY_HEADER = "📖 <b>Ваші заняття</b>\n\n"
HISTORY_EMPTY = "Занять ще не було."

# Client balance
BALANCE_HEADER = "💳 <b>Ваш баланс</b>\n\n"
BALANCE_ACTIVE = "<b>{used}/{total}</b> занять\nПакет до: <b>{expires}</b> ({days} дн.)\n"
BALANCE_NO_PACKAGE = "Активного пакета немає. Зверніться до тренера."

# Delete client
ASK_DELETE_CLIENT = "Виберіть клієнта для видалення:"
DELETE_CONFIRM = "Видалити <b>{name}</b>?\n\nКлієнт буде прихований, всі дані збережуться."
CLIENT_DELETED = "🗑 Клієнта <b>{name}</b> видалено."

# Quick text mark
QUICK_MARK_NO_MATCH = (
    "Не зрозумів жодного імені. Відправ список імен або вибери дію з меню.\n\n"
    "<i>Наприклад: Марина, Сергій, Ірина не була</i>"
)
QUICK_MARK_AMBIGUOUS = (
    "Знайшов кількох клієнтів за «<b>{token}</b>». Кого відмітити?"
)
QUICK_MARK_SUMMARY_HEADER = "📋 <b>Підсумок:</b>\n\n"
QUICK_MARK_UNRECOGNIZED_HEADER = "\n❓ <b>Не розпізнано:</b>\n"
