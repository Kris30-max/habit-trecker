# TECH_SPEC — техническая спецификация Habit Tracker Bot

Документ описывает, **как** реализуется проект. Что и зачем делаем — в
[PROJECT_IDEA.md](PROJECT_IDEA.md), краткая памятка — в [CLAUDE.md](CLAUDE.md).

---

## 1. Инфраструктура

```
 ┌──────────────┐  git push main  ┌──────────────────┐  autodeploy  ┌─────────────────────────┐
 │  Разработчик │ ──────────────► │ GitHub           │ ───────────► │ Railway                 │
 │  (локально)  │                 │ Kris30-max/      │  (после CI)  │ сервис "bot" (Docker)   │
 └──────────────┘                 │ habit-trecker    │              │ 1 реплика, long polling │
                                  │ + GitHub Actions │              └───────┬─────────┬───────┘
                                  └──────────────────┘                      │         │
                                                         getUpdates / send  │         │ SQL (asyncpg)
                                                                            ▼         ▼
                                                              ┌──────────────┐  ┌──────────────────────┐
                                                              │ Telegram     │  │ Supabase Postgres    │
                                                              │ Bot API      │  │ (Session pooler,     │
                                                              └──────────────┘  │  IPv4, порт 5432)    │
                                                                                └──────────────────────┘
```

| Компонент | Сервис | Роль |
|---|---|---|
| Код | GitHub `Kris30-max/habit-trecker` (публичный!) | Хранение кода, PR, CI (GitHub Actions) |
| Хостинг | Railway | Сборка Docker-образа и запуск бота 24/7, автодеплой из `main` |
| БД | Supabase (Postgres) | Постоянное хранение пользователей, привычек, отметок |
| Мессенджер | Telegram Bot API | Получение апдейтов (long polling), отправка сообщений |

### 1.1 Почему так

- **Supabase вместо SQLite.** Файловая система контейнера Railway эфемерна:
  при каждом деплое SQLite-файл пропадает. Postgres в Supabase — бесплатно,
  с веб-интерфейсом для просмотра данных.
- **Прямое подключение к Postgres, а не Supabase REST API.** Бот — серверный
  процесс, ему нужны транзакции, миграции и ORM. Ключи `anon`/`service_role`
  боту **не нужны**; нужен только `DATABASE_URL`.
- **Session pooler (порт 5432), а не direct connection.** Прямое подключение
  Supabase работает только по IPv6, Railway исходящий IPv6 не гарантирует.
  Session pooler доступен по IPv4 и совместим с prepared statements asyncpg.
- **Long polling, а не webhook.** Не нужен публичный домен, HTTPS и секрет
  вебхука; для одного пользователя нагрузка ничтожная. Переход на webhook
  возможен позже без изменения бизнес-логики.
- **Свой планировщик-тикер вместо APScheduler.** Расписание целиком лежит в БД;
  раз в минуту бот сам смотрит, кому что пора отправить. Рестарт или передеплой
  не теряет напоминаний — нет состояния в памяти, которое надо восстанавливать.

## 2. Стек

| Слой | Технология | Версия |
|---|---|---|
| Язык | Python | 3.12 |
| Бот-фреймворк | aiogram | 3.x |
| ORM | SQLAlchemy (async) | 2.x |
| Драйвер БД | asyncpg (prod), aiosqlite (тесты) | — |
| Миграции | Alembic | 1.x |
| Конфиг | pydantic-settings | 2.x |
| Часовые пояса | `zoneinfo` (stdlib) + `tzdata` | — |
| Тесты | pytest, pytest-asyncio | — |
| Линт/формат | ruff | — |
| Контейнер | Docker, `python:3.12-slim` | — |

## 3. Архитектура приложения

Один процесс, один event loop, две конкурентные задачи:

1. **Dispatcher aiogram** — long polling, обработка команд и нажатий кнопок.
2. **Ticker** — `asyncio`-цикл раз в `TICK_SECONDS` (60 с): напоминания,
   отложенные напоминания, вечерние сводки.

Слои (зависимости направлены только вниз):

```
handlers/ ──► services/ ──► db/repositories ──► db/models
   │              ▲
keyboards/    scheduler/ticker
states/
middlewares/
```

- **handlers** — только Telegram: разбор апдейта, вызов сервиса, ответ.
- **services** — чистая бизнес-логика (серии, статистика, расписание).
  Функции подсчёта серий/статистики — **чистые**, без БД, легко тестируются.
- **db** — модели, фабрика сессий, репозитории (единственное место с SQL).
- **middlewares** — `AccessMiddleware` (whitelist), `DbSessionMiddleware`
  (сессия на апдейт, commit/rollback), `UserMiddleware` (get-or-create user).

### 3.1 Структура репозитория

