from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import client_picker_kb
from app.bot.keyboards.trainer_menu import BTN_DELETE_CLIENT, trainer_main_kb
from app.db.repositories.clients import get_by_id
from app.services.clients import deactivate_client, get_active_clients

router = Router()


def _confirm_kb(client_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Так, видалити", callback_data=f"del_confirm:{client_id}")
    builder.button(text="❌ Скасувати", callback_data="del_cancel")
    builder.adjust(2)
    return builder.as_markup()


@router.message(F.text == BTN_DELETE_CLIENT)
async def start_delete(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.NO_ACTIVE_CLIENTS)
        return
    await message.answer(texts.ASK_DELETE_CLIENT, reply_markup=client_picker_kb(clients, "del_pick"))


@router.callback_query(F.data.startswith("del_pick:"))
async def client_picked(callback: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(callback.data.split(":")[1])
    client = await get_by_id(session, client_id)
    if client is None:
        await callback.answer("Клієнта не знайдено.")
        return
    await callback.answer()
    try:
        await callback.message.edit_text(
            texts.DELETE_CONFIRM.format(name=client.full_name),
            reply_markup=_confirm_kb(client_id),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("del_confirm:"))
async def confirm_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(callback.data.split(":")[1])
    client = await get_by_id(session, client_id)
    if client is None:
        await callback.answer("Клієнта не знайдено.")
        return
    name = client.full_name
    await deactivate_client(session, client)
    await callback.answer()
    try:
        await callback.message.edit_text(texts.CLIENT_DELETED.format(name=name))
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)


@router.callback_query(F.data == "del_cancel")
async def cancel_delete(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await callback.message.edit_text(texts.CANCEL_ACTION)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)
