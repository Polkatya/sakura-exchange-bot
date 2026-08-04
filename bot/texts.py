"""Все тексты бота в одном месте — удобно править, не трогая логику."""

from __future__ import annotations

import random
from html import escape

from .config import config

N = config.videos_per_trade

RULES = (
    "🌸 <b>SakuraExchangeBot</b>\n"
    "<i>Бот для обмена видео-контентом</i>\n\n"
    "⚠️ <b>Перед использованием ознакомьтесь с правилами:</b>\n\n"
    "🚫 <b>Строго запрещено:</b>\n"
    "• CP / ДП и любой незаконный контент\n"
    "• Любой контент с несовершеннолетними\n"
    "• Насилие, шантаж, вымогательство\n"
    "• Слив личных данных и чужих архивов\n\n"
    "⛔ <b>Нарушение = перманентный бан.</b>\n"
    "📩 На аккаунт нарушителя будут поданы жалобы в Telegram и переданы "
    "все данные об обмене.\n\n"
    "👇 Нажимая кнопку ниже, вы подтверждаете, что вам есть 18 лет "
    "и вы согласны с правилами."
)

AGREED = (
    "✅ <b>Понял, принято!</b>\n\n"
    "🌸 Добро пожаловать в <b>SakuraExchange</b>\n"
    "Выберите действие в меню ниже 👇"
)

NEED_TRADE = (
    "🙅 <b>Сначала создайте трейд</b>\n\n"
    "Без своей анкеты нельзя смотреть чужие и обмениваться.\n"
    "Нажмите ➕ <b>Создать трейд</b>"
)

CREATE_STEP1 = (
    "📝 <b>Шаг 1 из 3</b>\n\n"
    "<b>Что вы предлагаете?</b>\n"
    "<i>Например: хентай, милфы, 2D...</i>\n\n"
    "✍️ Напишите одним сообщением."
)


def create_step2(count: int = 0) -> str:
    return (
        "🎬 <b>Шаг 2 из 3</b>\n\n"
        f"Отправьте <b>{N} видео</b> по вашей тематике.\n"
        "<i>Можно по одному или пачкой.</i>\n\n"
        f"📎 Отправлено: <b>{count} / {N}</b>\n"
        f"{progress_bar(count, N)}"
    )


CREATE_STEP3 = (
    "🔎 <b>Шаг 3 из 3</b>\n\n"
    "<b>Что вы ищете?</b>\n"
    "<i>Например: азиатки, 2D, аниме...</i>\n\n"
    "✍️ Напишите одним сообщением."
)

ONLY_VIDEO = "❌ Это не видео.\n🎬 Отправьте именно <b>видео</b> (не фото, не файл-документ, не ссылку)."

CANCELLED = "❌ Отменено. Вы в главном меню."

PREMIUM_LOCKED_BACK = (
    "🔒 <b>Стрелка «назад» — премиум-функция</b>\n\n"
    f"👥 Пригласите <b>{config.premium_referrals_required} друзей</b>, "
    "и она откроется <b>навсегда</b>.\n"
    f"🚀 Бонусом: за каждого друга +{config.boost_hours_per_referral} ч буста анкеты.\n\n"
    "👑 Подробности — в разделе «Премиум»."
)

PREMIUM_LOCKED_SEARCH = (
    "🔒 <b>«Искать трейды» — премиум-функция</b>\n\n"
    f"👥 Пригласите <b>{config.premium_referrals_required} друзей</b>, "
    "и поиск откроется <b>навсегда</b>.\n"
    f"🚀 Бонусом: за каждого друга +{config.boost_hours_per_referral} ч буста анкеты.\n\n"
    "👑 Подробности — в разделе «Премиум»."
)

FEED_EMPTY = (
    "😴 <b>Пока пусто</b>\n\n"
    "Новых анкет нет. Загляните позже — база растёт каждый день.\n"
    "💡 Совет: поднимите свою анкету бустом, чтобы вас нашли первыми."
)

FEED_SKIPPED = "⏭ Пропущено"

