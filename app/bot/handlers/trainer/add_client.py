from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.trainer_menu import BTN_ADD_CLIENT, BTN_INVITE_LINK, trainer_main_kb
from app.bot.states.trainer import AddClientStates
from app.services.clients import add_client, create_link_code, get_active_clients

router = Router()


@router.message(F.text == BTN_INVITE_LINK)
async def invite_link_choose(message: Message, session: AsyncSession) -> None:
    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.INVITE_LINK_NO_CLIENTS, reply_markup=trainer_main_kb)
        return
    buttons = [[InlineKeyboardButton(text=c.full_name, callback_data=f"invite:{c.id}")] for c in clients]
    await message.answer(texts.INVITE_LINK_CHOOSE, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("invite:"))
async def invite_link_generate(callback: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(callback.data.split(":")[1])
    from app.db.repositories.clients import get_by_id
    client = await get_by_id(session, client_id)
    if client is None:
        await callback.answer("Клієнта не знайдено.", show_alert=True)
        return
    code = await create_link_code(session, client)
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"
    await callback.answer()
    try:
        await callback.message.edit_text(texts.INVITE_LINK_READY.format(name=client.full_name, link=link))
    except TelegramBadRequest:
        pass


@router.message(F.text == BTN_ADD_CLIENT)
async def start_add_client(message: Message, state: FSMContext) -> None:
    await state.set_state(AddClientStates.name)
    await message.answer(texts.ASK_CLIENT_NAME)


@router.message(AddClientStates.name)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AddClientStates.username)
    await message.answer(texts.ASK_CLIENT_USERNAME)


@router.message(AddClientStates.username)
async def got_username(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    username = None if raw == "/skip" else raw.lstrip("@")
    await state.update_data(username=username)
    await state.set_state(AddClientStates.aliases)
    await message.answer(texts.ASK_CLIENT_ALIASES)


@router.message(AddClientStates.aliases)
async def got_aliases(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = message.text.strip()
    aliases = [] if text == "/skip" else [a.strip() for a in text.split(",") if a.strip()]
    data = await state.get_data()
    await state.clear()

    client = await add_client(
        session,
        full_name=data["name"],
        telegram_username=data.get("username"),
        aliases=aliases,
    )
    code = await create_link_code(session, client)

    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"
    await message.answer(
        texts.CLIENT_ADDED.format(name=client.full_name, link=link),
        reply_markup=trainer_main_kb,
    )
