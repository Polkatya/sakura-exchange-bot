"""Слой работы с SQLite. Видео хранятся как telegram file_id, сами файлы бот не качает."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

import aiosqlite

from .config import config

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT,
    full_name      TEXT,
    agreed         INTEGER NOT NULL DEFAULT 0,
    banned         INTEGER NOT NULL DEFAULT 0,
    ban_reason     TEXT,
    verified       INTEGER NOT NULL DEFAULT 0,
    referrer_id    INTEGER,
    referrals      INTEGER NOT NULL DEFAULT 0,
    premium        INTEGER NOT NULL DEFAULT 0,
    premium_until  INTEGER NOT NULL DEFAULT 0,
    boost_until    INTEGER NOT NULL DEFAULT 0,
    trades_done    INTEGER NOT NULL DEFAULT 0,
    created_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE,
    offer       TEXT NOT NULL,
    want        TEXT NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trade_videos (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    file_id  TEXT NOT NULL,
    position INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trade_videos ON trade_videos(trade_id);

CREATE TABLE IF NOT EXISTS exchanges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    initiator_id INTEGER NOT NULL,
    partner_id   INTEGER NOT NULL,
    trade_id     INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'completed',
    created_at   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_exchanges_pair ON exchanges(initiator_id, trade_id);

CREATE TABLE IF NOT EXISTS exchange_videos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_id INTEGER NOT NULL,
    owner_id    INTEGER NOT NULL,
    file_id     TEXT NOT NULL,
    position    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_exchange_videos ON exchange_videos(exchange_id);

CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL,
    target_id   INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    reason      TEXT,
    comment     TEXT,
    trade_id    INTEGER,
    exchange_id INTEGER,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ratings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_id INTEGER NOT NULL,
    from_id     INTEGER NOT NULL,
    to_id       INTEGER NOT NULL,
    emoji       TEXT NOT NULL,
    score       INTEGER NOT NULL,
    created_at  INTEGER NOT NULL,
    UNIQUE(exchange_id, from_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange_id INTEGER NOT NULL,
    from_id     INTEGER NOT NULL,
    to_id       INTEGER NOT NULL,
    text        TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);
"""


def now() -> int:
    return int(time.time())


async def init() -> aiosqlite.Connection:
    global _db
    _db = await aiosqlite.connect(config.db_path)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(SCHEMA)
    # Миграции для уже созданных таблиц (CREATE IF NOT EXISTS не добавит колонки)
    migrations = [
        ("users", "premium_until", "INTEGER NOT NULL DEFAULT 0"),
    ]
    for table, column, definition in migrations:
        try:
            await _db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except aiosqlite.OperationalError:
            # Колонка уже существует
            pass
    await _db.commit()
    return _db


async def close() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def conn() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("База не инициализирована, вызовите db.init()")
    return _db


async def _fetchone(query: str, params: Iterable[Any] = ()) -> dict | None:
    async with conn().execute(query, tuple(params)) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def _fetchall(query: str, params: Iterable[Any] = ()) -> list[dict]:
    async with conn().execute(query, tuple(params)) as cur:
        rows = await cur.fetchall()
    return [dict(row) for row in rows]


async def _execute(query: str, params: Iterable[Any] = ()) -> int:
    cur = await conn().execute(query, tuple(params))
    await conn().commit()
    return cur.lastrowid


# ---------------------------------------------------------------- users


async def get_user(user_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))


async def ensure_user(user_id: int, username: str | None, full_name: str | None) -> dict:
    user = await get_user(user_id)
    if user is None:
        await _execute(
            "INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, now()),
        )
        user = await get_user(user_id)
    elif user["username"] != username or user["full_name"] != full_name:
        await _execute(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (username, full_name, user_id),
        )
        user["username"] = username
        user["full_name"] = full_name
    assert user is not None
    return user


async def set_agreed(user_id: int) -> None:
    await _execute("UPDATE users SET agreed = 1 WHERE user_id = ?", (user_id,))


async def set_referrer(user_id: int, referrer_id: int) -> None:
    await _execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))


async def add_referral(referrer_id: int) -> dict:
    await _execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
    await add_boost(referrer_id, config.boost_hours_per_referral * 3600)
    user = await get_user(referrer_id)
    assert user is not None
    if user["referrals"] >= config.premium_referrals_required and not user["premium"]:
        await set_premium(referrer_id, True)
        user["premium"] = 1
    return user


async def add_boost(user_id: int, seconds: int) -> int:
    user = await get_user(user_id)
    if user is None:
        return 0
    base = max(user["boost_until"], now())
    until = base + seconds
    await _execute("UPDATE users SET boost_until = ? WHERE user_id = ?", (until, user_id))
    return until


