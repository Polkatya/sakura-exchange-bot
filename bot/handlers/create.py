from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import db, keyboards, texts, utils
from ..config import config
from ..states import CreateTrade

router = Router(name="create")

MAX_TEXT = 200


@router.message(F.text == keyboards.BTN_CREATE)
async def start_create(message: Message, state: FSMContext, user: dict) -> None:
    await state.clear()
    trade = await db.get_trade_by_user(user["user_id"])
    if trade:
        await message.answer(
            "♻️ <b>У вас уже есть трейд</b>\n\nМожно пересоздать его с нуля или отредактировать по частям.",
            reply_markup=keyboards.trade_exists(),
        )
        return
    await state.set_state(CreateTrade.offer)
    await message.answer(texts.CREATE_STEP1, reply_markup=keyboards.cancel())


@router.callback_query(F.data == "create:new")
async def restart_create(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateTrade.offer)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.CREATE_STEP1, reply_markup=keyboards.cancel())
    await call.answer()


@router.message(CreateTrade.offer, F.text)
async def step_offer(message: Message, state: FSMContext) -> None:
    offer = message.text.strip()[:MAX_TEXT]
    if not offer:
        await message.answer("✍️ Напишите текстом, что вы предлагаете.")
        return
    has_bad, bad_words = utils.contains_forbidden(offer)
    if has_bad:
        await message.answer(texts.forbidden_words_error(bad_words))
        return
    await state.update_data(offer=offer, videos=[])
    await state.set_state(CreateTrade.videos)
    prompt = await message.answer(texts.create_step2(0), reply_markup=keyboards.cancel())
    await state.update_data(prompt_id=prompt.message_id)


@router.message(CreateTrade.videos, F.video)
async def step_videos(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    videos: list[str] = list(data.get("videos", []))
    videos.append(message.video.file_id)
    videos = videos[: config.videos_per_trade]
    await state.update_data(videos=videos)

    if len(videos) < config.videos_per_trade:
        await _update_progress(message, state, texts.create_step2(len(videos)))
        return

    await state.set_state(CreateTrade.want)
    await message.answer(texts.CREATE_STEP3, reply_markup=keyboards.cancel())


@router.message(CreateTrade.videos)
async def step_videos_wrong(message: Message) -> None:
    await message.answer(texts.ONLY_VIDEO)


@router.message(CreateTrade.want, F.text)
async def step_want(message: Message, state: FSMContext, user: dict) -> None:
    want = message.text.strip()[:MAX_TEXT]
    if not want:
        await message.answer("✍️ Напишите текстом, что вы ищете.")
        return
    has_bad, bad_words = utils.contains_forbidden(want)
    if has_bad:
        await message.answer(texts.forbidden_words_error(bad_words))
        return
    data = await state.get_data()
    offer: str = data["offer"]
    videos: list[str] = data["videos"]
    await db.save_trade(user["user_id"], offer, want, videos)
    await state.clear()
    await message.answer(
        texts.trade_created(offer, want, len(videos)),
        reply_markup=keyboards.main_menu(),
    )


@router.message(CreateTrade.offer)
@router.message(CreateTrade.want)
async def step_text_wrong(message: Message) -> None:
    await message.answer("✍️ Ответьте, пожалуйста, текстом.")


async def _update_progress(message: Message, state: FSMContext, text: str) -> None:
    data = await state.get_data()
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        sent = await message.answer(text, reply_markup=keyboards.cancel())
        await state.update_data(prompt_id=sent.message_id)
        return
    try:
        await message.bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=prompt_id,
            reply_markup=keyboards.cancel(),
        )
    except TelegramBadRequest:
        sent = await message.answer(text, reply_markup=keyboards.cancel())
        await state.update_data(prompt_id=sent.message_id)