```
habit-trecker/
├── bot/
│   ├── __main__.py           # сборка Bot/Dispatcher, запуск polling + ticker
│   ├── config.py             # Settings (pydantic-settings)
│   ├── texts.py              # все тексты бота
│   ├── handlers/             # start, habits_add, habits_list, today, stats, settings, callbacks
│   ├── keyboards/            # inline-клавиатуры + CallbackData-фабрики
│   ├── states/               # FSM: AddHabit, EditHabit, Settings
│   ├── services/             # habits.py, streaks.py, stats.py, schedule.py
│   ├── scheduler/ticker.py   # периодические задачи
│   ├── db/                   # base.py, models.py, session.py, repositories/
│   └── middlewares/          # access.py, db.py, user.py
├── migrations/               # Alembic (env.py async)
├── tests/                    # unit + интеграционные на SQLite in-memory
├── .github/workflows/ci.yml  # ruff + pytest
├── Dockerfile
├── railway.toml
├── alembic.ini
├── pyproject.toml
├── .env.example
├── CLAUDE.md · PROJECT_IDEA.md · TECH_SPEC.md
```

## 4. Модель данных (Postgres)

### `users`
| Поле | Тип | Примечание |
|---|---|---|
| id | bigserial PK | |
| telegram_id | bigint UNIQUE NOT NULL | |
| first_name | text | |
| timezone | text NOT NULL default `Asia/Almaty` | IANA-имя |
| summary_time | time NULL | время вечерней сводки, NULL = выкл |
| reminders_enabled | bool NOT NULL default true | |
| last_summary_on | date NULL | локальная дата последней сводки (идемпотентность) |
| created_at | timestamptz NOT NULL default now() | |

### `habits`
| Поле | Тип | Примечание |
|---|---|---|
| id | bigserial PK | |
| user_id | bigint FK → users ON DELETE CASCADE | |
| title | varchar(64) NOT NULL | |
| emoji | varchar(8) NULL | |
| schedule_days | smallint NOT NULL default 127 | битовая маска: бит 0 = пн … бит 6 = вс |
| remind_time | time NULL | локальное время; NULL = без напоминания |
| last_reminded_on | date NULL | локальная дата последнего напоминания |
| snoozed_until | timestamptz NULL | отложенное напоминание (UTC) |
| is_archived | bool NOT NULL default false | |
| created_at | timestamptz NOT NULL default now() | |

Индекс: `(user_id, is_archived)`.

### `habit_logs`
| Поле | Тип | Примечание |
|---|---|---|
| id | bigserial PK | |
| habit_id | bigint FK → habits ON DELETE CASCADE | |
| date | date NOT NULL | **локальная** дата пользователя |
| status | varchar(8) NOT NULL | `done` / `skipped` (CHECK) |
| created_at | timestamptz NOT NULL default now() | |

`UNIQUE (habit_id, date)`. Повторное нажатие — upsert (`ON CONFLICT DO UPDATE`),
так можно сменить «пропустил» на «сделал».

### Безопасность Supabase

Supabase автоматически публикует схему `public` через REST API, доступный по
`anon`-ключу. Поэтому первая миграция **включает RLS на всех таблицах без
политик** — REST-доступ закрыт, а бот, подключённый ролью `postgres`, RLS обходит.

### Правила времени

- Все `timestamptz` — в UTC.
- `date` в логах и `*_on` — локальная дата пользователя по его `timezone`.
- `remind_time`/`summary_time` — локальное «настенное» время.
- Перевод «сейчас» в локальное: `datetime.now(UTC).astimezone(ZoneInfo(tz))`.

## 5. Бизнес-логика

### 5.1 Расписание
`is_scheduled(habit, d) = habit.schedule_days & (1 << d.weekday()) != 0`
и `d >= habit.created_at` в локальной дате.

### 5.2 Серия (streak)
Идём назад от сегодняшнего дня по **запланированным** дням:
- `done` → +1, продолжаем;
- сегодня и отметки ещё нет → пропускаем (день не закончился, серию не рвёт);
- `skipped` или нет отметки за прошедший день → стоп.

Незапланированные дни пропускаются и серию не прерывают.
**Лучшая серия** — максимальный отрезок по всей истории тем же правилом.

### 5.3 Статистика за N дней (7 / 30)
`процент = done / запланированные_дни × 100`, где окно —
`[max(today − N + 1, дата создания), today]`; сегодняшний день входит
в знаменатель, только если по нему уже есть отметка.

### 5.4 Отметка выполнения
Кнопки несут `habit_id` и `date`. Разрешена отметка за **сегодня и вчера**
(поздно нажал на вчерашнее напоминание). Старше — ответ «слишком поздно».
Каждый callback проверяет, что привычка принадлежит текущему пользователю.

## 6. Планировщик (ticker)

Раз в 60 секунд, для каждого пользователя с `reminders_enabled`:

1. **Напоминания.** Привычки, у которых: не в архиве, запланированы на
   сегодня, `remind_time <= local_now`, `local_now − remind_time < 2 ч`
   (окно догоняющей отправки после простоя), нет лога за сегодня,
   `last_reminded_on <> today`.
2. **Отложенные.** `snoozed_until <= now_utc` → отправить, обнулить `snoozed_until`.
3. **Вечерняя сводка.** `summary_time <= local_now` и `last_summary_on <> today`.

**Идемпотентность:** перед отправкой выполняется условный
`UPDATE habits SET last_reminded_on = :today WHERE id = :id AND last_reminded_on IS DISTINCT FROM :today RETURNING id`.
Отправляем, только если строка вернулась. Так исключены дубли даже при
кратком перекрытии двух инстансов во время деплоя.

