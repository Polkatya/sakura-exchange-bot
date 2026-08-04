from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import db, keyboards, texts, utils
from ..config import config

router = Router(name="common")
fallback_router = Router(name="fallback")


def help_text() -> str:
    return (
        "❓ <b>Как это работает</b>\n\n"
        "1️⃣ ➕ <b>Создать трейд</b> — тема, "
        f"{config.videos_per_trade} видео, что ищете\n"
        "2️⃣ 🔍 <b>Искать трейды</b> — листайте анкеты стрелками\n"
        f"3️⃣ 🤝 <b>Начать трейд</b> — кидаете {config.videos_per_trade} видео "
        f"и сразу получаете {config.videos_per_trade} в ответ\n"
        "4️⃣ ⭐️ После обмена — оценка, комментарий или 🚨 жалоба\n"
        "5️⃣ 👑 <b>Премиум</b> — рефералы, буст анкеты\n\n"
        "🚫 Запрещённый контент = перманентный бан.\n"
        "Команды: /start /menu /cancel /rules\n\n" + texts.tip()
    )


async def show_menu(message: Message, text: str | None = None) -> None:
    await message.answer(
        text or f"🏠 <b>Главное меню</b>\n\n{texts.tip()}", reply_markup=keyboards.main_menu()
    )


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, user: dict) -> None:
    await state.clear()
    payload = (command.args or "").strip()
    if payload.startswith("ref_") and not user["agreed"] and user["referrer_id"] is None:
        try:
            referrer_id = int(payload[4:])
        except ValueError:
            referrer_id = 0
        if referrer_id and referrer_id != user["user_id"] and await db.get_user(referrer_id):
            await db.set_referrer(user["user_id"], referrer_id)

    if user["agreed"]:
        await show_menu(message, f"🌸 <b>С возвращением!</b>\n\n{texts.tip()}")
        return
    await message.answer(texts.RULES, reply_markup=keyboards.rules())


@router.callback_query(F.data == "agree")
async def cb_agree(call: CallbackQuery, state: FSMContext, user: dict) -> None:
    await state.clear()
    if not user["agreed"]:
        await db.set_agreed(user["user_id"])
        await _reward_referrer(call, user)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.AGREED, reply_markup=keyboards.main_menu())
    await call.answer("Добро пожаловать 🌸")


async def _reward_referrer(call: CallbackQuery, user: dict) -> None:
    referrer_id = user["referrer_id"]
    if not referrer_id:
        return
    referrer = await db.add_referral(referrer_id)
    need = config.premium_referrals_required
    if referrer["premium"]:
        text = (
            "🎉 <b>+1 реферал!</b>\n\n"
            f"👑 Премиум открыт <b>навсегда</b>\n"
            f"🚀 Буст анкеты: <b>{texts.boost_left(referrer)}</b>"
        )
    else:
        left = max(0, need - referrer["referrals"])
        text = (
            "🎉 <b>+1 реферал!</b>\n\n"
            f"📊 Прогресс: <b>{referrer['referrals']} / {need}</b>\n"
            f"{texts.progress_bar(min(referrer['referrals'], need), need)}\n"
            f"⏳ До премиума навсегда осталось: <b>{left}</b>\n"
            f"🚀 Буст анкеты: <b>{texts.boost_left(referrer)}</b>"
        )
    await utils.safe_send(call.bot, referrer_id, text)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_menu(message)


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(texts.RULES)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_menu(message, texts.CANCELLED)


@router.message(Command("help"))
@router.message(F.text == keyboards.BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(help_text(), reply_markup=keyboards.main_menu())


@router.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())
    await call.answer()


@fallback_router.message(StateFilter(None))
async def fallback(message: Message) -> None:
    await message.answer(
        "🤔 <b>Не понял команду</b>\n\nВыберите действие в меню ниже 👇",
        reply_markup=keyboards.main_menu(),
    )


@router.callback_query(F.data == "feed:home")
async def cb_home(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.answer(f"🏠 <b>Главное меню</b>\n\n{texts.tip()}", reply_markup=keyboards.main_menu())
    await call.answer()