async def set_premium(user_id: int, value: bool, hours: int = 0) -> None:
    """Устанавливает премиум.
    value=True и hours=0 -> навсегда (premium=1).
    value=True и hours>0 -> на срок (premium_until=now+hours, premium=1).
    value=False -> отключить (0 везде)."""
    if not value:
        await _execute("UPDATE users SET premium = 0, premium_until = 0 WHERE user_id = ?", (user_id,))
        return
    if hours > 0:
        until = now() + hours * 3600
        await _execute(
            "UPDATE users SET premium = 1, premium_until = ? WHERE user_id = ?", (until, user_id)
        )
    else:
        await _execute(
            "UPDATE users SET premium = 1, premium_until = 0 WHERE user_id = ?", (user_id,)
        )


def is_premium_active(user: dict) -> bool:
    """True, если у пользователя премиум навсегда, или временный и срок не истёк.
    Синхронная — не ходит в БД, только проверяет поля пользователя из словаря."""
    if not user:
        return False
    if user.get("premium"):
        until = int(user.get("premium_until") or 0)
        # навсегда: until=0 или пусто; временный: until>now()
        if until == 0 or until > now():
            return True
    return False


def trade_limit_of(user: dict) -> int:
    """Лимит обменов для пользователя.
    По умолчанию base_trade_limit + рефералы * бонус за реферала.
    Для активного премиума возвращаем очень большое число (безлимит)."""
    if is_premium_active(user):
        return 10_000_000
    base = config.base_trade_limit
    bonus = (int(user.get("referrals") or 0)) * config.trade_limit_bonus_per_referral
    return base + bonus


async def set_banned(user_id: int, value: bool, reason: str | None = None) -> None:
    await _execute(
        "UPDATE users SET banned = ?, ban_reason = ? WHERE user_id = ?",
        (1 if value else 0, reason, user_id),
    )
    if value:
        await _execute("UPDATE trades SET active = 0 WHERE user_id = ?", (user_id,))


async def set_verified(user_id: int, value: bool) -> None:
    await _execute("UPDATE users SET verified = ? WHERE user_id = ?", (1 if value else 0, user_id))


async def incr_trades_done(*user_ids: int) -> None:
    for user_id in user_ids:
        await _execute("UPDATE users SET trades_done = trades_done + 1 WHERE user_id = ?", (user_id,))


async def all_user_ids() -> list[int]:
    rows = await _fetchall("SELECT user_id FROM users WHERE banned = 0")
    return [row["user_id"] for row in rows]


# ---------------------------------------------------------------- trades


