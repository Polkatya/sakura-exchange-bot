from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from .. import db, keyboards, texts, utils
from ..config import PREMIUM_TIERS, config

router = Router(name="premium")

_PAYLOAD_PREFIX = "premium:"


def _tier_by_id(tier_id: str):
    for t in PREMIUM_TIERS:
        if t.id == tier_id:
            return t
    return None


@router.message(F.text == keyboards.BTN_PREMIUM)
async def show_premium(message: Message, state: FSMContext, user: dict) -> None:
    await state.clear()
    link = await utils.referral_link(message.bot, user["user_id"])
    active_premium = db.is_premium_active(user)
    await message.answer(
        texts.premium(user, link), reply_markup=keyboards.premium(link, active_premium)
    )


@router.callback_query(F.data == "premium:open")
async def cb_premium(call: CallbackQuery, user: dict) -> None:
    link = await utils.referral_link(call.bot, user["user_id"])
    active_premium = db.is_premium_active(user)
    await call.message.answer(
        texts.premium(user, link), reply_markup=keyboards.premium(link, active_premium)
    )
    await call.answer()


@router.callback_query(F.data.startswith("premium:buy"))
async def cb_buy(call: CallbackQuery, user: dict) -> None:
    parts = call.data.split(":")
    tier_id = parts[2] if len(parts) >= 3 else "forever"
    tier = _tier_by_id(tier_id)
    if tier is None:
        await call.answer("Тариф не найден", show_alert=True)
        return
    if tier.stars <= 0:
        await call.answer("Оплата звёздами отключена", show_alert=True)
        return
    if db.is_premium_active(user):
        await call.answer("У вас уже есть активный премиум 👑", show_alert=True)
        return
    duration_line = "навсегда" if tier.hours == 0 else f"на {tier.label}"
    await call.bot.send_invoice(
        chat_id=call.message.chat.id,
        title=f"👑 Премиум {tier.label} SakuraExchange",
        description=(
            f"Премиум {duration_line}: снятие лимитов, стрелка «назад» в ленте, "
            "приоритет анкеты. Оплата звёздами Telegram."
        ),
        payload=f"{_PAYLOAD_PREFIX}{tier.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Премиум {tier.label}", amount=tier.stars)],
    )
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message, user: dict) -> None:
    if not message.successful_payment.invoice_payload.startswith(_PAYLOAD_PREFIX):
        # Оставляем обратную совместимость со старым платежом PAYLOAD "premium_forever"
        tier_id = "forever"
    else:
        tier_id = message.successful_payment.invoice_payload[len(_PAYLOAD_PREFIX):]
    tier = _tier_by_id(tier_id) or _tier_by_id("forever")
    if tier.hours == 0:
        await db.set_premium(user["user_id"], True, hours=0)
        premium_note = "👑 <b>Премиум активирован навсегда!</b>\n\n"
    else:
        await db.set_premium(user["user_id"], True, hours=tier.hours)
        premium_note = f"👑 <b>Премиум активирован на {tier.label}!</b>\n\n"
    await db.add_boost(user["user_id"], 24 * 3600)
    await message.answer(
        premium_note
        + "🚀 Бонус: буст анкеты на 24 часа\n"
        + "Спасибо за поддержку 🌸",
        reply_markup=keyboards.main_menu(),
    )
    await utils.notify_admins(
        message.bot,
        f"💰 <b>Оплата премиума ({tier.label})</b>\n{texts.admin_user_title(user)} "
        f"(<code>{user['user_id']}</code>) — {tier.stars} ⭐️",
    )
