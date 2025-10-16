import asyncio
import random
import json
import os
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

TOKEN = "MY_TOKEN_TELEGRAMM"

# ---------------------- Состояния ----------------------
STATE_START, STATE_TEXT, STATE_CALENDAR, STATE_HOUR, STATE_MINUTE, STATE_REPEAT = range(6)
STATE_SELECT_REMINDER, STATE_CONFIRM_STOP, STATE_TIMEZONE = range(6, 9)

# ---------------------- Файлы для хранения данных ----------------------
DATA_FILE = "user_data.json"
TIMEZONE_FILE = "user_timezones.json"

# ---------------------- Загрузка данных ----------------------
def load_data():
    """Загружает данные пользователей из файла"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
    return {}

def save_data():
    """Сохраняет данные пользователей в файл"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")

def load_timezones():
    """Загружает часовые пояса из файла"""
    if os.path.exists(TIMEZONE_FILE):
        try:
            with open(TIMEZONE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Преобразуем ключи обратно в int
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Ошибка загрузки часовых поясов: {e}")
    return {}

def save_timezones():
    """Сохраняет часовые пояса в файл"""
    try:
        with open(TIMEZONE_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_timezones, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения часовых поясов: {e}")

# ---------------------- Инициализация хранилищ ----------------------
user_data_store = load_data()
user_timezones = load_timezones()
scheduled_jobs = {}

# ---------------------- Часовые пояса России ----------------------
RUSSIAN_TIMEZONES = {
    'kaliningrad': ('Калининград (UTC+2)', 'Europe/Kaliningrad'),
    'moscow': ('Москва (UTC+3)', 'Europe/Moscow'),
    'samara': ('Самара (UTC+4)', 'Europe/Samara'),
    'yekaterinburg': ('Екатеринбург (UTC+5)', 'Asia/Yekaterinburg'),
    'omsk': ('Омск (UTC+6)', 'Asia/Omsk'),
    'krasnoyarsk': ('Красноярск (UTC+7)', 'Asia/Krasnoyarsk'),
    'irkutsk': ('Иркутск (UTC+8)', 'Asia/Irkutsk'),
    'yakutsk': ('Якутск (UTC+9)', 'Asia/Yakutsk'),
    'vladivostok': ('Владивосток (UTC+10)', 'Asia/Vladivostok'),
    'magadan': ('Магадан (UTC+11)', 'Asia/Magadan'),
    'kamchatka': ('Камчатка (UTC+12)', 'Asia/Kamchatka')
}

# ---------------------- Ссылки на изображения из альбома ----------------------
IMAGE_URLS = [
    "https://disk.yandex.ru/i/3Sjt2RqIUVAaCw",
    "https://disk.yandex.ru/i/gzKwRm4XKVGJ7g",
    "https://disk.yandex.ru/i/OT2qZd--RbREVQ",
    "https://disk.yandex.ru/i/CZCi-mCeVcuymA",
    "https://disk.yandex.ru/i/VQuABgUCarlpSw",
    "https://disk.yandex.ru/i/sUxKzgK4UhHvBg",
    "https://disk.yandex.ru/i/iOY8_iw5N8oOQA",
    "https://disk.yandex.ru/i/gSPXWv2HD5YSig",
    "https://disk.yandex.ru/i/EMygqNBOrY10Kw",
    "https://disk.yandex.ru/i/f9SttRwwTnEiSA",
    "https://disk.yandex.ru/i/wMjMhoOPUxuoNQ"
]

def get_random_image():
    return random.choice(IMAGE_URLS)

def get_user_timezone(user_id):
    """Возвращает часовой пояс пользователя или Москву по умолчанию"""
    return user_timezones.get(user_id, 'Europe/Moscow')

# ---------------------- Функция отправки основного напоминания ----------------------
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data["user_id"]
    reminder_text = job.data["text"]
    
    random_image = get_random_image()
    
    try:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=random_image,
            caption=f"Эт твоя напоминулька, ты хотель {reminder_text} прекрасного тебе денька💖"
        )
    except Exception as e:
        print(f"Ошибка отправки напоминания: {e}")

# ---------------------- Функция отправки скрытого напоминания ----------------------
async def send_hidden_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data["user_id"]
    reminder_text = job.data["text"]
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Ты сделаль? {reminder_text} 😼"
        )
    except Exception as e:
        print(f"Ошибка отправки скрытого напоминания: {e}")

