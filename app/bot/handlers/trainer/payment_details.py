from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.trainer_menu import trainer_main_kb, BTN_PAYMENT_DETAILS
from app.bot.states.trainer import PaymentDetailsStates
from app.config import settings
from app.db.repositories.trainers import get_by_telegram_id, update_payment_details

router = Router()


def _details_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Змінити", callback_data="pd_edit")
    return builder.as_markup()


@router.message(F.text == BTN_PAYMENT_DETAILS)
async def show_details(message: Message, session: AsyncSession) -> None:
    trainer = await get_by_telegram_id(session, settings.trainer_telegram_id)
    if trainer and trainer.payment_details:
        await message.answer(
            texts.PAYMENT_DETAILS_SHOW.format(details=trainer.payment_details),
            reply_markup=_details_kb(),
        )
    else:
        await message.answer(texts.PAYMENT_DETAILS_EMPTY, reply_markup=_details_kb())


@router.callback_query(F.data == "pd_edit")
async def start_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PaymentDetailsStates.entering)
    await callback.message.edit_text(texts.PAYMENT_DETAILS_ASK)
    await callback.answer()


@router.message(PaymentDetailsStates.entering)
async def save_details(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer(texts.PAYMENT_DETAILS_ASK)
        return
    await update_payment_details(session, settings.trainer_telegram_id, text)
    await session.commit()
    await state.clear()
    await message.answer(texts.PAYMENT_DETAILS_SAVED, reply_markup=trainer_main_kb)
