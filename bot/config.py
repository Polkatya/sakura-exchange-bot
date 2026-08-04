import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "да"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return [int(part) for part in raw.replace(" ", "").split(",") if part]


@dataclass(frozen=True)
class PremiumTier:
    id: str
    label: str
    stars: int
    hours: int  # 0 = навсегда


PREMIUM_TIERS: list[PremiumTier] = [
    PremiumTier(id="1d", label="1 день", stars=15, hours=24),
    PremiumTier(id="7d", label="7 дней", stars=90, hours=7 * 24),
    PremiumTier(id="30d", label="30 дней", stars=300, hours=30 * 24),
    PremiumTier(id="forever", label="Навсегда", stars=999, hours=0),
]


@dataclass(frozen=True)
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: list[int] = field(default_factory=_admin_ids)
    db_path: str = os.getenv("DB_PATH", "sakura.db")
    videos_per_trade: int = _int("VIDEOS_PER_TRADE", 5)
    premium_referrals_required: int = _int("PREMIUM_REFERRALS_REQUIRED", 5)
    boost_hours_per_referral: int = _int("BOOST_HOURS_PER_REFERRAL", 1)
    search_requires_premium: bool = _bool("SEARCH_REQUIRES_PREMIUM", False)
    # Старое поле оставлено для совместимости; реальная цена теперь в PREMIUM_TIERS.
    premium_stars_price: int = _int("PREMIUM_STARS_PRICE", 150)
    repeat_trade_cooldown_hours: int = _int("REPEAT_TRADE_COOLDOWN_HOURS", 24)

    # Лимит трейдов: по умолчанию 5 обменов. За каждого приглашённого +1 к лимиту навсегда.
    base_trade_limit: int = _int("BASE_TRADE_LIMIT", 5)
    trade_limit_bonus_per_referral: int = _int("TRADE_LIMIT_BONUS_PER_REFERRAL", 1)
    # Премиум снимает лимит трейдов.


config = Config()
