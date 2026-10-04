# CLAUDE.md — Habit Tracker Telegram Bot

Памятка для работы над проектом. Подробности:
[PROJECT_IDEA.md](PROJECT_IDEA.md) — что и зачем, [TECH_SPEC.md](TECH_SPEC.md) — как.

## Суть проекта

Telegram-бот с трекером привычек: следит за прогрессом правильных привычек,
напоминает о них, считает серии (streak) и показывает статистику.
Пользователь — я сам (личный проект), доступ ограничен белым списком.

- **Проблема:** привычки не отслеживаются и забываются.
- **Решение:** напоминания + отметка в один тап + наглядный прогресс.

## Инфраструктура

- **GitHub:** https://github.com/Kris30-max/habit-trecker — **публичный** репозиторий.
- **Railway:** автодеплой из `main` (после зелёного CI), Dockerfile, 1 реплика.
- **Supabase:** Postgres, подключение через **Session pooler** (IPv4, порт 5432).
- Long polling, без webhook. Свой тикер раз в минуту вместо APScheduler.

## Стек

Python 3.12 · aiogram 3 · SQLAlchemy 2 async + asyncpg · Alembic ·
pydantic-settings · zoneinfo · pytest + pytest-asyncio (SQLite in-memory) · ruff · Docker

## Структура

```
bot/
  __main__.py     запуск polling + ticker
  config.py       Settings
  texts.py        тексты бота
  handlers/       только Telegram-логика
  keyboards/      клавиатуры, CallbackData-фабрики
  states/         FSM
  services/       бизнес-логика: streaks, stats, schedule (чистые функции)
  scheduler/      ticker.py — напоминания, snooze, вечерняя сводка
  db/             models, session, repositories
  middlewares/    access (whitelist), db-сессия, user
migrations/       Alembic
tests/
```

## Модель данных

- `users`: telegram_id, timezone, summary_time, reminders_enabled, last_summary_on
- `habits`: user_id, title, emoji, schedule_days (маска, бит0=пн), remind_time,
  last_reminded_on, snoozed_until, is_archived
- `habit_logs`: habit_id, date (локальная), status `done`/`skipped`; unique(habit_id, date)

Серии не хранятся — считаются из логов. Незапланированный день серию не рвёт;
сегодня без отметки — не рвёт; `skipped` или пропущенный прошедший день — рвёт.

## Команды бота

`/start` `/add` `/list` `/today` `/stats` `/edit` `/delete` `/settings` `/help`

## Команды разработки

```bash
pip install -e ".[dev]"          # установка
python -m bot                    # запуск локально (нужен .env)
pytest                           # тесты
ruff check . && ruff format .    # линт и формат
alembic revision --autogenerate -m "msg"  # новая миграция
alembic upgrade head             # применить миграции
```

## Переменные окружения

`BOT_TOKEN`, `ALLOWED_USER_IDS`, `DATABASE_URL` (postgresql+asyncpg://… pooler),
`DEFAULT_TZ`, `TICK_SECONDS`, `LOG_LEVEL`. Шаблон — `.env.example`.
Локально — `.env`, в проде — Railway Variables. Ключи Supabase API боту не нужны.

## Правила кода

- **Никаких секретов в git** — репозиторий публичный. `.env` в `.gitignore`.
- Хендлеры тонкие: апдейт → сервис → ответ. SQL только в репозиториях.
- Время в БД — UTC; даты отметок — локальные по `user.timezone`.
- Тикер идемпотентен: условный UPDATE `last_reminded_on` перед отправкой.
- Callback проверяет, что привычка принадлежит пользователю.
- Новые таблицы — с RLS (Supabase отдаёт `public` через REST).
- Тексты — в `texts.py`, на русском, коротко.
- Тайп-хинты везде; логика серий/статистики/тикера — только с тестами.

## Git-процесс

Ветки `feature/*` → PR → `main` → CI → автодеплой Railway.
Перед коммитом: `ruff check`, `pytest`, проверить, что `.env` не в индексе.

## Текущий этап

Порядок реализации — TECH_SPEC.md, раздел 13. Сейчас: шаг 1 (каркас).
Функции из бэклога не трогаем, пока не закрыт MVP.
