from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.trainer_menu import BTN_INCOME, trainer_main_kb
from app.bot.states.trainer import IncomeStates
from app.config import settings
from app.db.repositories.packages import get_income_for_period
from app.utils.tz import now_kyiv, to_utc

router = Router()


def _period_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Цей місяць", callback_data="income:current"),
            InlineKeyboardButton(text="📅 Попередній", callback_data="income:prev"),
        ],
        [InlineKeyboardButton(text="✏️ Інший місяць", callback_data="income:custom")],
    ])


def _format_period(dt: datetime) -> str:
    return dt.strftime("%m.%Y")


def _format_total(total: Decimal) -> str:
    return f"{int(total):,}".replace(",", " ")


async def _show_income(
    target: Message | CallbackQuery,
    session: AsyncSession,
    period_start: datetime,
    period_end: datetime,
    period_label: str,
) -> None:
    start_utc = to_utc(period_start)
    end_utc = to_utc(period_end)
    total, count = await get_income_for_period(session, start_utc, end_utc)

    if count == 0:
        result = texts.INCOME_EMPTY.format(period=period_label)
    else:
        result = texts.INCOME_RESULT.format(
            period=period_label,
            count=count,
            total=_format_total(total),
        )

    msg = target if isinstance(target, Message) else target.message
    try:
        await msg.edit_text(result)
    except (TelegramBadRequest, AttributeError):
        await msg.answer(result)
    if isinstance(target, Message):
        pass
    else:
        await target.answer()
    await msg.answer("Вибери дію:", reply_markup=trainer_main_kb)


@router.message(F.text == BTN_INCOME)
async def start_income(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.INCOME_CHOOSE_PERIOD, reply_markup=_period_kb())


@router.callback_query(F.data == "income:current")
async def income_current(callback: CallbackQuery, session: AsyncSession) -> None:
    now = now_kyiv()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start + relativedelta(months=1)
    await _show_income(callback, session, start, end, _format_period(start))


@router.callback_query(F.data == "income:prev")
async def income_prev(callback: CallbackQuery, session: AsyncSession) -> None:
    now = now_kyiv()
    end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = end - relativedelta(months=1)
    await _show_income(callback, session, start, end, _format_period(start))


@router.callback_query(F.data == "income:custom")
async def income_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(IncomeStates.enter_month)
    await callback.answer()
    try:
        await callback.message.edit_text(texts.INCOME_ASK_MONTH)
    except TelegramBadRequest:
        pass


@router.message(IncomeStates.enter_month)
async def income_enter_month(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = (message.text or "").strip()
    try:
        dt = datetime.strptime(text, "%m.%Y")
        kyiv = ZoneInfo(settings.timezone)
        start = dt.replace(tzinfo=kyiv)
        end = start + relativedelta(months=1)
    except ValueError:
        await message.answer(texts.INCOME_INVALID_MONTH)
        return

    await state.clear()
    await _show_income(message, session, start, end, _format_period(start))