# ---------------------- Функция планирования напоминания ----------------------
async def schedule_reminder(user_id, context: ContextTypes.DEFAULT_TYPE, reminder_data):
    try:
        reminder_text = reminder_data["text"]
        date_str = reminder_data["date"]
        hour = reminder_data["hour"]
        minute = reminder_data["minute"]
        repeat = reminder_data.get("repeat", "no_repeat")
        
        # Получаем часовой пояс пользователя
        user_tz = get_user_timezone(user_id)
        user_timezone = pytz.timezone(user_tz)
        
        # Создаем datetime в часовом поясе пользователя
        reminder_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        reminder_datetime_naive = datetime.combine(reminder_date, datetime.min.time()).replace(hour=hour, minute=minute)
        
        # Преобразуем в часовой пояс пользователя, затем в UTC
        reminder_datetime_user = user_timezone.localize(reminder_datetime_naive)
        reminder_datetime_utc = reminder_datetime_user.astimezone(pytz.UTC)
        
        # Время для скрытого напоминания (через 10 минут)
        hidden_reminder_datetime_utc = reminder_datetime_utc + timedelta(minutes=10)
        
        # Текущее время в UTC
        now_utc = datetime.now(pytz.UTC)
        
        print(f"Пользователь {user_id} установил: {hour}:{minute} в поясе {user_tz}")
        print(f"Это соответствует: {reminder_datetime_utc.strftime('%H:%M')} UTC")
        print(f"Скрытое напоминание: {hidden_reminder_datetime_utc.strftime('%H:%M')} UTC")
        
        # Если время уже прошло, корректируем
        if reminder_datetime_utc < now_utc:
            if repeat == "no_repeat":
                # Для неповторяющихся - отправляем через 10 секунд
                reminder_datetime_utc = now_utc + timedelta(seconds=10)
                hidden_reminder_datetime_utc = reminder_datetime_utc + timedelta(minutes=10)
            else:
                # Для повторяющихся - добавляем период
                if repeat == "daily":
                    reminder_datetime_utc += timedelta(days=1)
                    hidden_reminder_datetime_utc = reminder_datetime_utc + timedelta(minutes=10)
                elif repeat == "weekly":
                    reminder_datetime_utc += timedelta(weeks=1)
                    hidden_reminder_datetime_utc = reminder_datetime_utc + timedelta(minutes=10)
                elif repeat == "monthly":
                    reminder_datetime_utc += timedelta(days=30)
                    hidden_reminder_datetime_utc = reminder_datetime_utc + timedelta(minutes=10)
                elif repeat == "yearly":
                    reminder_datetime_utc += timedelta(days=365)
                    hidden_reminder_datetime_utc = reminder_datetime_utc + timedelta(minutes=10)
        
        # Создаем уникальные имена для задач
        job_name = f"reminder_{user_id}_{datetime.now().timestamp()}"
        hidden_job_name = f"hidden_reminder_{user_id}_{datetime.now().timestamp()}"
        
        # Планируем основное напоминание в UTC
        context.job_queue.run_once(
            send_reminder,
            when=reminder_datetime_utc,
            data={
                "user_id": user_id,
                "text": reminder_text
            },
            name=job_name
        )
        
        # Планируем скрытое напоминание через 10 минут
        context.job_queue.run_once(
            send_hidden_reminder,
            when=hidden_reminder_datetime_utc,
            data={
                "user_id": user_id,
                "text": reminder_text
            },
            name=hidden_job_name
        )
        
        # Сохраняем информацию о задачах
        if user_id not in scheduled_jobs:
            scheduled_jobs[user_id] = []
        scheduled_jobs[user_id].append({
            "job_name": job_name,
            "hidden_job_name": hidden_job_name,
            "text": reminder_text,
            "datetime": reminder_datetime_utc,
            "hidden_datetime": hidden_reminder_datetime_utc,
            "repeat": repeat
        })
        
        user_time = reminder_datetime_utc.astimezone(user_timezone)
        hidden_user_time = hidden_reminder_datetime_utc.astimezone(user_timezone)
        print(f"Основное напоминание запланировано на {user_time.strftime('%Y-%m-%d %H:%M')} в поясе {user_tz}")
        print(f"Скрытое напоминание запланировано на {hidden_user_time.strftime('%Y-%m-%d %H:%M')} в поясе {user_tz}")
        
        # Сохраняем данные после добавления напоминания
        save_data()
        
    except Exception as e:
        print(f"Ошибка планирования напоминания: {e}")

