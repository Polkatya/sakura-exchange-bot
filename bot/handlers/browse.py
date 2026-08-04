from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import db, keyboards, texts, utils
from ..config import config

router = Router(name="browse")


@router.message(F.text == keyboards.BTN_SEARCH)
async def open_feed(message: Message, state: FSMContext, user: dict) -> None:
    await state.clear()
    await _open(message.bot, message.chat.id, state, user)


@router.callback_query(F.data == "feed:open")
async def cb_open_feed(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    await state.clear()
    await call.answer()
    await _open(call.bot, call.message.chat.id, state, user)


async def _open(bot: Bot, chat_id: int, state: FSMContext, user: dict) -> None:
    trade = await db.get_trade_by_user(user["user_id"])
    if not trade:
        await bot.send_message(chat_id, texts.NEED_TRADE, reply_markup=keyboards.main_menu())
        return
    if config.search_requires_premium and not utils.is_premium(user):
        await bot.send_message(chat_id, texts.PREMIUM_LOCKED_SEARCH, reply_markup=keyboards.go_premium())
        return

    feed = await db.feed_trade_ids(user["user_id"])
    if not feed:
        await bot.send_message(chat_id, texts.FEED_EMPTY, reply_markup=keyboards.main_menu())
        return
    await state.update_data(feed=feed, idx=0)
    await _show_card(bot, chat_id, state)


@router.callback_query(F.data == "feed:next")
async def cb_next(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    data = await state.get_data()
    feed: list[int] = data.get("feed", [])
    if not feed:
        await call.answer()
        await _open(call.bot, call.message.chat.id, state, user)
        return
    idx = data.get("idx", 0) + 1
    wrapped = idx >= len(feed)
    await state.update_data(idx=0 if wrapped else idx)
    await call.answer("🔁 Начинаем сначала" if wrapped else texts.FEED_SKIPPED)
    await _show_card(call.bot, call.message.chat.id, state)


@router.callback_query(F.data == "feed:prev")
async def cb_prev(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    if not config.search_requires_premium and not utils.is_premium(user):
        await call.answer("🔒 Премиум-функция", show_alert=True)
        await call.message.answer(texts.PREMIUM_LOCKED_BACK, reply_markup=keyboards.go_premium())
        return
    data = await state.get_data()
    feed: list[int] = data.get("feed", [])
    idx = data.get("idx", 0)
    if not feed:
        await call.answer()
        await _open(call.bot, call.message.chat.id, state, user)
        return
    if idx == 0:
        await call.answer("Это первая анкета", show_alert=False)
        return
    await state.update_data(idx=idx - 1)
    await call.answer("⬅️ Назад")
    await _show_card(call.bot, call.message.chat.id, state)


async def _show_card(bot: Bot, chat_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    feed: list[int] = list(data.get("feed", []))
    idx: int = data.get("idx", 0)

    while feed:
        if idx >= len(feed):
            idx = 0
        trade_id = feed[idx]
        trade = await db.get_trade(trade_id)
        owner = await db.get_user(trade["user_id"]) if trade else None
        if not trade or not trade["active"] or owner is None or owner["banned"]:
            feed.pop(idx)
            await state.update_data(feed=feed, idx=idx)
            continue

        videos = await db.get_trade_videos(trade_id)
        avg, count = await db.rating_of(owner["user_id"])
        card = texts.feed_card(trade, owner, len(videos), avg, count, idx + 1, len(feed))
        await state.update_data(feed=feed, idx=idx)
        await bot.send_message(chat_id, card, reply_markup=keyboards.feed_card(trade_id))
        return

    await state.update_data(feed=[], idx=0)
    await bot.send_message(chat_id, texts.FEED_EMPTY, reply_markup=keyboards.main_menu())
