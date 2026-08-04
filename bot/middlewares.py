from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from . import db, keyboards, texts
from .config import config

BANNED_TEXT = (
    "⛔️ <b>Вы заблокированы</b>\n\nДоступ к боту закрыт за нарушение правил.\nАпелляции не принимаются."
)


class UserMiddleware(BaseMiddleware):
    """Подтягивает пользователя из БД, режет банов и не пускает дальше правил."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        user = await db.ensure_user(tg_user.id, tg_user.username, tg_user.full_name)
        data["user"] = user

        if user["user_id"] in config.admin_ids:
            return await handler(event, data)

        if user["banned"]:
            if isinstance(event, Message):
                await event.answer(BANNED_TEXT)
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔️ Вы заблокированы", show_alert=True)
            return None

        if not user["agreed"] and not _is_entry_point(event):
            if isinstance(event, Message):
                await event.answer(texts.RULES, reply_markup=keyboards.rules())
            elif isinstance(event, CallbackQuery):
                await event.answer("Сначала примите правила 👇", show_alert=True)
                await event.message.answer(texts.RULES, reply_markup=keyboards.rules())
            return None

        return await handler(event, data)


def _is_entry_point(event: TelegramObject) -> bool:
    if isinstance(event, Message):
        return bool(event.text and event.text.startswith("/start"))
    if isinstance(event, CallbackQuery):
        return event.data == "agree"
    return True
