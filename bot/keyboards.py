from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .config import PREMIUM_TIERS, config

BTN_MY_TRADE = "👤 Мой трейд"
BTN_PREMIUM = "👑 Премиум"
BTN_SEARCH = "🔍 Искать трейды"
BTN_CREATE = "➕ Создать трейд"
BTN_HELP = "❓ Помощь"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MY_TRADE), KeyboardButton(text=BTN_PREMIUM)],
            [KeyboardButton(text=BTN_SEARCH)],
            [KeyboardButton(text=BTN_CREATE), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие 🌸",
    )


def rules() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Согласен с правилами", callback_data="agree")]]
    )


def cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    )


def my_trade() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить трейд", callback_data="edit:menu")],
            [InlineKeyboardButton(text="🔍 Искать трейды", callback_data="feed:open")],
        ]
    )


def trade_exists() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♻️ Создать заново", callback_data="create:new")],
            [InlineKeyboardButton(text="✏️ Изменить трейд", callback_data="edit:menu")],
        ]
    )


def edit_menu(active: bool) -> InlineKeyboardMarkup:
    toggle = (
        InlineKeyboardButton(text="🙈 Скрыть анкету из ленты", callback_data="edit:hide")
        if active
        else InlineKeyboardButton(text="👁 Вернуть анкету в ленту", callback_data="edit:show")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Изменить «предлагаю»", callback_data="edit:offer")],
            [InlineKeyboardButton(text="🔍 Изменить «ищу»", callback_data="edit:want")],
            [InlineKeyboardButton(text="🎬 Заменить видео", callback_data="edit:videos")],
            [toggle],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit:back")],
        ]
    )


def feed_card(trade_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚨 Пожаловаться на анкету", callback_data=f"report:profile:{trade_id}"
                )
            ],
            [
                InlineKeyboardButton(text="⬅️", callback_data="feed:prev"),
                InlineKeyboardButton(text="🏠 Главная", callback_data="feed:home"),
                InlineKeyboardButton(text="➡️", callback_data="feed:next"),
            ],
            [InlineKeyboardButton(text="🤝 Начать трейд", callback_data=f"trade:start:{trade_id}")],
        ]
    )


def exchange_collect(trade_id: int, has_profile_videos: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_profile_videos:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📁 Отправить видео из моей анкеты",
                    callback_data=f"trade:useprofile:{trade_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="❌ Отменить обмен", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_exchange(exchange_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔥", callback_data=f"rate:{exchange_id}:5"),
                InlineKeyboardButton(text="👍", callback_data=f"rate:{exchange_id}:4"),
                InlineKeyboardButton(text="😐", callback_data=f"rate:{exchange_id}:3"),
                InlineKeyboardButton(text="👎", callback_data=f"rate:{exchange_id}:1"),
            ],
            [InlineKeyboardButton(text="💬 Оставить комментарий", callback_data=f"comment:{exchange_id}")],
            [InlineKeyboardButton(text="🚨 Пожаловаться", callback_data=f"report:exchange:{exchange_id}")],
            [InlineKeyboardButton(text="🔍 Искать трейды", callback_data="feed:open")],
        ]
    )


REPORT_REASONS = {
    "theme": "❌ Некорректная тематика",
    "content": "🚫 Содержание трейда",
    "other": "📝 Другое",
}


def report_reasons(exchange_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"reason:{exchange_id}:{key}")]
        for key, title in REPORT_REASONS.items()
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium(link: str, user_premium: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="📤 Поделиться ссылкой",
                url=f"https://t.me/share/url?url={link}&text="
                "🌸 Обменивайся видео-контентом в SakuraExchangeBot",
            )
        ]
    ]
    # 4 тарифных кнопки (1д/7д/30д/навсегда), если премиума ещё нет
    if not user_premium:
        for tier in PREMIUM_TIERS:
            if tier.stars > 0:
                forever = " (навсегда)" if tier.hours == 0 else ""
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=f"⭐️ Купить {tier.label}{forever} — {tier.stars}",
                            callback_data=f"premium:buy:{tier.id}",
                        )
                    ]
                )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def go_premium() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="👑 Открыть премиум", callback_data="premium:open")]]
    )


def admin_report(report_id: int, target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔨 Забанить", callback_data=f"adm:ban:{report_id}:{target_id}"),
                InlineKeyboardButton(
                    text="✅ Отклонить", callback_data=f"adm:dismiss:{report_id}:{target_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🙈 Скрыть анкету", callback_data=f"adm:hide:{report_id}:{target_id}"
                ),
                InlineKeyboardButton(
                    text="☑️ Верифицировать", callback_data=f"adm:verify:{report_id}:{target_id}"
                ),
            ],
        ]
    )
