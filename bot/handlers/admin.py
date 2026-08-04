from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from .. import db, texts, utils
from ..config import config

router = Router(name="admin")
router.message.filter(F.from_user.id.in_(set(config.admin_ids)))
router.callback_query.filter(F.from_user.id.in_(set(config.admin_ids)))

BAN_NOTICE = (
    "⛔️ <b>Вы заблокированы</b>\n\nПричина: нарушение правил бота.\nВаша анкета скрыта, доступ закрыт."
)

ADMIN_HELP = (
    "🛠 <b>Админка</b>\n\n"
    "/stats — статистика\n"
    "/user &lt;id&gt; — карточка пользователя\n"
    "/ban &lt;id&gt; [причина] — бан\n"
    "/unban &lt;id&gt; — разбан\n"
    "/verify &lt;id&gt; — выдать ✅\n"
    "/unverify &lt;id&gt; — снять ✅\n"
    "/grant &lt;id&gt; — выдать премиум\n"
    "/boost &lt;id&gt; &lt;часов&gt; — выдать буст\n"
    "/broadcast &lt;текст&gt; — рассылка"
)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer(ADMIN_HELP)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    data = await db.stats()
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{data['users']}</b>\n"
        f"⛔️ Забанено: <b>{data['banned']}</b>\n"
        f"👑 Активных премиум: <b>{data['premium_users']}</b>\n"
        f"📄 Активных анкет: <b>{data['trades']}</b>\n"
        f"🤝 Обменов всего: <b>{data['exchanges']}</b>\n"
        f"📅 Обменов за сутки: <b>{data['day_exchanges']}</b>\n"
        f"🚨 Открытых жалоб: <b>{data['open_reports']}</b>\n\n"
        f"🔗 <b>Рефералы:</b>\n"
        f"  • Приглашено пользователей всего: <b>{data['referrals_total']}</b>\n"
        f"  • У кого есть реферер (по ссылкам): <b>{data['users_with_referrer']}</b>"
    )


@router.message(Command("user"))
async def cmd_user(message: Message, command: CommandObject) -> None:
    target = await _target_from_args(message, command)
    if target is None:
        return
    trade = await db.get_trade_by_user(target["user_id"])
    avg, count = await db.rating_of(target["user_id"])
    complaints = await db.reports_against(target["user_id"])
    await message.answer(
        f"👤 {texts.admin_user_title(target)} (<code>{target['user_id']}</code>)\n\n"
        f"⛔️ Бан: {'да' if target['banned'] else 'нет'}\n"
        f"👑 Премиум: {'да' if target['premium'] else 'нет'}\n"
        f"👥 Рефералов: {target['referrals']}\n"
        f"🤝 Обменов: {target['trades_done']}\n"
        f"{texts.rating_line(avg, count)}\n"
        f"🚨 Жалоб на него: {complaints}\n"
        f"{texts.boost_line(target)}\n"
        f"📄 Анкета: {'#' + str(trade['id']) if trade else 'нет'}"
    )


@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject) -> None:
    target = await _target_from_args(message, command)
    if target is None:
        return
    parts = (command.args or "").split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "нарушение правил"
    await db.set_banned(target["user_id"], True, reason)
    await utils.safe_send(message.bot, target["user_id"], BAN_NOTICE)
    await message.answer(f"🔨 Забанен <code>{target['user_id']}</code>\nПричина: {reason}")


@router.message(Command("unban"))
async def cmd_unban(message: Message, command: CommandObject) -> None:
    target = await _target_from_args(message, command)
    if target is None:
        return
    await db.set_banned(target["user_id"], False)
    await utils.safe_send(message.bot, target["user_id"], "✅ Бан снят. Не нарушайте правила 🌸")
    await message.answer(f"✅ Разбанен <code>{target['user_id']}</code>")


