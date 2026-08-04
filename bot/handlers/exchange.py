from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import db, keyboards, texts, utils
from ..config import config
from ..states import Comment, Exchange

router = Router(name="exchange")

RATING_EMOJI = {5: "🔥", 4: "👍", 3: "😐", 1: "👎"}


@router.callback_query(F.data.startswith("trade:start:"))
async def start_trade(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    trade_id = int(call.data.split(":")[2])
    trade = await db.get_trade(trade_id)
    if not trade or not trade["active"]:
        await call.answer("Анкета больше недоступна", show_alert=True)
        return
    if trade["user_id"] == user["user_id"]:
        await call.answer("Это ваша анкета 🙂", show_alert=True)
        return

    partner = await db.get_user(trade["user_id"])
    if partner is None or partner["banned"]:
        await call.answer("Анкета больше недоступна", show_alert=True)
        return

    my_trade = await db.get_trade_by_user(user["user_id"])
    if not my_trade:
        await call.answer("Сначала создайте свой трейд", show_alert=True)
        return

    # Лимит обменов (5 по умолчанию + рефералы). Премиум = безлимит.
    limit = db.trade_limit_of(user)
    done = int(user.get("trades_done") or 0)
    if done >= limit:
        await call.message.answer(
            texts.trade_limit_reached(done, limit), reply_markup=keyboards.go_premium()
        )
        await call.answer("Лимит трейдов превышен", show_alert=True)
        return

    cooldown = config.repeat_trade_cooldown_hours * 3600
    if cooldown and await db.recent_exchange(user["user_id"], trade_id, cooldown):
        await call.answer(
            f"Вы уже обменивались с этой анкетой. Повтор через {config.repeat_trade_cooldown_hours} ч.",
            show_alert=True,
        )
        return

    my_videos = await db.get_trade_videos(my_trade["id"])
    await state.set_state(Exchange.videos)
    await state.update_data(trade_id=trade_id, partner_id=partner["user_id"], videos=[])
    await call.message.answer(
        texts.exchange_intro(trade["want"], 0),
        reply_markup=keyboards.exchange_collect(trade_id, len(my_videos) >= config.videos_per_trade),
    )
    await call.answer()


@router.callback_query(Exchange.videos, F.data.startswith("trade:useprofile:"))
async def use_profile_videos(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    my_trade = await db.get_trade_by_user(user["user_id"])
    videos = await db.get_trade_videos(my_trade["id"]) if my_trade else []
    if len(videos) < config.videos_per_trade:
        await call.answer("В анкете не хватает видео", show_alert=True)
        return
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("Беру видео из анкеты 📁")
    await _finish_exchange(call.bot, call.message.chat.id, state, user, videos)


@router.message(Exchange.videos, F.video)
async def collect_videos(message: Message, state: FSMContext, user: dict) -> None:
    data = await state.get_data()
    videos: list[str] = list(data.get("videos", []))
    videos.append(message.video.file_id)
    videos = videos[: config.videos_per_trade]
    await state.update_data(videos=videos)

    if len(videos) < config.videos_per_trade:
        await message.answer(
            f"📎 Отправлено: <b>{len(videos)} / {config.videos_per_trade}</b>\n"
            f"{texts.progress_bar(len(videos), config.videos_per_trade)}"
        )
        return
    await _finish_exchange(message.bot, message.chat.id, state, user, videos)


@router.message(Exchange.videos)
async def collect_videos_wrong(message: Message) -> None:
    await message.answer(texts.ONLY_VIDEO)


async def _finish_exchange(
    bot: Bot, chat_id: int, state: FSMContext, user: dict, my_videos: list[str]
) -> None:
    data = await state.get_data()
    trade_id: int = data["trade_id"]
    await state.clear()

    trade = await db.get_trade(trade_id)
    partner = await db.get_user(trade["user_id"]) if trade else None
    if not trade or not trade["active"] or partner is None or partner["banned"]:
        await bot.send_message(
            chat_id,
            "😔 <b>Анкета стала недоступна</b>\nОбмен отменён, ваши видео никому не отправлены.",
            reply_markup=keyboards.main_menu(),
        )
        return

    partner_videos = await db.get_trade_videos(trade_id)
    exchange_id = await db.create_exchange(
        user["user_id"], partner["user_id"], trade_id, my_videos, partner_videos
    )
    await db.incr_trades_done(user["user_id"], partner["user_id"])

    await utils.send_videos(bot, chat_id, partner_videos)
    await bot.send_message(
        chat_id,
        texts.exchange_done_for_initiator(partner, exchange_id),
        reply_markup=keyboards.after_exchange(exchange_id),
    )

    delivered = await utils.safe_send(
        bot, partner["user_id"], texts.exchange_done_for_partner(user, exchange_id)
    )
    if delivered:
        await utils.send_videos(bot, partner["user_id"], my_videos)
        await bot.send_message(
            partner["user_id"],
            "⭐️ Оцените обмен или пожалуйтесь, если что-то не так:",
            reply_markup=keyboards.after_exchange(exchange_id),
        )


@router.callback_query(F.data.startswith("rate:"))
async def rate_exchange(call: CallbackQuery, user: dict) -> None:
    _, raw_id, raw_score = call.data.split(":")
    exchange_id, score = int(raw_id), int(raw_score)
    exchange = await db.get_exchange(exchange_id)
    if not exchange:
        await call.answer("Обмен не найден", show_alert=True)
        return
    partner_id = _other_side(exchange, user["user_id"])
    if partner_id is None:
        await call.answer("Это не ваш обмен", show_alert=True)
        return
    await db.add_rating(exchange_id, user["user_id"], partner_id, RATING_EMOJI.get(score, "😐"), score)
    await call.answer(f"Оценка {RATING_EMOJI.get(score, '')} сохранена, спасибо!")
    await utils.safe_send(
        call.bot,
        partner_id,
        f"⭐️ <b>Вас оценили после обмена #{exchange_id}:</b> {RATING_EMOJI.get(score, '')}",
    )


@router.callback_query(F.data.startswith("comment:"))
async def ask_comment(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    exchange_id = int(call.data.split(":")[1])
    exchange = await db.get_exchange(exchange_id)
    if not exchange or _other_side(exchange, user["user_id"]) is None:
        await call.answer("Обмен не найден", show_alert=True)
        return
    await state.set_state(Comment.text)
    await state.update_data(exchange_id=exchange_id)
    await call.message.answer(texts.COMMENT_ASK, reply_markup=keyboards.cancel())
    await call.answer()


@router.message(Comment.text, F.text)
async def save_comment(message: Message, state: FSMContext, user: dict) -> None:
    data = await state.get_data()
    exchange_id: int = data["exchange_id"]
    await state.clear()
    exchange = await db.get_exchange(exchange_id)
    partner_id = _other_side(exchange, user["user_id"]) if exchange else None
    if partner_id is None:
        await message.answer("😔 Обмен не найден.", reply_markup=keyboards.main_menu())
        return
    text = message.text.strip()[:500]
    await db.add_comment(exchange_id, user["user_id"], partner_id, text)
    await utils.safe_send(message.bot, partner_id, texts.comment_delivered(user, text))
    await message.answer("✅ <b>Комментарий отправлен</b>", reply_markup=keyboards.main_menu())


def _other_side(exchange: dict, user_id: int) -> int | None:
    if exchange["initiator_id"] == user_id:
        return exchange["partner_id"]
    if exchange["partner_id"] == user_id:
        return exchange["initiator_id"]
    return None
