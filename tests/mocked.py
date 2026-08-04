"""Мини-мок Telegram API: гоняем хендлеры без реальной сети."""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncGenerator
from typing import Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import TelegramMethod
from aiogram.types import (
    CallbackQuery,
    Chat,
    Message,
    Update,
    User,
    Video,
)

NOW = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)


class MockedSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []
        self._message_id = 1000

    async def close(self) -> None:  # pragma: no cover - ничего не открывали
        pass

    async def stream_content(
        self, *args: Any, **kwargs: Any
    ) -> AsyncGenerator[bytes, None]:  # pragma: no cover
        yield b""

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None) -> Any:
        self.requests.append(method)
        name = type(method).__name__
        if name == "GetMe":
            return User(id=bot.id, is_bot=True, first_name="Sakura", username="SakuraExchangeBot")
        if name == "SendMediaGroup":
            return [self._message(getattr(method, "chat_id", 1)) for _ in getattr(method, "media", [1])]
        if name.startswith("Send") or name.startswith("Copy") or name.startswith("Forward"):
            return self._message(getattr(method, "chat_id", 1), getattr(method, "text", None))
        if name.startswith("Edit"):
            return True
        return True

    def _message(self, chat_id: int, text: str | None = None) -> Message:
        self._message_id += 1
        return Message(
            message_id=self._message_id,
            date=NOW,
            chat=Chat(id=chat_id, type="private"),
            text=text,
        )

    # ------------------------------------------------------------- helpers

    def sent_texts(self, chat_id: int | None = None) -> list[str]:
        result = []
        for request in self.requests:
            if type(request).__name__ != "SendMessage":
                continue
            if chat_id is not None and request.chat_id != chat_id:
                continue
            result.append(request.text)
        return result

    def last_text(self, chat_id: int | None = None) -> str:
        texts = self.sent_texts(chat_id)
        return texts[-1] if texts else ""

    def clear(self) -> None:
        self.requests.clear()


def make_bot() -> tuple[Bot, MockedSession]:
    session = MockedSession()
    bot = Bot(
        "42:TEST",
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    return bot, session


def tg_user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name=f"User{user_id}", username=f"user{user_id}")


_update_id = 0


def _next_update_id() -> int:
    global _update_id
    _update_id += 1
    return _update_id


def text_update(user_id: int, text: str) -> Update:
    return Update(
        update_id=_next_update_id(),
        message=Message(
            message_id=_next_update_id(),
            date=NOW,
            chat=Chat(id=user_id, type="private"),
            from_user=tg_user(user_id),
            text=text,
        ),
    )


def video_update(user_id: int, file_id: str) -> Update:
    return Update(
        update_id=_next_update_id(),
        message=Message(
            message_id=_next_update_id(),
            date=NOW,
            chat=Chat(id=user_id, type="private"),
            from_user=tg_user(user_id),
            video=Video(
                file_id=file_id,
                file_unique_id=file_id,
                width=640,
                height=480,
                duration=10,
            ),
        ),
    )


def callback_update(user_id: int, data: str) -> Update:
    return Update(
        update_id=_next_update_id(),
        callback_query=CallbackQuery(
            id=str(_next_update_id()),
            from_user=tg_user(user_id),
            chat_instance="test",
            data=data,
            message=Message(
                message_id=_next_update_id(),
                date=NOW,
                chat=Chat(id=user_id, type="private"),
                from_user=tg_user(0),
                text="карточка",
            ),
        ),
    )
