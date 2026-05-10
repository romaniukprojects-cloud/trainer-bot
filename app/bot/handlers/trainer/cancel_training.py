from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import cancel_training_confirm_kb, sbd_date_choice_kb
from app.bot.keyboards.trainer_menu import BTN_CANCEL_TRAINING, trainer_main_kb
from app.bot.states.trainer import CancelTrainingStates
from app.config import settings
from app.services.sessions import cancel_training_day
from app.utils.tz import now_kyiv

router = Router()


def _parse_date(text: str) -> datetime | None:
    tz = ZoneInfo(settings.timezone)
    today = now_kyiv().date()
    for fmt in ("%d.%m.%Y", "%d.%m"):
        try:
            parsed = datetime.strptime(text.strip(), fmt)
            d = today.replace(month=parsed.month, day=parsed.day)
            if fmt == "%d.%m" and d > today:
                d = d.replace(year=d.year - 1)
            elif fmt == "%d.%m.%Y":
                d = parsed.date()
            return datetime(d.year, d.month, d.day, tzinfo=tz)
        except ValueError:
            continue
    return None


def _day_window(date_local: datetime) -> tuple[datetime, datetime]:
    tz = ZoneInfo(settings.timezone)
    day_start = datetime(date_local.year, date_local.month, date_local.day, tzinfo=tz).astimezone(UTC)
    return day_start, day_start + timedelta(days=1)


@router.message(F.text == BTN_CANCEL_TRAINING)
async def start_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CancelTrainingStates.choosing_date)
    await message.answer(texts.CT_CHOOSE_DATE, reply_markup=sbd_date_choice_kb())


@router.callback_query(CancelTrainingStates.choosing_date, F.data == "sbd_today")
async def pick_today(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    await _show_preview(callback.message, state, session, now_kyiv(), edit=True)


@router.callback_query(CancelTrainingStates.choosing_date, F.data == "sbd_other")
async def pick_other(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(CancelTrainingStates.enter_date)
    try:
        await callback.message.edit_text(texts.CT_ASK_DATE)
    except TelegramBadRequest:
        pass


@router.message(CancelTrainingStates.enter_date)
async def got_date(message: Message, state: FSMContext, session: AsyncSession) -> None:
    date_local = _parse_date(message.text or "")
    if date_local is None:
        await message.answer(texts.INVALID_DATE)
        return
    await _show_preview(message, state, session, date_local, edit=False)


async def _show_preview(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    date_local: datetime,
    edit: bool,
) -> None:
    from app.db.repositories.sessions import get_countable_for_date

    day_start, day_end = _day_window(date_local)
    rows = await get_countable_for_date(session, day_start, day_end)
    date_str = date_local.strftime("%d.%m.%Y")

    if not rows:
        text = texts.CT_NOTHING.format(date=date_str)
        if edit:
            try:
                await target.edit_text(text)
            except TelegramBadRequest:
                pass
        else:
            await target.answer(text, reply_markup=trainer_main_kb)
        await state.clear()
        return

    _STATUS_LABELS = {
        "attended": "✅ прийшов",
        "missed_no_notice": "🚫 пропуск",
    }

    text = texts.CT_CONFIRM_HEADER.format(date=date_str)
    for record, client_name in rows:
        label = _STATUS_LABELS.get(record.status.value, record.status.value)
        text += texts.CT_CONFIRM_LINE.format(name=client_name, status=label)

    await state.set_state(CancelTrainingStates.confirming)
    await state.update_data(day_start=day_start.isoformat(), day_end=day_end.isoformat(), date_str=date_str)

    if edit:
        try:
            await target.edit_text(text, reply_markup=cancel_training_confirm_kb())
        except TelegramBadRequest:
            pass
    else:
        await target.answer(text, reply_markup=cancel_training_confirm_kb())


@router.callback_query(CancelTrainingStates.confirming, F.data == "ct_confirm")
async def do_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    data = await state.get_data()
    day_start = datetime.fromisoformat(data["day_start"])
    day_end = datetime.fromisoformat(data["day_end"])
    date_str = data["date_str"]
    await state.clear()

    summary = await cancel_training_day(session, day_start, day_end)

    text = texts.CT_DONE_HEADER.format(date=date_str)
    for client_name, _ in summary:
        text += texts.CT_DONE_LINE.format(name=client_name)

    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)


@router.callback_query(CancelTrainingStates.confirming, F.data == "ct_cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(texts.CANCEL_ACTION)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери дію:", reply_markup=trainer_main_kb)
