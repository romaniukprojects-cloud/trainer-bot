from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import settings
from app.db.base import AsyncSessionLocal
from app.db.repositories.clients import get_by_telegram_id


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        data["is_trainer"] = False
        data["client"] = None
        if user:
            data["is_trainer"] = user.id == settings.trainer_telegram_id
            # Use existing session if available (DbSessionMiddleware ran first),
            # otherwise open a short-lived read-only session for the client lookup.
            session = data.get("session")
            if session is not None:
                data["client"] = await get_by_telegram_id(session, user.id)
            else:
                async with AsyncSessionLocal() as s:
                    data["client"] = await get_by_telegram_id(s, user.id)
        return await handler(event, data)
