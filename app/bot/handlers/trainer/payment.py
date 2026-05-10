from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import client_picker_kb, date_choice_kb
from app.bot.keyboards.trainer_menu import BTN_REGISTER_PAYMENT, trainer_main_kb
from app.bot.states.trainer import RegisterPaymentStates
from app.db.repositories.clients import get_by_id
from app.services.clients import get_active_clients
from app.services.packages import register_payment
from app.utils.formatting import fmt_date

router = Router()


def _parse_date(text: str) -> datetime | None:
    today = datetime.now(UTC).date()
    try:
        d = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        return datetime(d.year, d.month, d.day, tzinfo=UTC)
    except ValueError:
        pass
    try:
        parsed = datetime.strptime(text.strip(), "%d.%m")
        from datetime import date as date_cls
        d = date_cls(today.year, parsed.month, parsed.day)
        if d > today:
            d = date_cls(today.year - 1, parsed.month, parsed.day)
        return datetime(d.year, d.month, d.day, tzinfo=UTC)
    except ValueError:
        pass
    return None


@router.message(F.text == BTN_REGISTER_PAYMENT)
async def start_payment(message: Message, state: FSMContext, session: AsyncSession) -> None:
    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.NO_ACTIVE_CLIENTS)
        return
    await state.set_state(RegisterPaymentStates.select_client)
    await message.answer(texts.ASK_PAYMENT_CLIENT, reply_markup=client_picker_kb(clients, "pay_client"))


@router.callback_query(RegisterPaymentStates.select_client, F.data.startswith("pay_client:"))
async def client_selected(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[1])
    await state.update_data(client_id=client_id)
    await state.set_state(RegisterPaymentStates.enter_amount)
    await callback.answer()
    try:
        await callback.message.edit_text(texts.ASK_PAYMENT_AMOUNT)
    except TelegramBadRequest:
        pass


@router.message(RegisterPaymentStates.enter_amount)
async def got_amount(message: Message, state: FSMContext) -> None:
    try:
        price = Decimal(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer(texts.INVALID_AMOUNT)
        return

    await state.update_data(price=str(price))
    await state.set_state(RegisterPaymentStates.choose_date)
    await message.answer(texts.ASK_PAYMENT_DATE, reply_markup=date_choice_kb())


@router.callback_query(RegisterPaymentStates.choose_date, F.data == "date_today")
async def date_today(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.clear()
    await _finish_payment(callback.message, session, data, purchased_at=None, edit=True)


@router.callback_query(RegisterPaymentStates.choose_date, F.data == "date_other")
async def date_other(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RegisterPaymentStates.enter_date)
    await callback.answer()
    try:
        await callback.message.edit_text(texts.ASK_PAYMENT_DATE_MANUAL)
    except TelegramBadRequest:
        pass


@router.message(RegisterPaymentStates.enter_date)
async def got_date(message: Message, state: FSMContext, session: AsyncSession) -> None:
    purchased_at = _parse_date(message.text)
    if purchased_at is None:
        await message.answer(texts.INVALID_DATE)
        return
    data = await state.get_data()
    await state.clear()
    await _finish_payment(message, session, data, purchased_at=purchased_at, edit=False)


async def _finish_payment(
    message: Message,
    session: AsyncSession,
    data: dict,
    purchased_at: datetime | None,
    edit: bool,
) -> None:
    client = await get_by_id(session, data["client_id"])
    price = Decimal(data["price"])
    package = await register_payment(session, client_id=client.id, price=price, purchased_at=purchased_at)
    text = texts.PAYMENT_REGISTERED.format(
        name=client.full_name,
        price=int(price),
        expires=fmt_date(package.expires_at),
    )
    if edit:
        try:
            await message.edit_text(text)
        except TelegramBadRequest:
            await message.answer(text)
        await message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)
    else:
        await message.answer(text, reply_markup=trainer_main_kb)
