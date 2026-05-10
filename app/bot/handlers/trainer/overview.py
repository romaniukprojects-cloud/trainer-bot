from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.trainer_menu import BTN_OVERVIEW
from app.db.repositories.packages import get_active_for_client, get_consumed_count
from app.services.clients import get_active_clients
from app.utils.formatting import days_until, fmt_date

router = Router()


@router.message(F.text == BTN_OVERVIEW)
async def show_overview(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.OVERVIEW_EMPTY)
        return

    lines = [texts.OVERVIEW_HEADER]
    for client in clients:
        packages = await get_active_for_client(session, client.id)
        if packages:
            pkg = packages[0]
            used = await get_consumed_count(session, pkg.id)
            lines.append(
                texts.OVERVIEW_CLIENT_ACTIVE.format(
                    name=client.full_name,
                    used=used,
                    total=pkg.total_sessions,
                    expires=fmt_date(pkg.expires_at),
                    days=days_until(pkg.expires_at),
                )
            )
        else:
            lines.append(texts.OVERVIEW_CLIENT_NO_PACKAGE.format(name=client.full_name))

    await message.answer("".join(lines))
