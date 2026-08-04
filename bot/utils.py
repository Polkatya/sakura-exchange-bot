from __future__ import annotations

import logging
from collections.abc import Sequence

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup, InputMediaVideo

from . import db, texts
from .config import config

log = logging.getLogger(__name__)

FORBIDDEN_WORDS = [
    "цп", "дп", "cp", "dp", "child porn", "childporn",
    "школьниц", "школьник", "schoolgirl", "school boy",
    "несовершеннолет", "minor", "underage", "under age",
    "ребёнок", "ребенок", "ребят", "детей", "детское", "детская",
    "lolicon", "loli", "lolita",
    "shotacon", "shota",
    "инцест", "incest",
    "насилие", "rape", "raped",
    "животн", "beastiality", "bestiality", "zoophilia",
    "шантаж", "blackmail",
    "слив", "слив", "dox", "doxx", "doxxing",
]


def find_forbidden_words(text: str) -> list[str]:
    """Ищет запретные слова в тексте. Возвращает список найденных (в нижнем регистре)."""
    if not text:
        return []
    normalized = text.lower()
    found: set[str] = set()
    for word in FORBIDDEN_WORDS:
        if word in normalized:
            found.add(word)
    return sorted(found)


def contains_forbidden(text: str) -> tuple[bool, list[str]]:
    """Проверяет текст на запретные слова. Возвращает (есть_ли, список_найденных)."""
    bad = find_forbidden_words(text)
    return (len(bad) > 0, bad)


async def send_videos(bot: Bot, chat_id: int, file_ids: Sequence[str], caption: str | None = None) -> None:
    """Отправляет видео альбомами по 10 штук."""
    if not file_ids:
        return
    for start in range(0, len(file_ids), 10):
        chunk = file_ids[start : start + 10]
        media = [InputMediaVideo(media=file_id) for file_id in chunk]
        if caption and start == 0:
            media[0] = InputMediaVideo(media=chunk[0], caption=caption)
        try:
            await bot.send_media_group(chat_id, media=media)
        except TelegramAPIError as error:
            log.warning("Не удалось отправить альбом в %s: %s", chat_id, error)
            for file_id in chunk:
                try:
                    await bot.send_video(chat_id, file_id)
                except TelegramAPIError as inner:
                    log.warning("Не удалось отправить видео в %s: %s", chat_id, inner)


async def notify_admins(
    bot: Bot,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    videos: Sequence[str] = (),
) -> None:
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=keyboard)
            await send_videos(bot, admin_id, videos)
        except TelegramAPIError as error:
            log.warning("Не доставлено админу %s: %s", admin_id, error)


async def safe_send(bot: Bot, chat_id: int, text: str, keyboard: InlineKeyboardMarkup | None = None) -> bool:
    try:
        await bot.send_message(chat_id, text, reply_markup=keyboard)
        return True
    except TelegramAPIError as error:
        log.info("Сообщение для %s не доставлено: %s", chat_id, error)
        return False


def is_premium(user: dict) -> bool:
    from . import db
    return db.is_premium_active(user)


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


async def referral_link(bot: Bot, user_id: int) -> str:
    me = await bot.me()
    return f"https://t.me/{me.username}?start=ref_{user_id}"


async def profile_stats(user_id: int) -> tuple[float, int]:
    return await db.rating_of(user_id)


def videos_left_text(count: int) -> str:
    return texts.progress_bar(count, config.videos_per_trade)
