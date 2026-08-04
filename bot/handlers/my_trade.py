from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import db, keyboards, texts, utils
from ..config import config
from ..states import EditTrade

router = Router(name="my_trade")


@router.message(F.text == keyboards.BTN_MY_TRADE)
async def show_my_trade(message: Message, state: FSMContext, user: dict) -> None:
    await state.clear()
    trade = await db.get_trade_by_user(user["user_id"])
    if not trade:
        await message.answer(texts.NEED_TRADE, reply_markup=keyboards.main_menu())
        return
    videos = await db.get_trade_videos(trade["id"])
    avg, count = await db.rating_of(user["user_id"])
    card = texts.my_trade(trade, user, len(videos), avg, count)
    if not trade["active"]:
        card += "\n\n🙈 <i>Анкета скрыта из ленты</i>"
    await utils.send_videos(message.bot, message.chat.id, videos, caption=card)
    if not videos:
        await message.answer(card)
    await message.answer("⚙️ Управление анкетой:", reply_markup=keyboards.my_trade())


@router.callback_query(F.data == "edit:menu")
async def edit_menu(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    await state.clear()
    trade = await db.get_trade_by_user(user["user_id"])
    if not trade:
        await call.answer("Сначала создайте трейд", show_alert=True)
        return
    await call.message.answer("✏️ <b>Что меняем?</b>", reply_markup=keyboards.edit_menu(bool(trade["active"])))
    await call.answer()


@router.callback_query(F.data == "edit:offer")
async def edit_offer(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditTrade.offer)
    await call.message.answer(
        "📦 <b>Что вы предлагаете?</b>\n<i>Напишите новый текст.</i>", reply_markup=keyboards.cancel()
    )
    await call.answer()


@router.callback_query(F.data == "edit:want")
async def edit_want(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditTrade.want)
    await call.message.answer(
        "🔍 <b>Что вы ищете?</b>\n<i>Напишите новый текст.</i>", reply_markup=keyboards.cancel()
    )
    await call.answer()


@router.callback_query(F.data == "edit:videos")
async def edit_videos(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditTrade.videos)
    await state.update_data(videos=[])
    prompt = await call.message.answer(
        f"🎬 <b>Отправьте {config.videos_per_trade} новых видео</b>\n"
        f"📎 Отправлено: <b>0 / {config.videos_per_trade}</b>\n"
        f"{texts.progress_bar(0, config.videos_per_trade)}",
        reply_markup=keyboards.cancel(),
    )
    await state.update_data(prompt_id=prompt.message_id)
    await call.answer()


@router.callback_query(F.data.in_({"edit:hide", "edit:show"}))
async def toggle_active(call: CallbackQuery, user: dict) -> None:
    trade = await db.get_trade_by_user(user["user_id"])
    if not trade:
        await call.answer("Сначала создайте трейд", show_alert=True)
        return
    active = call.data == "edit:show"
    await db.set_trade_active(trade["id"], active)
    await call.message.edit_text(
        "👁 <b>Анкета снова в ленте</b>" if active else "🙈 <b>Анкета скрыта из ленты</b>",
        reply_markup=keyboards.edit_menu(active),
    )
    await call.answer()


@router.callback_query(F.data == "edit:back")
async def edit_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("🏠 <b>Главное меню</b>", reply_markup=keyboards.main_menu())
    await call.answer()


@router.message(EditTrade.offer, F.text)
async def save_offer(message: Message, state: FSMContext, user: dict) -> None:
    offer = message.text.strip()[:200]
    has_bad, bad_words = utils.contains_forbidden(offer)
    if has_bad:
        await message.answer(texts.forbidden_words_error(bad_words))
        return
    trade = await db.get_trade_by_user(user["user_id"])
    if trade:
        await db.update_trade_fields(trade["id"], offer=offer)
    await state.clear()
    await message.answer("✅ <b>Обновлено!</b>", reply_markup=keyboards.main_menu())


@router.message(EditTrade.want, F.text)
async def save_want(message: Message, state: FSMContext, user: dict) -> None:
    want = message.text.strip()[:200]
    has_bad, bad_words = utils.contains_forbidden(want)
    if has_bad:
        await message.answer(texts.forbidden_words_error(bad_words))
        return
    trade = await db.get_trade_by_user(user["user_id"])
    if trade:
        await db.update_trade_fields(trade["id"], want=want)
    await state.clear()
    await message.answer("✅ <b>Обновлено!</b>", reply_markup=keyboards.main_menu())


@router.message(EditTrade.videos, F.video)
async def save_videos(message: Message, state: FSMContext, user: dict) -> None:
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

    trade = await db.get_trade_by_user(user["user_id"])
    if trade:
        await db.set_trade_videos(trade["id"], videos)
    await state.clear()
    await message.answer(
        f"✅ <b>Видео обновлены!</b>\n🎬 В анкете: {len(videos)} шт.",
        reply_markup=keyboards.main_menu(),
    )


@router.message(EditTrade.videos)
async def save_videos_wrong(message: Message) -> None:
    await message.answer(texts.ONLY_VIDEO)
