from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.client_menu import client_main_kb
from app.bot.keyboards.trainer_menu import trainer_main_kb
from app.config import settings
from app.db.models.client import Client
from app.db.repositories.clients import get_by_telegram_id
from app.db.repositories.trainers import get_or_create as get_or_create_trainer
from app.services.clients import link_telegram

router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    is_trainer: bool,
    client: Client | None,
) -> None:
    await state.clear()

    if is_trainer:
        full_name = message.from_user.full_name or "Тренер"
        await get_or_create_trainer(session, settings.trainer_telegram_id, full_name)
        # Clean up if trainer accidentally used a client invite link
        accidental = await get_by_telegram_id(session, message.from_user.id)
        if accidental:
            accidental.telegram_user_id = None
            await session.commit()
            await message.answer(
                texts.TRAINER_LINK_CLEANUP.format(name=accidental.full_name),
                reply_markup=trainer_main_kb,
            )
        else:
            await session.commit()
            await message.answer(texts.START_TRAINER, reply_markup=trainer_main_kb)
        return

    args = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else None
    if args:
        linked = await link_telegram(
            session, args, message.from_user.id, message.from_user.username
        )
        if linked:
            await message.answer(texts.START_CLIENT_LINKED, reply_markup=client_main_kb)
        elif client:
            await message.answer(texts.START_CLIENT, reply_markup=client_main_kb)
        else:
            await message.answer(texts.START_CODE_INVALID)
        return

    if client:
        await message.answer(texts.START_CLIENT, reply_markup=client_main_kb)
    else:
        await message.answer(texts.START_UNKNOWN)


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    is_trainer: bool,
    client: Client | None,
) -> None:
    await state.clear()
    if is_trainer:
        await message.answer(texts.CANCEL_ACTION, reply_markup=trainer_main_kb)
    elif client:
        await message.answer(texts.CANCEL_ACTION, reply_markup=client_main_kb)
    else:
        await message.answer(texts.CANCEL_ACTION)