# ---------------------- Восстановление напоминаний при запуске ----------------------
def restore_reminders(application):
    """Восстанавливает все напоминания при запуске бота"""
    print("Восстановление напоминаний...")
    
    for user_id_str, reminders in user_data_store.items():
        user_id = int(user_id_str)
        for reminder in reminders:
            try:
                # Проверяем, есть ли все необходимые данные для планирования
                if all(key in reminder for key in ['text', 'date', 'hour', 'minute']):
                    # Создаем контекст для планирования
                    async def schedule_reminder_job(context):
                        await schedule_reminder(user_id, context, reminder)
                    
                    # Планируем задачу
                    application.job_queue.run_once(schedule_reminder_job, when=1)
                    print(f"Восстановлено напоминание для пользователя {user_id}: {reminder['text']}")
                else:
                    print(f"Неполные данные для напоминания пользователя {user_id}")
            except Exception as e:
                print(f"Ошибка восстановления напоминания для пользователя {user_id}: {e}")

# ---------------------- Старт ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Что напомнить?", callback_data="what")],
        [InlineKeyboardButton("Мои напоминалочки", callback_data="my_reminders")],
        [InlineKeyboardButton("Мой часовой пояс", callback_data="timezone")],
        [InlineKeyboardButton("Пообщаться со мной", callback_data="chat_with_me")],
        [InlineKeyboardButton("Поддержать автора", callback_data="support_author")],
        [InlineKeyboardButton("Остановить туть", callback_data="stop")]
    ]
    if update.message:
        await update.message.reply_text("Привет, котик!🐱 выбирай, что делаем:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        query = update.callback_query
        try:
            await query.answer()
        except:
            pass
        await query.edit_message_text("Привет, котик!🐱 выбирай, что делаем:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_START

# ---------------------- Обработка кнопок ----------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass

    user_id = query.from_user.id
    data = query.data

    # ---------------- Начальные действия ----------------
    if data == "what":
        keyboard = [[InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")]]
        await query.edit_message_text("Введи, что напомнить:", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_TEXT

    elif data == "my_reminders":
        reminders = user_data_store.get(str(user_id), [])
        if not reminders:
            text = "Туть пусто 👉👈"
        else:
            text_list = []
            for r in reminders:
                reminder_text = r.get('text', "?")
                if "date" in r and "hour" in r and "minute" in r:
                    # Показываем время в часовом поясе пользователя
                    date_str = r['date']
                    hour = r['hour']
                    minute = r['minute']
                    user_tz = get_user_timezone(user_id)
                    user_timezone = pytz.timezone(user_tz)
                    
                    reminder_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    reminder_datetime = user_timezone.localize(
                        datetime.combine(reminder_date, datetime.min.time()).replace(hour=hour, minute=minute)
                    )
                    
                    # Находим название пояса для отображения
                    tz_name = "Москва"
                    for key, value in RUSSIAN_TIMEZONES.items():
                        if value[1] == user_tz:
                            tz_name = value[0]
                            break
                    
                    text_list.append(f"{reminder_text} — {reminder_datetime.strftime('%d.%m.%Y %H:%M')} ({tz_name.split(' ')[0]})")
                else:
                    text_list.append(f"{reminder_text} — Дата и время не установлены 😿")
            text = "Твои напоминульки:\n" + "\n".join(text_list)
        keyboard = [[InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_START

    # ---------------- Поддержать автора ----------------
    elif data == "support_author":
        support_message = (
            "Это не обязательно, но напоминулька для тебя бесплатна, но если ты хочешь нас поддержать, "
            "ты можешь отправить поддержалочку на номер карты: 2202206413185344 Павел Д."
        )
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_start")]]
        await query.edit_message_text(support_message, reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_START

    # ---------------- Пообщаться со мной ----------------
    elif data == "chat_with_me":
        chat_message = (
            "Эхъ, я тоже очень хочу с тобой пообщаться, но пока что я не умею разговаривать, у меня лапки 😿 "
            "Но скоро я научусь и мы сможем с тобой болтать!"
        )
        keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_start")]]
        await query.edit_message_text(chat_message, reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_START

    # ---------------- Часовой пояс ----------------
    elif data == "timezone":
        user_tz = user_timezones.get(user_id)
        
        # Проверяем, был ли уже установлен часовой пояс
        if user_tz and not context.user_data.get('timezone_changed'):
            # Первый раз после установки - показываем сообщение об отпуске
            context.user_data['timezone_changed'] = True
            message = "Видать ты отправился в замурчательный отпуск! Давай поменяем твой пояс 🏖️"
        elif user_tz and context.user_data.get('timezone_changed'):
            # Второй и последующие разы - просто показываем выбор
            message = "Выбери свой часовой пояс:"
            context.user_data['timezone_changed'] = False  # Сбрасываем флаг
        else:
            # Первый выбор
            message = "Выбери свой часовой пояс:"
        
        # Создаем клавиатуру с часовыми поясами
        keyboard = []
        row = []
        for i, (key, (name, tz)) in enumerate(RUSSIAN_TIMEZONES.items(), 1):
            row.append(InlineKeyboardButton(name, callback_data=f"tz_{key}"))
            if i % 2 == 0:  # По 2 кнопки в строке
                keyboard.append(row)
                row = []
        if row:  # Добавляем оставшиеся кнопки
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")])
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_TIMEZONE

    elif data.startswith("tz_"):
        tz_key = data.split("_")[1]
        if tz_key in RUSSIAN_TIMEZONES:
            user_timezones[user_id] = RUSSIAN_TIMEZONES[tz_key][1]
            tz_name = RUSSIAN_TIMEZONES[tz_key][0]
            
            # Сохраняем часовой пояс
            save_timezones()
            
            await query.edit_message_text(
                f"Отлично! Установлен часовой пояс: {tz_name} 🕐\n"
                f"Теперь все напоминания будут приходить в твоём местном времени!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")]])
            )
            return STATE_START

    # ---------------- Остановка напоминания ----------------
    elif data == "stop":
        reminders = user_data_store.get(str(user_id), [])
        if not reminders:
            await query.edit_message_text("Нет напоминулек для остановки 😿")
            return STATE_START
        keyboard = [[InlineKeyboardButton(r['text'], callback_data=f"stop_{idx}")] for idx, r in enumerate(reminders)]
        keyboard.append([InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")])
        await query.edit_message_text("Выбери напоминульку для остановки:", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_SELECT_REMINDER

    elif data.startswith("stop_"):
        idx = int(data.split("_")[1])
        reminders = user_data_store.get(str(user_id), [])
        if idx >= len(reminders):
            await query.edit_message_text("Ошибка: в напоминульках пусто 🙀")
            return STATE_START

        context.user_data['stop_index'] = idx
        reminder_name = reminders[idx].get('text', "?")
        keyboard = [
            [InlineKeyboardButton("Точно?", callback_data="confirm_stop")],
            [InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")]
        ]
        await query.edit_message_text(f"Ты выбрал: {reminder_name}\nХочешь удалить?", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_CONFIRM_STOP

    elif data == "confirm_stop":
        idx = context.user_data.get('stop_index')
        reminders = user_data_store.get(str(user_id), [])

        if idx is not None and idx < len(reminders):
            removed = reminders.pop(idx)
            # Также удаляем запланированные задачи (основную и скрытую)
            if user_id in scheduled_jobs and idx < len(scheduled_jobs[user_id]):
                job_info = scheduled_jobs[user_id].pop(idx)
                # Находим и отменяем обе задачи в job_queue
                current_jobs = context.job_queue.get_jobs_by_name(job_info["job_name"])
                for job in current_jobs:
                    job.schedule_removal()
                
                hidden_jobs = context.job_queue.get_jobs_by_name(job_info["hidden_job_name"])
                for job in hidden_jobs:
                    job.schedule_removal()
            
            # Сохраняем данные после удаления
            save_data()
            
            await query.edit_message_text(f"Напоминулька '{removed.get('text', '?')}' остановлена😻")
        else:
            await query.edit_message_text("Ошибка: в напоминульках пусто🙀")
        context.user_data.pop('stop_index', None)
        return await start(update, context)

    elif data == "change":
        await query.edit_message_text("Введи новую напоминульку:")
        return STATE_TEXT

    elif data == "back_to_start":
        return await start(update, context)

    # ---------------- Когда напомнить ----------------
    elif data == "when":
        if str(user_id) not in user_data_store or not user_data_store[str(user_id)]:
            await query.edit_message_text("Сначала введи что напоминаем🐱")
            return STATE_TEXT
        await show_calendar(update, context)
        return STATE_CALENDAR

    # ---------------- Выбор даты ----------------
    elif data.startswith("calendar_"):
        date_str = data.split("_")[1]
        if str(user_id) not in user_data_store or not user_data_store[str(user_id)]:
            await query.edit_message_text("Сначала введи что напоминаем🐱")
            return STATE_TEXT
        user_data_store[str(user_id)][-1]["date"] = date_str
        save_data()  # Сохраняем после установки даты

        hours = [f"{i:02}" for i in range(24)]
        keyboard = []
        row = []
        for idx, h in enumerate(hours, 1):
            row.append(InlineKeyboardButton(h, callback_data=f"hour_{h}"))
            if idx % 6 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")])
        await query.edit_message_text("В какой час?", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_HOUR

    # ---------------- Выбор часа ----------------
    elif data.startswith("hour_"):
        if str(user_id) not in user_data_store or not user_data_store[str(user_id)]:
            await query.edit_message_text("Сначала введи что напоминаем🐱")
            return STATE_TEXT
        hour_str = data.split("_")[1]
        try:
            hour = int(hour_str)
        except ValueError:
            await query.edit_message_text("Эхъ, попробуй снова, ошибочка вышла😿")
            return STATE_HOUR
        user_data_store[str(user_id)][-1]["hour"] = hour
        save_data()  # Сохраняем после установки часа

        keyboard = []
        row = []
        for i in range(0, 60, 5):
            row.append(InlineKeyboardButton(f"{i:02}", callback_data=f"minute_{i}"))
            if len(row) == 6:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")])
        await query.edit_message_text("А в какую минутку?", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_MINUTE

    # ---------------- Выбор минут ----------------
    elif data.startswith("minute_"):
        if str(user_id) not in user_data_store or not user_data_store[str(user_id)]:
            await query.edit_message_text("Сначала введи что напоминаем🐱")
            return STATE_TEXT
        try:
            minute = int(data.split("_")[1])
        except ValueError:
            await query.edit_message_text("Эхъ, попробуй снова, ошибочка вышла😿")
            return STATE_MINUTE
        user_data_store[str(user_id)][-1]["minute"] = minute
        save_data()  # Сохраняем после установки минут

        keyboard = [
            [InlineKeyboardButton("Повторять?", callback_data="repeat"),
             InlineKeyboardButton("Не повторять", callback_data="no_repeat")],
            [InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")]
        ]
        await query.edit_message_text("Когда повторять?", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_REPEAT

    # ---------------- Повторяемость ----------------
    elif data == "repeat":
        keyboard = [
            [InlineKeyboardButton("Каждый день", callback_data="daily")],
            [InlineKeyboardButton("Каждую неделю", callback_data="weekly")],
            [InlineKeyboardButton("Каждый месяц", callback_data="monthly")],
            [InlineKeyboardButton("Каждый год", callback_data="yearly")],
            [InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")]
        ]
        await query.edit_message_text("Выберите частоту повторения:", reply_markup=InlineKeyboardMarkup(keyboard))
        return STATE_REPEAT

    elif data in ["daily", "weekly", "monthly", "yearly", "no_repeat"]:
        user_data_store[str(user_id)][-1]["repeat"] = data
        reminder = user_data_store[str(user_id)][-1]
        
        # Показываем пользователю время в его часовом поясе
        date_str = reminder['date']
        hour = reminder['hour']
        minute = reminder['minute']
        user_tz = get_user_timezone(user_id)
        user_timezone = pytz.timezone(user_tz)
        
        reminder_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        reminder_datetime = user_timezone.localize(
            datetime.combine(reminder_date, datetime.min.time()).replace(hour=hour, minute=minute)
        )
        
        # Находим название пояса для отображения
        tz_name = "Москва"
        for key, value in RUSSIAN_TIMEZONES.items():
            if value[1] == user_tz:
                tz_name = value[0]
                break
        
        await query.message.reply_text("Спасибо! Есть напоминулька!")
        await query.message.reply_text(
            f"Текст: {reminder['text']}\n"
            f"Дата и время: {reminder_datetime.strftime('%d.%m.%Y %H:%M')} ({tz_name})\n"
            f"Повтор: {data}"
        )
        
        await schedule_reminder(user_id, context, reminder)
        return await start(update, context)

    else:
        await query.answer("Эта кнопка недоступна.", show_alert=True)
        return STATE_START

# ---------------------- Ввод текста ----------------------
async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    if str(user_id) not in user_data_store:
        user_data_store[str(user_id)] = []
    user_data_store[str(user_id)].append({"text": text})
    
    # Сохраняем данные после добавления текста напоминания
    save_data()

    keyboard = [
        [InlineKeyboardButton("Когда напомнить?", callback_data="when")],
        [InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")]
    ]
    await update.message.reply_text("Установили напоминульку 😺", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_START

# ---------------------- Календарь ----------------------
async def show_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, month_offset=0):
    query = update.callback_query
    now = datetime.now()
    year = now.year + (now.month + month_offset - 1) // 12
    month = (now.month + month_offset - 1) % 12 + 1
    keyboard = []

    first_day = datetime(year, month, 1)
    last_day = (first_day.replace(month=month % 12 + 1, day=1) - timedelta(days=1)).day

    for week_start in range(1, last_day + 1, 7):
        row = []
        for d in range(week_start, min(week_start + 7, last_day + 1)):
            day_date = datetime(year, month, d).date()
            if day_date >= now.date():
                row.append(InlineKeyboardButton(str(d), callback_data=f"calendar_{day_date}"))
            else:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("След. месяц", callback_data="next_month")])
    keyboard.append([InlineKeyboardButton("Вернуться в менюшку", callback_data="back_to_start")])

    try:
        await query.edit_message_text("Выбери дату:", reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        pass

# ---------------------- Основная функция ----------------------
def main():
    # Создаем приложение
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Восстанавливаем напоминания сразу после создания приложения
    restore_reminders(application)

    # Добавляем обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_START: [CallbackQueryHandler(button)],
            STATE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, text_input), 
                CallbackQueryHandler(button)
            ],
            STATE_CALENDAR: [CallbackQueryHandler(button)],
            STATE_HOUR: [CallbackQueryHandler(button)],
            STATE_MINUTE: [CallbackQueryHandler(button)],
            STATE_REPEAT: [CallbackQueryHandler(button)],
            STATE_SELECT_REMINDER: [CallbackQueryHandler(button)],
            STATE_CONFIRM_STOP: [CallbackQueryHandler(button)],
            STATE_TIMEZONE: [CallbackQueryHandler(button)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False  # Возвращаем обратно
    )

    application.add_handler(conv_handler)
    
    print("Бот запущен...")
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()