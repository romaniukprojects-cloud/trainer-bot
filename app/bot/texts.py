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
ASK_PAYMENT_AMOUNT = "Введіть суму оплати за 10 занять (грн):\n<i>Наприклад: 5000</i>"
ASK_PAYMENT_DATE = "Дата оплати:"
ASK_PAYMENT_DATE_MANUAL = (
    "Введіть дату у форматі <code>ДД.ММ</code> або <code>ДД.ММ.РРРР</code>:\n"
    "<i>Наприклад: 25.04 або 25.04.2025</i>"
)
INVALID_DATE = "❌ Невірна дата. Введіть у форматі ДД.ММ або ДД.ММ.РРРР"
PAYMENT_REGISTERED = (
    "✅ Оплату зареєстровано!\n\n"
    "<b>{name}</b>: {price} грн (за 10 занять)\n"
    "Пакет до: <b>{expires}</b>"
)
INVALID_AMOUNT = "❌ Невірна сума. Введіть число, наприклад: <code>1500</code>"
NO_ACTIVE_CLIENTS = "Клієнтів поки немає. Спочатку додайте клієнта через «➕ Додати клієнта»."

# Mark session (multi-select)
MULTI_MARK_PROMPT = (
    "Натискай на клієнтів щоб відмітити:\n\n"
    "☐ — не відмічено (пропустити)\n"
    "✅ — прийшов\n"
    "🚫 — не прийшов (без попередження)\n"
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

# Payment details
PAYMENT_DETAILS_SHOW = "💳 <b>Реквізити для оплати:</b>\n\n{details}"
PAYMENT_DETAILS_EMPTY = "💳 Реквізити ще не встановлено."
PAYMENT_DETAILS_ASK = (
    "Введіть реквізити для оплати:\n\n"
    "<i>Наприклад: Monobank: 5375 4141 1234 5678\nПриватБанк: 4149 6090 1234 5678</i>"
)
PAYMENT_DETAILS_SAVED = "✅ Реквізити збережено."

# Sessions by date
SBD_CHOOSE_DATE = "Оберіть дату:"
SBD_ASK_DATE = "Введіть дату у форматі <code>ДД.ММ</code> або <code>ДД.ММ.РРРР</code>:"
SBD_HEADER = "📅 <b>Заняття за {date}:</b>\n\n"
SBD_EMPTY = "📅 За <b>{date}</b> занять не відмічено."
SBD_TOTAL = "\nВсього: <b>{count}</b>"

# Schedule management
SCHEDULE_SELECT_CLIENT = "Оберіть клієнта для перегляду розкладу:"
SCHEDULE_HEADER = "📆 <b>Розклад: {name}</b>\n\n"
SCHEDULE_NO_SLOTS = "<i>Розкладу ще немає.</i>"
SCHEDULE_SLOT_LINE = "• {weekday} {time}\n"
SCHEDULE_ADD_WEEKDAY = "Оберіть день тижня:"
SCHEDULE_ADD_TIME = "Введіть час у форматі <code>ГГ:ХХ</code>:\n<i>Наприклад: 10:00</i>"
SCHEDULE_SLOT_ADDED = "✅ Слот додано: <b>{weekday} {time}</b>"
SCHEDULE_SLOT_REMOVED = "🗑 Слот видалено."
SCHEDULE_INVALID_TIME = "❌ Невірний формат. Введіть час як <code>10:00</code>"
SCHEDULE_SELECT_FOR_REMOVE = "Оберіть слот для видалення:"

# Session date picker
SESSION_ASK_DATE = "📅 На яку дату відмітити заняття?"

# Cancel training
CT_CHOOSE_DATE = "Оберіть дату тренування, яке потрібно скасувати:"
CT_ASK_DATE = "Введіть дату у форматі <code>ДД.ММ</code> або <code>ДД.ММ.РРРР</code>:"
CT_NOTHING = "📅 За <b>{date}</b> відмічених занять немає — нічого скасовувати."
CT_CONFIRM_HEADER = "🚫 Скасувати тренування за <b>{date}</b>?\n\nБудуть скасовані:\n"
CT_CONFIRM_LINE = "• {name} ({status})\n"
CT_DONE_HEADER = "✅ Скасовано тренування за <b>{date}</b>:\n\n"
CT_DONE_LINE = "• {name}\n"

# Auto session confirmation (sent by scheduler reminder job)
SCHED_CONFIRM_PROMPT = (
    "⏰ <b>Заняття через ~1 год: {name}</b>\n"
    "{weekday}, {time}\n\n"
    "Оберіть статус:"
)
SCHED_CONFIRM_ALREADY = "Статус вже виставлено."
