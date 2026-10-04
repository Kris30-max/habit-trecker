START = (
    "Привет, {name}! 👋\n\n"
    "Я трекер привычек: напомню о них, отмечу выполнение "
    "и покажу, сколько дней подряд ты держишься.\n\n"
    "Начни с /add — добавь первую привычку."
)

HELP = (
    "<b>Что я умею</b>\n\n"
    "/today — привычки на сегодня и отметки\n"
    "/add — добавить привычку\n"
    "/stats — серии и прогресс\n"
    "/list — все привычки\n"
    "/edit — изменить привычку\n"
    "/delete — убрать привычку в архив\n"
    "/settings — часовой пояс, напоминания, вечерняя сводка\n"
    "/cancel — прервать текущее действие\n"
    "/help — эта справка"
)

CANCELLED = "Отменено."
NOTHING_TO_CANCEL = "Нечего отменять 🙂"
STALE_BUTTON = "Эта кнопка устарела"
HABIT_NOT_FOUND = "Привычка не найдена"

# /add
ADD_ASK_TITLE = "Как называется привычка? Например: <i>Читать 20 минут</i>\n\n/cancel — отмена"
ADD_BAD_TITLE = "Название должно быть от 1 до {max_len} символов. Попробуй ещё раз."
ADD_ASK_DAYS = "<b>{title}</b>\n\nВ какие дни? Отметь нужные и нажми «Готово»."
ADD_NO_DAYS = "Выбери хотя бы один день"
ADD_DAYS_CHOSEN = "<b>{title}</b>\nДни: {days}"
ADD_ASK_TIME = "Во сколько напоминать? Напиши время, например <i>21:00</i>."
ADD_BAD_TIME = "Не понял время. Напиши в формате ЧЧ:ММ, например <i>07:30</i>."
ADD_DONE = "✅ Привычка <b>{title}</b> добавлена.\n{days} · {reminder}\n\nОтмечать — в /today"

REMINDER_AT = "🔔 {time}"
REMINDER_OFF = "🔕 без напоминания"

# /today
DAY_HEADER_TODAY = "📅 <b>Сегодня, {date}</b>"
DAY_HEADER_YESTERDAY = "📅 <b>Вчера, {date}</b>"
DAY_EMPTY = "На этот день привычек нет. Добавить — /add"
DAY_PROGRESS = "Выполнено {done} из {total}"
DAY_ALL_DONE = "🎉 Всё выполнено!"
MARK_TOO_LATE = "Отметить можно только сегодня или вчера"
MARKED_DONE = "✅ Отмечено"
MARKED_DONE_STREAK = "✅ Отмечено! Серия: {days} 🔥"
MARKED_SKIPPED = "⏭ Пропущено"
MARK_REMOVED = "↩️ Отметка снята"

# /list, /delete
LIST_EMPTY = "Пока нет привычек. Добавить — /add"
LIST_HEADER = "📋 <b>Твои привычки</b>"
LIST_ITEM = "{n}. <b>{title}</b>\n     {days} · {reminder}"
DELETE_ASK = "Какую привычку убрать в архив?"
DELETE_CONFIRM = "Убрать <b>{title}</b> в архив? История отметок сохранится."
DELETE_DONE = "🗄 <b>{title}</b> в архиве."

# /edit
EDIT_ASK_HABIT = "Какую привычку изменить?"
EDIT_ASK_FIELD = "<b>{title}</b>\n{days} · {reminder}\n\nЧто меняем?"
EDIT_ASK_TITLE = "Новое название для <b>{title}</b>:\n\n/cancel — отмена"
EDIT_ASK_DAYS = "<b>{title}</b>\n\nВ какие дни? Отметь нужные и нажми «Готово»."
EDIT_ASK_TIME = "Новое время напоминания для <b>{title}</b>, например <i>21:00</i>:"
EDIT_SAVED = "✏️ Сохранено: <b>{title}</b>\n{days} · {reminder}"

# /settings
SETTINGS = (
    "⚙️ <b>Настройки</b>\n\n"
    "Часовой пояс: <b>{tz}</b> (сейчас {now})\n"
    "Напоминания: {reminders}\n"
    "Вечерняя сводка: {summary}"
)
SETTINGS_ON = "включены"
SETTINGS_OFF = "выключены"
SETTINGS_SUMMARY_OFF = "выключена"
SETTINGS_ASK_SUMMARY = (
    "Во сколько присылать итоги дня? Напиши время, например <i>21:30</i>.\n\n/cancel — отмена"
)
SETTINGS_ASK_TZ = (
    "Выбери часовой пояс или напиши его название, например <i>Asia/Almaty</i>.\n\n/cancel — отмена"
)
SETTINGS_BAD_TZ = "Не знаю такой часовой пояс. Пример: <i>Asia/Almaty</i>."
SETTINGS_SAVED = "✅ Сохранено"

# Напоминания (тикер)
REMINDER = "🔔 Пора: <b>{title}</b>"
REMINDER_STREAK = "Серия: {days} 🔥 Не прерывай!"
REMINDER_DONE = "✅ <b>{title}</b> — сделано!"
REMINDER_DONE_STREAK = "✅ <b>{title}</b> — сделано! Серия: {days} 🔥"
REMINDER_SKIPPED = "⏭ <b>{title}</b> — пропущено."
SNOOZED = "⏰ <b>{title}</b> — напомню в {time}."
SNOOZE_TOO_LATE = "Отложить можно только сегодняшнее напоминание"
SUMMARY_HEADER = "🌙 <b>Итоги дня</b>"

# /stats
STATS_HEADER = "📊 <b>Прогресс</b>"
STATS_STREAK = "🔥 Серия: {current} · рекорд: {best}"
STATS_NO_STREAK = "Серии пока нет · рекорд: {best}"
STATS_MONTH = "30 дн. {bar} {percent}% ({done}/{planned})"
STATS_WEEK = "7 дн.  {strip}"
STATS_NO_DATA = "30 дн. — пока нет данных"
STATS_LEGEND = "✅ сделано · ⏭ пропущено · ❌ не отмечено · ⬜️ сегодня · ▫️ не запланировано"