COMMENT_ASK = (
    "💬 <b>Напишите комментарий собеседнику</b>\n"
    "<i>Он придёт под вашим псевдонимом, ник не раскроется.</i>\n\n"
    "✍️ Одним сообщением, или /cancel чтобы отменить."
)

REPORT_ASK_REASON = "🚨 <b>За что жалоба?</b>\nВыберите причину:"

REPORT_ASK_TEXT = (
    "📝 <b>Опишите проблему</b>\n"
    "<i>Что именно не так? Чем подробнее — тем быстрее разберёмся.</i>\n\n"
    "✍️ Напишите одним сообщением или /cancel."
)

REPORT_SENT = (
    "✅ <b>Жалоба отправлена администрации</b>\n"
    "🕵️ Мы проверим содержание и примем меры.\n"
    "Спасибо, что бережёте бота 🌸"
)

TIPS = [
    "Чем точнее тематика в анкете — тем больше нормальных трейдов.",
    "Видео с обложкой-превью открывают чаще. Не грузите чёрные экраны.",
    f"Буст поднимает анкету выше всех — {config.boost_hours_per_referral} ч за каждого друга.",
    "Высокий рейтинг 🔥 = вам чаще предлагают обмен.",
    "Нашли запрещённый контент — жмите 🚨. Бан прилетает моментально.",
    "Можно заменить видео только для одного обмена — анкета не изменится.",
    "Обновляйте анкету: свежие анкеты поднимаются в ленте.",
]


def tip() -> str:
    return f"💡 <i>{escape(random.choice(TIPS))}</i>"


def progress_bar(done: int, total: int) -> str:
    done = max(0, min(done, total))
    return "🟪" * done + "⬜️" * (total - done)


def rating_line(avg: float, count: int) -> str:
    if not count:
        return "⭐️ Рейтинг: <i>пока нет оценок</i>"
    if avg >= 4.5:
        emoji = "🔥"
    elif avg >= 3.5:
        emoji = "👍"
    elif avg >= 2.5:
        emoji = "😐"
    else:
        emoji = "👎"
    return f"{emoji} Рейтинг: <b>{avg:.1f}/5</b> ({count})"