Ошибки отправки (`TelegramForbiddenError` — пользователь заблокировал бота)
логируются, у пользователя выключаются напоминания; остальные ошибки не
роняют тикер.

## 7. Интерфейс бота

| Команда | Хендлер | FSM |
|---|---|---|
| `/start` | регистрация, выбор часового пояса кнопками | — |
| `/add` | название → дни → время напоминания | `AddHabit` |
| `/list` | список + кнопки «✏️», «🗄 в архив» | — |
| `/today` | привычки на сегодня + «✅ / ⏭» | — |
| `/stats` | серии, % за 7/30 дней, мини-календарь 7 дней | — |
| `/edit` | выбор привычки → поле → новое значение | `EditHabit` |
| `/delete` | архивирование с подтверждением | — |
| `/settings` | часовой пояс, время сводки, вкл/выкл напоминаний | `Settings` |
| `/help` | справка | — |

Callback-фабрики: `HabitAction(action, habit_id, date)`, `DayToggle(mask)`,
`TzPick(tz)`. Команды регистрируются в меню через `bot.set_my_commands`.

## 8. Конфигурация

| Переменная | Где задаётся | Пример |
|---|---|---|
| `BOT_TOKEN` | Railway Variables, локально `.env` | `123:ABC…` |
| `ALLOWED_USER_IDS` | Railway / `.env` | `123456789` |
| `DATABASE_URL` | Railway / `.env` | `postgresql+asyncpg://postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:5432/postgres` |
| `DEFAULT_TZ` | Railway / `.env` | `Asia/Almaty` |
| `TICK_SECONDS` | опционально | `60` |
| `LOG_LEVEL` | опционально | `INFO` |

Ключи Supabase `anon` / `service_role` боту не нужны и в Railway не передаются.
Секреты **никогда** не попадают в репозиторий — он публичный.

## 9. Деплой и CI/CD

1. Работа в ветке `feature/*` → PR в `main`.
2. **GitHub Actions** (`ci.yml`): `ruff check`, `ruff format --check`, `pytest`.
3. Merge/push в `main` → Railway (включён «Wait for CI») собирает Dockerfile.
4. Старт контейнера: `alembic upgrade head && python -m bot`.
5. `railway.toml`: builder `DOCKERFILE`, `restartPolicyType = "ON_FAILURE"`,
   1 реплика (две реплики = конфликт `getUpdates`).
6. Логи — stdout в формате `время уровень логгер сообщение`, смотрим в Railway.

Корректное завершение: по SIGTERM останавливаем polling и тикер,
закрываем сессию бота и пул БД.

## 10. Тестирование

- **Unit:** `streaks.py`, `stats.py`, `schedule.py` — чистые функции;
  кейсы: незапланированные дни, сегодня без отметки, `skipped`, смена
  часового пояса, граница полуночи, привычка создана посреди недели.
- **Интеграционные:** репозитории и тикер на SQLite in-memory
  (модели переносимы, Postgres-специфика только в миграциях).
- Хендлеры — по необходимости, через моки `Bot`.
- Порог: вся логика серий/статистики/тикера покрыта тестами.

## 11. Наблюдаемость и эксплуатация

- Логи Railway; уровень `INFO`, отправки напоминаний — `INFO`, ошибки — `ERROR`.
- Бэкапы: на Free-плане Supabase нет автоматических бэкапов → еженедельный
  `pg_dump` через GitHub Action в приватный артефакт (этап 4).
- Пауза проекта: Free-проект Supabase засыпает после 7 дней без активности —
  бот ходит в БД каждую минуту, поэтому не уснёт.

## 12. Технические риски

| Риск | Мера |
|---|---|
| Утечка секретов в публичный репозиторий | `.env` в `.gitignore`, только `.env.example`; секреты в Railway Variables |
| Supabase direct connection не работает с Railway (IPv6) | Используем Session pooler (IPv4) |
| Дубли напоминаний при деплое | Условный UPDATE `last_reminded_on` (раздел 6) |
| Пропуск напоминаний при простое | Окно догоняющей отправки 2 ч |
| Ошибки часовых поясов | `zoneinfo`, локальные даты, тесты на полночь |
| Supabase REST открывает таблицы по anon-ключу | RLS на всех таблицах |
| Падение процесса | Railway restart policy ON_FAILURE |

## 13. Порядок реализации

1. **Каркас:** `pyproject.toml`, конфиг, `__main__`, `/start` `/help`,
   whitelist, Dockerfile, `railway.toml`, CI. Первый деплой на Railway.
2. **БД:** модели, Alembic, первая миграция с RLS, middlewares сессии/пользователя.
3. **Привычки:** `/add` (FSM), `/list`, `/today`, отметки, `/delete`.
4. **Логика:** `streaks.py`, `stats.py` + тесты, `/stats`.
5. **Тикер:** напоминания, «⏰ Через час», вечерняя сводка.
6. **Полировка:** `/edit`, `/settings`, тексты, бэкап-workflow.
