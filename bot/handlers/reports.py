from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import db, keyboards, texts, utils
from ..states import Report

router = Router(name="reports")


@router.callback_query(F.data.startswith("report:profile:"))
async def report_profile(call: CallbackQuery, user: dict) -> None:
    trade_id = int(call.data.split(":")[2])
    trade = await db.get_trade(trade_id)
    if not trade:
        await call.answer("Анкета не найдена", show_alert=True)
        return
    target = await db.get_user(trade["user_id"])
    if target is None:
        await call.answer("Анкета не найдена", show_alert=True)
        return

    report_id = await db.add_report(
        reporter_id=user["user_id"],
        target_id=target["user_id"],
        kind="profile",
        reason="Содержание анкеты",
        trade_id=trade_id,
    )
    videos = await db.get_trade_videos(trade_id)
    await utils.notify_admins(
        call.bot,
        texts.report_profile_admin(user, target, trade, report_id),
        keyboards.admin_report(report_id, target["user_id"]),
        videos,
    )
    await call.answer("Жалоба отправлена 🚨", show_alert=True)
    await call.message.answer(texts.REPORT_SENT)


@router.callback_query(F.data.startswith("report:exchange:"))
async def report_exchange(call: CallbackQuery) -> None:
    exchange_id = int(call.data.split(":")[2])
    await call.message.answer(texts.REPORT_ASK_REASON, reply_markup=keyboards.report_reasons(exchange_id))
    await call.answer()


@router.callback_query(F.data.startswith("reason:"))
async def choose_reason(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    _, raw_id, key = call.data.split(":")
    exchange_id = int(raw_id)
    reason = keyboards.REPORT_REASONS.get(key, "Другое")

    if key == "other":
        await state.set_state(Report.text)
        await state.update_data(exchange_id=exchange_id, reason=reason)
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(texts.REPORT_ASK_TEXT, reply_markup=keyboards.cancel())
        await call.answer()
        return

    await call.message.edit_reply_markup(reply_markup=None)
    await _send_exchange_report(call.bot, user, exchange_id, reason, None)
    await call.answer("Жалоба отправлена 🚨")
    await call.message.answer(texts.REPORT_SENT)


@router.message(Report.text, F.text)
async def report_text(message: Message, state: FSMContext, user: dict) -> None:
    data = await state.get_data()
    await state.clear()
    await _send_exchange_report(
        message.bot, user, data["exchange_id"], data.get("reason", "Другое"), message.text.strip()[:500]
    )
    await message.answer(texts.REPORT_SENT, reply_markup=keyboards.main_menu())


async def _send_exchange_report(
    bot: Bot, reporter: dict, exchange_id: int, reason: str, comment: str | None
) -> None:
    exchange = await db.get_exchange(exchange_id)
    if not exchange:
        return
    if exchange["initiator_id"] == reporter["user_id"]:
        target_id = exchange["partner_id"]
    else:
        target_id = exchange["initiator_id"]
    target = await db.get_user(target_id)
    if target is None:
        return

    report_id = await db.add_report(
        reporter_id=reporter["user_id"],
        target_id=target_id,
        kind="exchange",
        reason=reason,
        comment=comment,
        exchange_id=exchange_id,
    )
    videos = await db.get_exchange_videos(exchange_id, target_id)
    await utils.notify_admins(
        bot,
        texts.report_exchange_admin(reporter, target, reason, comment, exchange_id, report_id),
        keyboards.admin_report(report_id, target_id),
        videos,
    )