def anon_code(user_id: int) -> str:
    """Короткий псевдоним вместо @ника — один и тот же для одного человека."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    value = (user_id * 2654435761) % (len(alphabet) ** 4)
    code = ""
    for _ in range(4):
        value, rest = divmod(value, len(alphabet))
        code = alphabet[rest] + code
    return code


def user_title(user: dict) -> str:
    """Анонимное имя для обычных экранов: @ники никому не показываем."""
    title = f"Аноним #{anon_code(user['user_id'])}"
    if user.get("verified"):
        title += " ✅"
    return title


def admin_user_title(user: dict) -> str:
    """Для админских сообщений: псевдоним + реальный контакт."""
    name = user.get("username")
    contact = f"@{escape(name)}" if name else escape(user.get("full_name") or "без ника")
    return f"{user_title(user)} — {contact}"


def trade_created(offer: str, want: str, videos: int) -> str:
    return (
        "✅ <b>Отлично! Трейд создан!</b>\n\n"
        f"📦 <b>Предлагаете:</b> {escape(offer)}\n"
        f"🔍 <b>Ищете:</b> {escape(want)}\n"
        f"🎬 <b>Видео:</b> {videos} шт.\n\n"
        "🌸 Теперь другие могут найти ваш трейд!\n\n" + tip()
    )


def my_trade(trade: dict, user: dict, videos: int, avg: float, ratings: int) -> str:
    return (
        f"🌸 <b>Ваш трейд</b> #{trade['id']}\n\n"
        f"👤 Ваш псевдоним: {user_title(user)}\n"
        f"📦 <b>Предлагаете:</b> {escape(trade['offer'])}\n"
        f"🔍 <b>Ищете:</b> {escape(trade['want'])}\n"
        f"🎬 <b>Видео:</b> {videos} шт.\n"
        f"🤝 <b>Обменов:</b> {user['trades_done']}\n"
        f"{rating_line(avg, ratings)}\n"
        f"{boost_line(user)}"
    )


def feed_card(trade: dict, owner: dict, videos: int, avg: float, ratings: int, pos: int, total: int) -> str:
    boosted = "🚀 <b>BOOST</b>\n" if is_boosted(owner) else ""
    return (
        f"{boosted}🌸 <b>Трейд #{trade['id']}</b>\n\n"
        f"👤 {user_title(owner)}\n"
        f"📦 <b>Предлагает:</b> {escape(trade['offer'])}\n"
        f"🔍 <b>Ищет:</b> {escape(trade['want'])}\n"
        f"🎬 <b>Видео:</b> {videos} шт. <i>(откроются после обмена)</i>\n"
        f"🤝 <b>Обменов:</b> {owner['trades_done']}\n"
        f"{rating_line(avg, ratings)}\n\n"
        f"🔒 Видео прилетят автоматом, как только скинете свои {N}.\n"
        f"📄 Анкета {pos} из {total}"
    )


def exchange_intro(theme: str, count: int = 0) -> str:
    return (
        "🤝 <b>Начинаем обмен!</b>\n\n"
        f"📋 <b>Тематика анкеты:</b> {escape(theme)}\n\n"
        "💡 Если ваши текущие видео в анкете не подходят под эту тематику — "
        "можете заменить их <b>только для этого обмена</b>. Анкета не изменится.\n\n"
        f"🎬 Отправьте <b>{N} видео</b> для обмена:\n"
        f"📎 Отправлено: <b>{count} / {N}</b>\n"
        f"{progress_bar(count, N)}"
    )


def exchange_done_for_initiator(partner: dict, exchange_id: int) -> str:
    return (
        "✅ <b>Обмен завершён!</b>\n\n"
        f"🎬 Вы получили {N} видео от {user_title(partner)}\n"
        f"🆔 Обмен #{exchange_id}\n\n"
        "⭐️ Оцените обмен и оставьте комментарий 👇"
    )


def exchange_done_for_partner(initiator: dict, exchange_id: int) -> str:
    return (
        "🎉 <b>С вами обменялись!</b>\n\n"
        f"🎬 Вы получили {N} видео от {user_title(initiator)}\n"
        f"🆔 Обмен #{exchange_id}\n\n"
        "⭐️ Оцените обмен и оставьте комментарий 👇"
    )


def comment_delivered(from_user: dict, text: str) -> str:
    return f"💬 <b>Комментарий после обмена:</b>\n\n«{escape(text)}»\n\n— от {user_title(from_user)}"


def is_boosted(user: dict) -> bool:
    from .db import now

    return user["boost_until"] > now()


def boost_left(user: dict) -> str:
    from .db import now

    left = user["boost_until"] - now()
    if left <= 0:
        return "нет"
    hours, minutes = divmod(left // 60, 60)
    return f"{hours} ч {minutes} мин" if hours else f"{minutes} мин"


def boost_line(user: dict) -> str:
    return f"🚀 Буст: <b>{boost_left(user)}</b>" if is_boosted(user) else "🚀 Буст: <i>не активен</i>"


def premium(user: dict, link: str) -> str:
    from .config import PREMIUM_TIERS
    from .db import now

    need = config.premium_referrals_required
    have = min(user["referrals"], need)
    until_ts = int(user.get("premium_until") or 0)
    is_forever = bool(user["premium"]) and until_ts == 0
    is_temp = bool(user["premium"]) and until_ts > 0 and until_ts > now()

    if is_forever:
        status = "👑 <b>Статус: ПРЕМИУМ НАВСЕГДА</b>"
    elif is_temp:
        left_s = max(0, until_ts - now())
        h, rem = divmod(left_s // 60, 60)
        d, h = divmod(h, 24)
        left_txt = f"{d} д {h} ч" if d else f"{h} ч {rem} мин" if h else f"{rem} мин"
        status = f"👑 <b>Статус: ПРЕМИУМ активен</b>\n⏳ Осталось: <b>{left_txt}</b>"
    else:
        status = "🔒 <b>Статус: обычный</b>"

    locked = "«Искать трейды»" if config.search_requires_premium else "стрелка «назад» ⬅️ в ленте"

    tiers_block = "\n".join(
        f"⭐️ <b>{t.stars}</b> — {t.label}" for t in PREMIUM_TIERS
    )

    stars = (
        f"\n\n💰 <b>Тарифы премиума (оплата звёздами Telegram):</b>\n{tiers_block}\n"
        if not is_forever and not is_temp else ""
    )

    referral = (
        "🔒 Премиум-функция — стрелка «назад» ⬅️ в ленте (и поиск, если включён).\n\n"
        if not is_forever and not is_temp else ""
    )

    return (
        "👑 <b>Премиум SakuraExchangeBot</b>\n\n"
        f"{status}\n\n"
        f"{referral}"
        f"👥 Пригласите <b>{need} друзей</b> — откроется <b>навсегда</b>\n"
        f"🚀 За каждого друга +{config.boost_hours_per_referral} ч буста: "
        "ваша анкета показывается <b>ВЫШЕ всех</b>\n"
        "♾ С премиумом — безлимитные обмены (лимит трейдов снимается)\n\n"
        f"📊 <b>Ваш прогресс:</b> {have} / {need}\n"
        f"{progress_bar(have, need)}\n"
        f"{boost_line(user)}"
        f"{stars}\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{escape(link)}</code>"
    )


def report_profile_admin(reporter: dict, target: dict, trade: dict, report_id: int) -> str:
    return (
        f"🚨 <b>ЖАЛОБА НА АНКЕТУ</b> #{report_id}\n\n"
        f"👤 <b>От:</b> {admin_user_title(reporter)} (<code>{reporter['user_id']}</code>)\n"
        f"🎯 <b>На:</b> {admin_user_title(target)} (<code>{target['user_id']}</code>)\n\n"
        f"🆔 Трейд #{trade['id']}\n"
        f"📦 <b>Предлагает:</b> {escape(trade['offer'])}\n"
        f"🔍 <b>Ищет:</b> {escape(trade['want'])}"
    )


def report_exchange_admin(
    reporter: dict, target: dict, reason: str, comment: str | None, exchange_id: int, report_id: int
) -> str:
    extra = f"\n📝 <b>Комментарий:</b> {escape(comment)}" if comment else ""
    return (
        f"🚨 <b>ЖАЛОБА ПОСЛЕ ТРЕЙДА</b> #{report_id}\n\n"
        f"❗️ <b>Тип:</b> {escape(reason)}{extra}\n\n"
        f"👤 <b>От:</b> {admin_user_title(reporter)} (<code>{reporter['user_id']}</code>)\n"
        f"🎯 <b>На:</b> {admin_user_title(target)} (<code>{target['user_id']}</code>)\n"
        f"🆔 <b>Обмен #{exchange_id}</b>"
    )


def forbidden_words_error(found: list[str]) -> str:
    words = ", ".join(f"<code>{escape(w)}</code>" for w in found)
    return (
        "🚫 <b>В тексте обнаружены запрещённые слова!</b>\n\n"
        f"Найдено: {words}\n\n"
        "⚠️ Анкета не может быть создана/обновлена.\n"
        "Пожалуйста, уберите эти слова и напишите заново.\n\n"
        "<i>Помните: CP/ДП, несовершеннолетние, насилие и "
        "другой незаконный контент = перманентный бан.</i>"
    )


def trade_limit_reached(done: int, limit: int) -> str:
    return (
        "⛔️ <b>Лимит трейдов превышен!</b>\n\n"
        f"Сделано обменов: <b>{done} / {limit}</b>\n\n"
        "💡 <b>Как увеличить лимит:</b>\n"
        "• 👥 Пригласите <b>1 человека</b> по своей реферальной ссылке — "
        "лимит <b>навсегда</b> повысится на +1 трейд.\n"
        "• 👑 Купите Премиум — ограничение снимается полностью.\n\n"
        "Хватит копить — поделитесь ботом с друзьями! 🌸"
    )
