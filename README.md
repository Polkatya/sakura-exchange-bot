# 🌸 SakuraExchangeBot

Телеграм-бот для обмена видео-контентом: анкеты («трейды»), лента, обмен 5×5,
рейтинг, комментарии, жалобы админу, премиум по рефералам и Telegram Stars.

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# впиши BOT_TOKEN от @BotFather и свой ADMIN_IDS (id можно узнать у @userinfobot)

python main.py
```

Проверка логики без Telegram (моки API, ничего не шлёт в сеть):

```bash
python tests/test_flow.py
```

## Как работает бот

| Экран | Что происходит |
|---|---|
| `/start` | Правила + кнопка «✅ Согласен с правилами» |
| Меню | 👤 Мой трейд · 👑 Премиум · 🔍 Искать трейды · ➕ Создать трейд · ❓ Помощь |
| Создание | 3 шага: что предлагаешь → 5 видео → что ищешь |
| Мой трейд | Анкета + видео, редактирование текста/видео, скрытие из ленты |
| Лента | Карточка анкеты, ⬅️ 🏠 ➡️, 🚨 жалоба, 🤝 начать трейд |
| Обмен | Кидаешь 5 видео (или берёшь их из анкеты) → мгновенный swap |
| После обмена | 🔥👍😐👎 оценка, 💬 комментарий собеседнику, 🚨 жалоба |
| Премиум | Рефералка: 5 друзей = навсегда, 1 друг = +1 ч буста анкеты. Плюс оплата ⭐️ |

Анкеты с активным бустом всегда показываются выше остальных.

## Премиум

- Реф-ссылка вида `t.me/<bot>?start=ref_<id>`, реферал засчитывается после принятия правил.
- `PREMIUM_REFERRALS_REQUIRED` друзей → премиум навсегда.
- Каждый друг → `BOOST_HOURS_PER_REFERRAL` часов буста (буст суммируется).
- `SEARCH_REQUIRES_PREMIUM=false` (по умолчанию): поиск открыт всем, премиум нужен для
  стрелки ⬅️ «назад» в ленте. Поставь `true` — и премиум будет закрывать весь поиск.
- `PREMIUM_STARS_PRICE` — цена премиума в Telegram Stars, `0` отключает продажу.

## Жалобы и модерация

Жалобы уходят всем `ADMIN_IDS` вместе с видео и кнопками:
🔨 Забанить · ✅ Отклонить · 🙈 Скрыть анкету · ☑️ Верифицировать.

Команды админа: `/admin`, `/stats`, `/user <id>`, `/ban <id> [причина]`, `/unban <id>`,
`/verify <id>`, `/unverify <id>`, `/grant <id>`, `/boost <id> <часов>`, `/broadcast <текст>`.

## Структура

```
main.py              запуск, роутеры, команды меню
bot/config.py        настройки из .env
bot/db.py            SQLite: users, trades, trade_videos, exchanges, reports, ratings, comments
bot/texts.py         все тексты и оформление
bot/keyboards.py     клавиатуры
bot/middlewares.py   бан-чек и «сначала прими правила»
bot/handlers/        common · create · my_trade · browse · exchange · reports · premium · admin
tests/               моки Telegram API + сквозной прогон сценариев
```

Видео нигде не скачиваются: бот хранит только `file_id` и пересылает их между
пользователями.

## Деплой на сервер (systemd)

```ini
[Unit]
Description=SakuraExchangeBot
After=network.target

[Service]
WorkingDirectory=/opt/sakura-exchange-bot
ExecStart=/opt/sakura-exchange-bot/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now sakura
journalctl -u sakura -f
```
