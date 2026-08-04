"""Точка входа SakuraExchangeBot."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot import db
from bot.config import config
from bot.handlers import setup_routers
from bot.middlewares import UserMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("sakura")

COMMANDS = [
    BotCommand(command="start", description="🌸 Запустить бота"),
    BotCommand(command="menu", description="🏠 Главное меню"),
    BotCommand(command="rules", description="📜 Правила"),
    BotCommand(command="help", description="❓ Как это работает"),
    BotCommand(command="cancel", description="❌ Отменить действие"),
]


async def main() -> None:
    if not config.bot_token:
        log.error("BOT_TOKEN не задан. Скопируйте .env.example в .env и вставьте токен от @BotFather.")
        sys.exit(1)
    if not config.admin_ids:
        log.warning("ADMIN_IDS пуст — жалобы будет некому получать.")

    await db.init()

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.message.middleware(UserMiddleware())
    dispatcher.callback_query.middleware(UserMiddleware())
    dispatcher.include_router(setup_routers())

    await bot.set_my_commands(COMMANDS)
    me = await bot.me()
    log.info("Бот запущен: @%s", me.username)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Бот остановлен")
