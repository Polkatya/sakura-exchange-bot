"""Сквозной прогон сценариев бота на моках Telegram API."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("BOT_TOKEN", "42:TEST")
os.environ.setdefault("ADMIN_IDS", "999")
os.environ.setdefault("REPEAT_TRADE_COOLDOWN_HOURS", "24")

from aiogram import Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

from bot import db  # noqa: E402
from bot.config import config  # noqa: E402
from bot.handlers import setup_routers  # noqa: E402
from bot.middlewares import UserMiddleware  # noqa: E402
from tests.mocked import (  # noqa: E402
    callback_update,
    make_bot,
    text_update,
    video_update,
)

ALICE = 111
BOB = 222
ADMIN = 999
N = config.videos_per_trade


def check(condition: bool, label: str) -> None:
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise AssertionError(label)


async def register(dp, bot, user_id: int, payload: str = "") -> None:
    await dp.feed_update(bot, text_update(user_id, f"/start {payload}".strip()))
    await dp.feed_update(bot, callback_update(user_id, "agree"))


async def create_trade(dp, bot, user_id: int, offer: str, want: str, prefix: str) -> None:
    await dp.feed_update(bot, text_update(user_id, "➕ Создать трейд"))
    await dp.feed_update(bot, text_update(user_id, offer))
    for i in range(N):
        await dp.feed_update(bot, video_update(user_id, f"{prefix}_{i}"))
    await dp.feed_update(bot, text_update(user_id, want))


async def main() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    config_db_path = tmp.name
    object.__setattr__(config, "db_path", config_db_path)

    await db.init()
    bot, session = make_bot()
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    dp.include_router(setup_routers())

    # --- правила и согласие
    await dp.feed_update(bot, text_update(ALICE, "/start"))
    check("правила" in session.last_text(ALICE).lower(), "/start показывает правила")
    await dp.feed_update(bot, text_update(ALICE, "привет"))
    check("правила" in session.last_text(ALICE).lower(), "без согласия дальше не пускает")
    await dp.feed_update(bot, callback_update(ALICE, "agree"))
    alice = await db.get_user(ALICE)
    check(bool(alice["agreed"]), "согласие сохранено")

    # --- реферал: Боб приходит по ссылке Алисы
    await register(dp, bot, BOB, f"ref_{ALICE}")
    alice = await db.get_user(ALICE)
    check(alice["referrals"] == 1, "реферал засчитан")
    check(alice["boost_until"] > db.now(), "буст за реферала выдан")

    # --- Алиса создаёт трейд
    await create_trade(dp, bot, ALICE, "хентай, милфы", "азиатки, 2D", "alice")
    trade_a = await db.get_trade_by_user(ALICE)
    check(trade_a is not None, "анкета Алисы создана")
    check(len(await db.get_trade_videos(trade_a["id"])) == N, f"в анкете {N} видео")

    # --- Боб без анкеты не может смотреть ленту
    session.clear()
    await dp.feed_update(bot, text_update(BOB, "🔍 Искать трейды"))
    check("создайте трейд" in session.last_text(BOB).lower(), "без анкеты лента закрыта")

    # --- Боб создаёт анкету и открывает ленту
    await create_trade(dp, bot, BOB, "азиатки, 2D", "хентай", "bob")
    session.clear()
    await dp.feed_update(bot, text_update(BOB, "🔍 Искать трейды"))
    check(f"Трейд #{trade_a['id']}" in session.last_text(BOB), "в ленте видна анкета Алисы")
    check(
        not any(type(r).__name__ == "SendMediaGroup" for r in session.requests),
        "в ленте видео не показываются",
    )

    # --- стрелка назад — премиум
    session.clear()
    await dp.feed_update(bot, callback_update(BOB, "feed:prev"))
    check("премиум" in session.last_text(BOB).lower(), "⬅️ требует премиум")

    # --- обмен
    session.clear()
    await dp.feed_update(bot, callback_update(BOB, f"trade:start:{trade_a['id']}"))
    check("Начинаем обмен" in session.last_text(BOB), "старт обмена")
    for i in range(N):
        await dp.feed_update(bot, video_update(BOB, f"bob_swap_{i}"))
    exchange = await db.get_exchange(1)
    check(exchange is not None, "обмен записан в БД")
    check(len(await db.get_exchange_videos(1, BOB)) == N, "видео Боба сохранены")
    check(len(await db.get_exchange_videos(1, ALICE)) == N, "видео Алисы сохранены")
    check("Обмен завершён" in session.last_text(BOB), "Боб получил подтверждение")
    check(
        any("С вами обменялись" in t for t in session.sent_texts(ALICE)),
        "Алиса уведомлена об обмене",
    )
    bob = await db.get_user(BOB)
    check(bob["trades_done"] == 1, "счётчик обменов вырос")
    check(
        not any("@user" in (t or "") for t in session.sent_texts()),
        "@ники собеседников не показываются",
    )
    check(
        any("Аноним #" in (t or "") for t in session.sent_texts(BOB)),
        "вместо ника показывается псевдоним",
    )

    # --- повтор с той же анкетой блокируется
    session.clear()
    await dp.feed_update(bot, callback_update(BOB, f"trade:start:{trade_a['id']}"))
    check("Начинаем обмен" not in session.last_text(BOB), "повторный обмен на кулдауне")

    # --- оценка и комментарий
    await dp.feed_update(bot, callback_update(BOB, "rate:1:5"))
    avg, count = await db.rating_of(ALICE)
    check(count == 1 and avg == 5.0, "оценка сохранена")
    session.clear()
    await dp.feed_update(bot, callback_update(BOB, "comment:1"))
    await dp.feed_update(bot, text_update(BOB, "топ контент, спасибо"))
    check(
        any("Комментарий после обмена" in t for t in session.sent_texts(ALICE)),
        "комментарий доставлен",
    )

    # --- жалоба после трейда уходит админу
    session.clear()
    await dp.feed_update(bot, callback_update(BOB, "report:exchange:1"))
    await dp.feed_update(bot, callback_update(BOB, "reason:1:theme"))
    admin_texts = session.sent_texts(ADMIN)
    check(any("ЖАЛОБА ПОСЛЕ ТРЕЙДА" in t for t in admin_texts), "жалоба ушла админу")

    # --- жалоба на анкету
    session.clear()
    await dp.feed_update(bot, callback_update(BOB, f"report:profile:{trade_a['id']}"))
    check(
        any("ЖАЛОБА НА АНКЕТУ" in t for t in session.sent_texts(ADMIN)),
        "жалоба на анкету ушла админу",
    )

    # --- админ банит
    report = await db.get_report(2)
    session.clear()
    await dp.feed_update(bot, callback_update(ADMIN, f"adm:ban:{report['id']}:{ALICE}"))
    alice = await db.get_user(ALICE)
    check(bool(alice["banned"]), "админ забанил нарушителя")
    trade_a = await db.get_trade_by_user(ALICE)
    check(not trade_a["active"], "анкета забаненного скрыта")
    session.clear()
    await dp.feed_update(bot, text_update(ALICE, "/start"))
    check("заблокированы" in session.last_text(ALICE).lower(), "забаненный получает отказ")

    # --- обычный юзер не имеет доступа к админке
    session.clear()
    await dp.feed_update(bot, text_update(BOB, "/stats"))
    check("Статистика" not in session.last_text(BOB), "админка закрыта для юзеров")

    # --- премиум-экран
    session.clear()
    await dp.feed_update(bot, text_update(BOB, "👑 Премиум"))
    check("Премиум SakuraExchangeBot" in session.last_text(BOB), "премиум-экран открывается")

    await db.close()
    await bot.session.close()
    os.unlink(config_db_path)
    print("\n🌸 Все сценарии пройдены")


if __name__ == "__main__":
    asyncio.run(main())