@router.message(Command("verify"))
async def cmd_verify(message: Message, command: CommandObject) -> None:
    target = await _target_from_args(message, command)
    if target is None:
        return
    await db.set_verified(target["user_id"], True)
    await utils.safe_send(
        message.bot,
        target["user_id"],
        "✅ <b>Ваша анкета верифицирована!</b>\nТеперь рядом с ником стоит галочка.",
    )
    await message.answer(f"☑️ Верифицирован <code>{target['user_id']}</code>")


@router.message(Command("unverify"))
async def cmd_unverify(message: Message, command: CommandObject) -> None:
    target = await _target_from_args(message, command)
    if target is None:
        return
    await db.set_verified(target["user_id"], False)
    await message.answer(f"➖ Галочка снята у <code>{target['user_id']}</code>")


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject) -> None:
    target = await _target_from_args(message, command)
    if target is None:
        return
    await db.set_premium(target["user_id"], True)
    await utils.safe_send(message.bot, target["user_id"], "👑 <b>Вам выдан премиум навсегда!</b>")
    await message.answer(f"👑 Премиум выдан <code>{target['user_id']}</code>")


@router.message(Command("boost"))
async def cmd_boost(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").split()
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("Формат: /boost &lt;id&gt; &lt;часов&gt;")
        return
    user_id, hours = int(parts[0]), int(parts[1])
    if await db.get_user(user_id) is None:
        await message.answer("Пользователь не найден")
        return
    await db.add_boost(user_id, hours * 3600)
    await utils.safe_send(message.bot, user_id, f"🚀 <b>Вам выдан буст анкеты на {hours} ч!</b>")
    await message.answer(f"🚀 Буст {hours} ч выдан <code>{user_id}</code>")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject) -> None:
    text = (command.args or "").strip()
    if not text:
        await message.answer("Формат: /broadcast &lt;текст&gt;")
        return
    user_ids = await db.all_user_ids()
    sent = 0
    for user_id in user_ids:
        if await utils.safe_send(message.bot, user_id, f"📢 <b>Объявление</b>\n\n{text}"):
            sent += 1
        await asyncio.sleep(0.05)
    await message.answer(f"📢 Отправлено: <b>{sent}</b> из {len(user_ids)}")


@router.callback_query(F.data.startswith("adm:"))
async def admin_action(call: CallbackQuery) -> None:
    _, action, raw_report, raw_target = call.data.split(":")
    report_id, target_id = int(raw_report), int(raw_target)
    target = await db.get_user(target_id)
    if target is None:
        await call.answer("Пользователь не найден", show_alert=True)
        return

    if action == "ban":
        await db.set_banned(target_id, True, "жалоба")
        await db.set_report_status(report_id, "banned")
        await utils.safe_send(call.bot, target_id, BAN_NOTICE)
        result = f"🔨 Забанен {texts.admin_user_title(target)}"
    elif action == "dismiss":
        await db.set_report_status(report_id, "dismissed")
        result = "✅ Жалоба отклонена"
    elif action == "hide":
        trade = await db.get_trade_by_user(target_id)
        if trade:
            await db.set_trade_active(trade["id"], False)
        await db.set_report_status(report_id, "hidden")
        await utils.safe_send(
            call.bot,
            target_id,
            "🙈 <b>Ваша анкета скрыта модерацией</b>\nОтредактируйте её и верните в ленту.",
        )
        result = "🙈 Анкета скрыта"
    elif action == "verify":
        await db.set_verified(target_id, True)
        await db.set_report_status(report_id, "dismissed")
        result = "☑️ Пользователь верифицирован"
    else:
        await call.answer()
        return

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(f"{result}\n🆔 Жалоба #{report_id}")
    await call.answer()


async def _target_from_args(message: Message, command: CommandObject) -> dict | None:
    raw = (command.args or "").split(maxsplit=1)
    if not raw or not raw[0].lstrip("-").isdigit():
        await message.answer("Формат: /команда &lt;user_id&gt;")
        return None
    user = await db.get_user(int(raw[0]))
    if user is None:
        await message.answer("Пользователь не найден")
        return None
    return user