async def get_trade_by_user(user_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM trades WHERE user_id = ?", (user_id,))


async def get_trade(trade_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM trades WHERE id = ?", (trade_id,))


async def _trade_update_ts(trade_id: int) -> int:
    """Считает новый updated_at для трейда:
    - строго больше предыдущего updated_at
    - строго больше времени последнего обмена по этому трейду (если есть)
    - не меньше текущего now()
    """
    old = await get_trade(trade_id)
    base = now()
    if old:
        base = max(base, old["updated_at"] + 1)
    latest_ex = await _fetchone(
        "SELECT MAX(created_at) AS m FROM exchanges WHERE trade_id = ?", (trade_id,)
    )
    if latest_ex and latest_ex["m"] is not None:
        base = max(base, latest_ex["m"] + 1)
    return base


async def save_trade(user_id: int, offer: str, want: str, videos: list[str]) -> int:
    existing = await get_trade_by_user(user_id)
    ts = now()
    if existing:
        trade_id = existing["id"]
        new_updated = await _trade_update_ts(trade_id)
        await _execute(
            "UPDATE trades SET offer = ?, want = ?, active = 1, updated_at = ? WHERE id = ?",
            (offer, want, new_updated, trade_id),
        )
        await set_trade_videos(trade_id, videos, bump_updated=True)
    else:
        trade_id = await _execute(
            "INSERT INTO trades (user_id, offer, want, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, offer, want, ts, ts),
        )
        # При первом создании видео заполняем без лишнего +1 к updated_at:
        # делаем вид, что видео сохранились в тот же момент, что и сам трейд.
        # Иначе updated_at становится > времени любого немедленного обмена,
        # и проверка на «уже обменялись» ложноположительно срабатывает.
        await conn().execute("DELETE FROM trade_videos WHERE trade_id = ?", (trade_id,))
        await conn().executemany(
            "INSERT INTO trade_videos (trade_id, file_id, position) VALUES (?, ?, ?)",
            [(trade_id, file_id, i) for i, file_id in enumerate(videos)],
        )
        await conn().execute("UPDATE trades SET updated_at = ? WHERE id = ?", (ts, trade_id))
        await conn().commit()
    return trade_id


async def update_trade_fields(trade_id: int, *, offer: str | None = None, want: str | None = None) -> None:
    new_updated = await _trade_update_ts(trade_id)
    if offer is not None:
        await _execute("UPDATE trades SET offer = ?, updated_at = ? WHERE id = ?", (offer, new_updated, trade_id))
    if want is not None:
        if offer is None:
            await _execute("UPDATE trades SET want = ?, updated_at = ? WHERE id = ?", (want, new_updated, trade_id))
        else:
            await _execute("UPDATE trades SET want = ? WHERE id = ?", (want, trade_id))


async def set_trade_videos(trade_id: int, videos: list[str], bump_updated: bool = True) -> None:
    trade = await get_trade(trade_id)
    if bump_updated:
        new_updated = await _trade_update_ts(trade_id)
    else:
        new_updated = (trade["updated_at"] if trade else now())
    await conn().execute("DELETE FROM trade_videos WHERE trade_id = ?", (trade_id,))
    await conn().executemany(
        "INSERT INTO trade_videos (trade_id, file_id, position) VALUES (?, ?, ?)",
        [(trade_id, file_id, i) for i, file_id in enumerate(videos)],
    )
    await conn().execute("UPDATE trades SET updated_at = ? WHERE id = ?", (new_updated, trade_id))
    await conn().commit()


async def get_trade_videos(trade_id: int) -> list[str]:
    rows = await _fetchall(
        "SELECT file_id FROM trade_videos WHERE trade_id = ? ORDER BY position", (trade_id,)
    )
    return [row["file_id"] for row in rows]


async def set_trade_active(trade_id: int, active: bool) -> None:
    await _execute("UPDATE trades SET active = ? WHERE id = ?", (1 if active else 0, trade_id))


async def feed_trade_ids(viewer_id: int) -> list[int]:
    """Анкеты для ленты: сначала с активным бустом, потом свежие.
    Исключает анкеты, с которыми пользователь уже обменялся,
    если только анкета не была обновлена ПОСЛЕ последнего обмена."""
    rows = await _fetchall(
        """
        SELECT t.id
        FROM trades t
        JOIN users u ON u.user_id = t.user_id
        WHERE t.active = 1
          AND t.user_id != ?
          AND u.banned = 0
          AND NOT EXISTS (
              /* Проверяем, был ли уже обмен между viewer и владельцем анкеты,
                 который случился СТРОГО ПОСЛЕ последнего обновления анкеты.
                 Если такой обмен есть — анкету скрываем.
                 Если анкета обновилась УЖЕ ПОСЛЕ обмена — показываем заново. */
              SELECT 1
              FROM exchanges e
              WHERE e.status = 'completed'
                AND (
                    (e.initiator_id = ? AND e.partner_id = t.user_id)
                    OR
                    (e.partner_id = ? AND e.initiator_id = t.user_id)
                )
                AND e.created_at >= t.updated_at
          )
        ORDER BY (CASE WHEN u.boost_until > ? THEN 1 ELSE 0 END) DESC,
                 u.boost_until DESC,
                 t.updated_at DESC
        """,
        (viewer_id, viewer_id, viewer_id, now()),
    )
    return [row["id"] for row in rows]


# ---------------------------------------------------------------- exchanges


async def recent_exchange(initiator_id: int, trade_id: int, within_seconds: int) -> dict | None:
    return await _fetchone(
        """
        SELECT * FROM exchanges
        WHERE initiator_id = ? AND trade_id = ? AND created_at > ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (initiator_id, trade_id, now() - within_seconds),
    )


async def create_exchange(
    initiator_id: int,
    partner_id: int,
    trade_id: int,
    initiator_videos: list[str],
    partner_videos: list[str],
) -> int:
    # Гарантируем, что created_at обмена будет СТРОГО ПОСЛЕ updated_at трейда.
    # Иначе из-за int-секундной точности now() может оказаться меньше updated_at
    # (когда трейд только что обновили через +1), и проверка «уже обменялись»
    # в feed_trade_ids будет ложноположительно пропускать анкету.
    trade = await get_trade(trade_id)
    base_ts = now()
    if trade:
        base_ts = max(base_ts, trade["updated_at"] + 1)
    else:
        base_ts = base_ts + 1

    exchange_id = await _execute(
        "INSERT INTO exchanges (initiator_id, partner_id, trade_id, created_at) VALUES (?, ?, ?, ?)",
        (initiator_id, partner_id, trade_id, base_ts),
    )
    payload = [(exchange_id, initiator_id, f, i) for i, f in enumerate(initiator_videos)]
    payload += [(exchange_id, partner_id, f, i) for i, f in enumerate(partner_videos)]
    await conn().executemany(
        "INSERT INTO exchange_videos (exchange_id, owner_id, file_id, position) VALUES (?, ?, ?, ?)",
        payload,
    )
    await conn().commit()
    return exchange_id


async def get_exchange(exchange_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM exchanges WHERE id = ?", (exchange_id,))


async def get_exchange_videos(exchange_id: int, owner_id: int) -> list[str]:
    rows = await _fetchall(
        "SELECT file_id FROM exchange_videos WHERE exchange_id = ? AND owner_id = ? ORDER BY position",
        (exchange_id, owner_id),
    )
    return [row["file_id"] for row in rows]


# ---------------------------------------------------------------- reports / ratings / comments


async def add_report(
    reporter_id: int,
    target_id: int,
    kind: str,
    reason: str | None = None,
    comment: str | None = None,
    trade_id: int | None = None,
    exchange_id: int | None = None,
) -> int:
    return await _execute(
        """
        INSERT INTO reports (reporter_id, target_id, kind, reason, comment, trade_id, exchange_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (reporter_id, target_id, kind, reason, comment, trade_id, exchange_id, now()),
    )


async def get_report(report_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM reports WHERE id = ?", (report_id,))


async def set_report_status(report_id: int, status: str) -> None:
    await _execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))


async def open_reports_count() -> int:
    row = await _fetchone("SELECT COUNT(*) AS c FROM reports WHERE status = 'open'")
    return row["c"] if row else 0


async def reports_against(user_id: int) -> int:
    row = await _fetchone("SELECT COUNT(*) AS c FROM reports WHERE target_id = ?", (user_id,))
    return row["c"] if row else 0


async def add_rating(exchange_id: int, from_id: int, to_id: int, emoji: str, score: int) -> None:
    await _execute(
        """
        INSERT INTO ratings (exchange_id, from_id, to_id, emoji, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(exchange_id, from_id) DO UPDATE SET emoji = excluded.emoji, score = excluded.score
        """,
        (exchange_id, from_id, to_id, emoji, score, now()),
    )


async def rating_of(user_id: int) -> tuple[float, int]:
    row = await _fetchone(
        "SELECT AVG(score) AS avg_score, COUNT(*) AS c FROM ratings WHERE to_id = ?", (user_id,)
    )
    if not row or not row["c"]:
        return (0.0, 0)
    return (float(row["avg_score"]), int(row["c"]))


async def add_comment(exchange_id: int, from_id: int, to_id: int, text: str) -> int:
    return await _execute(
        "INSERT INTO comments (exchange_id, from_id, to_id, text, created_at) VALUES (?, ?, ?, ?, ?)",
        (exchange_id, from_id, to_id, text, now()),
    )


# ---------------------------------------------------------------- stats


async def stats() -> dict:
    users = await _fetchone("SELECT COUNT(*) AS c FROM users")
    banned = await _fetchone("SELECT COUNT(*) AS c FROM users WHERE banned = 1")
    trades = await _fetchone("SELECT COUNT(*) AS c FROM trades WHERE active = 1")
    exchanges = await _fetchone("SELECT COUNT(*) AS c FROM exchanges")
    day_exchanges = await _fetchone(
        "SELECT COUNT(*) AS c FROM exchanges WHERE created_at > ?", (now() - 86400,)
    )
    reports = await open_reports_count()
    referrals_total = await _fetchone("SELECT COALESCE(SUM(referrals), 0) AS c FROM users")
    with_referrer = await _fetchone("SELECT COUNT(*) AS c FROM users WHERE referrer_id IS NOT NULL")
    premium_users = await _fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE premium = 1 AND (premium_until = 0 OR premium_until > ?)", (now(),)
    )
    return {
        "users": users["c"] if users else 0,
        "banned": banned["c"] if banned else 0,
        "trades": trades["c"] if trades else 0,
        "exchanges": exchanges["c"] if exchanges else 0,
        "day_exchanges": day_exchanges["c"] if day_exchanges else 0,
        "open_reports": reports,
        "referrals_total": referrals_total["c"] if referrals_total else 0,
        "users_with_referrer": with_referrer["c"] if with_referrer else 0,
        "premium_users": premium_users["c"] if premium_users else 0,
    }
