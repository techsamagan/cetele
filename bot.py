import os
import logging
import sqlite3
from datetime import datetime, date, timedelta, time as dtime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes,
)

ENTER_AMOUNT = 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
TZ = ZoneInfo("Europe/Istanbul")

# (key, daily_goal, unit_per_lang, name_per_lang)
TASKS = [
    ("quran",    2,  {"tr":"sayfa",  "en":"pages",   "ky":"барак", "ru":"стр."},  {"tr":"Kuran",    "en":"Quran",    "ky":"Куран",    "ru":"Коран"}),
    ("risale",   2,  {"tr":"sayfa",  "en":"pages",   "ky":"барак", "ru":"стр."},  {"tr":"Risale",   "en":"Risale",   "ky":"Рисала",   "ru":"Рисале"}),
    ("pirlanta", 3,  {"tr":"sayfa",  "en":"pages",   "ky":"барак", "ru":"стр."},  {"tr":"Pırlanta", "en":"Pırlanta", "ky":"Пырланта", "ru":"Пырланта"}),
    ("cevsen",   5,  {"tr":"bab",    "en":"sections","ky":"баб",   "ru":"глав"},   {"tr":"Cevşen",   "en":"Cevşen",   "ky":"Жевшен",   "ru":"Джевшен"}),
    ("meal",     1,  {"tr":"sayfa",  "en":"page",    "ky":"барак", "ru":"стр."},  {"tr":"Meal",     "en":"Meal",     "ky":"Мэал",     "ru":"Мэал"}),
    ("vaaz",     20, {"tr":"dakika", "en":"min",     "ky":"мүн",   "ru":"мин"},    {"tr":"Vaaz",     "en":"Vaaz",     "ky":"Ваз",      "ru":"Ваз"}),
]

# All day names across all languages → weekday index (0=Mon)
DAY_INPUT = {
    "pazartesi":0,"salı":1,"sali":1,"çarşamba":2,"carsamba":2,
    "perşembe":3,"persembe":3,"cuma":4,"cumartesi":5,"pazar":6,
    "monday":0,"tuesday":1,"wednesday":2,"thursday":3,
    "friday":4,"saturday":5,"sunday":6,
    "mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6,
    "понедельник":0,"вторник":1,"среда":2,"четверг":3,
    "пятница":4,"суббота":5,"воскресенье":6,
    "пн":0,"вт":1,"ср":2,"чт":3,"пт":4,"сб":5,"вс":6,
    "дүйшөмбү":0,"шейшемби":1,"шаршемби":2,"бейшемби":3,
    "жума":4,"ишемби":5,"жекшемби":6,
}

I18N = {
    "tr": {
        "welcome":      "Hoş geldin, *{name}*! 🎉 Günlük hatırlatıcın hazır.",
        "stopped":      "Hatırlatıcılar durduruldu. Tekrar başlamak için /start yaz. 👋",
        "time_set":     "✅ Hatırlatıcı saatin *{time}* olarak ayarlandı.",
        "time_usage":   "Kullanım: `/time 08:30`",
        "time_invalid": "Geçersiz format. Örnek: `/time 08:30`",
        "week_set":     "✅ Haftan *{day}* gününden başlıyor!\nHer {day} sabahı haftalık özet gönderilecek. 📅",
        "week_usage":   "Haftanın hangi günden başlasın?\n\n*Kullanım:* `/week <gün>`\n*Seçenekler:* {options}",
        "week_invalid": "Geçersiz gün. Örnek: `/week cuma`",
        "lang_set":     "✅ Dil Türkçe olarak ayarlandı.",
        "lang_invalid": "Geçersiz dil. Seçenekler: `tr` `en` `ky` `ru`",
        "stats_header": "📊 *İstatistikler*\n🔥 Seri: *{streak} gün* | Hafta başı: *{day}*\n",
        "stats_week":   "Bu hafta ({from_date} itibaren):",
        "streak_line":  "🔥 {n} günlük seri!",
        "reminder_title":"📋 *Hatırlatıcı — {date}*",
        "click_below":  "_Tamamlananları aşağıdaki butonlarla işaretle._",
        "all_done":     "\n\n🎉 *Maşallah! Hepsini tamamladın. Hayırlı olsun!*",
        "evening_nudge":"🌙 Güne az kaldı! Henüz *{n} görev* kaldı. Hadi bitirelim! 💪",
        "weekly_title": "📊 *Haftalık Özet*\n_{from_date} – {to_date}_\n",
        "weekly_stats": "🏆 Mükemmel gün: *{perfect}/7* | 📈 Tamamlama: *%{pct}*",
        "weekly_great": "🎉 Harika bir hafta!",
        "weekly_good":  "💪 Çok iyi gidiyorsun!",
        "weekly_ok":    "🤲 Gelecek hafta daha iyisini yapabilirsin!",
        "weekly_next":  "\nYeni haftan *{day}* gününden başlıyor. Hayırlı olsun! 🌟",
        "btn_reset":     "🔄 Sıfırla",
        "enter_prompt":  "✏️ Kaç {unit} {name} yaptın? Sayıyı yaz:",
        "enter_invalid": "Geçersiz sayı. Lütfen pozitif bir tam sayı gir:",
        "enter_cancel":  "İptal edildi.",
        "not_registered":"Önce /start ile kayıt ol.",
        "goal_label":   "hedef",
        "extra_label":  "ekstra",
        "days": {0:"Pazartesi",1:"Salı",2:"Çarşamba",3:"Perşembe",4:"Cuma",5:"Cumartesi",6:"Pazar"},
        "day_options":  "pazartesi · salı · çarşamba · perşembe · cuma · cumartesi · pazar",
        "intros": [
            "Bismillah! Küçük adımlar büyük yolculuklar başlatır. 💪",
            "Hayırlı günler! Bugünkü hedeflerin seni bekliyor. ✨",
            "Yeni bir gün, yeni bir fırsat. Hadi başlayalım! 🌅",
            "Allah kolaylık versin! Her gün bir tuğla, her tuğla bir saray. 🕌",
            "Bugün de güzel bir gün! Her adım seni daha iyiye götürür. 🌟",
            "Azim ve sabırla devam et. Sen yapabilirsin! 🤲",
            "Her gün bir adım, her adım bir kazanım. Başlayalım! ⭐",
        ],
    },
    "en": {
        "welcome":      "Welcome, *{name}*! 🎉 Your daily reminder is ready.",
        "stopped":      "Reminders stopped. Type /start to resume. 👋",
        "time_set":     "✅ Reminder time set to *{time}*.",
        "time_usage":   "Usage: `/time 08:30`",
        "time_invalid": "Invalid format. Example: `/time 08:30`",
        "week_set":     "✅ Your week now starts on *{day}*!\nWeekly summary sent every {day} morning. 📅",
        "week_usage":   "Which day should your week start?\n\n*Usage:* `/week <day>`\n*Options:* {options}",
        "week_invalid": "Invalid day. Example: `/week friday`",
        "lang_set":     "✅ Language set to English.",
        "lang_invalid": "Invalid language. Options: `tr` `en` `ky` `ru`",
        "stats_header": "📊 *Statistics*\n🔥 Streak: *{streak} days* | Week starts: *{day}*\n",
        "stats_week":   "This week (from {from_date}):",
        "streak_line":  "🔥 {n}-day streak!",
        "reminder_title":"📋 *Reminder — {date}*",
        "click_below":  "_Mark tasks done using the buttons below._",
        "all_done":     "\n\n🎉 *Mashallah! All tasks done. Blessed day!*",
        "evening_nudge":"🌙 Day is ending! *{n} tasks* remaining. Let's finish! 💪",
        "weekly_title": "📊 *Weekly Summary*\n_{from_date} – {to_date}_\n",
        "weekly_stats": "🏆 Perfect days: *{perfect}/7* | 📈 Completion: *{pct}%*",
        "weekly_great": "🎉 What a great week!",
        "weekly_good":  "💪 You're doing great!",
        "weekly_ok":    "🤲 You can do even better next week!",
        "weekly_next":  "\nYour new week starts on *{day}*. Blessed week ahead! 🌟",
        "btn_reset":     "🔄 Reset",
        "enter_prompt":  "✏️ How many {unit} of {name} did you do? Type the number:",
        "enter_invalid": "Invalid number. Please enter a positive whole number:",
        "enter_cancel":  "Cancelled.",
        "not_registered":"Please /start first.",
        "goal_label":   "goal",
        "extra_label":  "extra",
        "days": {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"},
        "day_options":  "monday · tuesday · wednesday · thursday · friday · saturday · sunday",
        "intros": [
            "Bismillah! Small steps lead to great journeys. 💪",
            "Good day! Today's goals are waiting for you. ✨",
            "A new day, a new opportunity. Let's go! 🌅",
            "May Allah make it easy! Every day a brick, every brick a palace. 🕌",
            "Another beautiful day! Every step takes you further. 🌟",
            "Keep going with patience and determination. You can do it! 🤲",
            "Every day a step, every step a gain. Let's begin! ⭐",
        ],
    },
    "ky": {
        "welcome":      "Кош келдиң, *{name}*! 🎉 Күнүмдүк эскертмең даяр.",
        "stopped":      "Эскертмелер токтотулду. Кайра баштоо үчүн /start жаз. 👋",
        "time_set":     "✅ Эскертме убактысы *{time}* деп коюлду.",
        "time_usage":   "Колдонуу: `/time 08:30`",
        "time_invalid": "Туура эмес формат. Мисал: `/time 08:30`",
        "week_set":     "✅ Аптаң *{day}* күнүнөн башталат!\nАр бир {day} жумалык жыйынтык жөнөтүлөт. 📅",
        "week_usage":   "Апта кайсы күндөн башталсын?\n\n*Колдонуу:* `/week <күн>`\n*Варианттар:* {options}",
        "week_invalid": "Туура эмес күн. Мисал: `/week жума`",
        "lang_set":     "✅ Тил кыргызча деп коюлду.",
        "lang_invalid": "Туура эмес тил. Варианттар: `tr` `en` `ky` `ru`",
        "stats_header": "📊 *Статистика*\n🔥 Серия: *{streak} күн* | Апта башы: *{day}*\n",
        "stats_week":   "Бул апта ({from_date} дан):",
        "streak_line":  "🔥 {n} күндүк серия!",
        "reminder_title":"📋 *Эскертме — {date}*",
        "click_below":  "_Аткарылгандарды төмөндөгү баскычтар менен белги кой._",
        "all_done":     "\n\n🎉 *Машаллах! Баарын бүтүрдүң. Кутлу болсун!*",
        "evening_nudge":"🌙 Күн бүтүп баратат! Дагы *{n} тапшырма* калды. Бүтүрөлү! 💪",
        "weekly_title": "📊 *Жумалык Жыйынтык*\n_{from_date} – {to_date}_\n",
        "weekly_stats": "🏆 Мүнөзсүз күндөр: *{perfect}/7* | 📈 Аткаруу: *{pct}%*",
        "weekly_great": "🎉 Эң сонун апта!",
        "weekly_good":  "💪 Абдан жакшы баратасың!",
        "weekly_ok":    "🤲 Кийинки аптада дагы жакшыраак кыла аласың!",
        "weekly_next":  "\nЖаңы аптаң *{day}* күнүнөн башталат. Кутлу апта! 🌟",
        "btn_reset":     "🔄 Баштапкы абалга",
        "enter_prompt":  "✏️ Канча {unit} {name} жасадың? Санды жаз:",
        "enter_invalid": "Жараксыз сан. Оң бүтүн сан кир:",
        "enter_cancel":  "Жокко чыгарылды.",
        "not_registered":"Алгач /start менен катталыңыз.",
        "goal_label":   "максат",
        "extra_label":  "кошумча",
        "days": {0:"Дүйшөмбү",1:"Шейшемби",2:"Шаршемби",3:"Бейшемби",4:"Жума",5:"Ишемби",6:"Жекшемби"},
        "day_options":  "дүйшөмбү · шейшемби · шаршемби · бейшемби · жума · ишемби · жекшемби",
        "intros": [
            "Бисмилла! Кичинекей кадамдар чоң жолду башталат. 💪",
            "Кайрымдуу күн! Бүгүнкү максаттарың сени күтүп жатат. ✨",
            "Жаңы күн, жаңы мүмкүнчүлүк. Баштайлы! 🌅",
            "Аллах жеңилдетсин! Ар бир күн бир кыш, ар бир кыш бир сарай. 🕌",
            "Дагы бир сонун күн! Ар бир кадам алга алып барат. 🌟",
            "Чыдамдуулук жана каармандык менен уланта бер. Сен кыла аласың! 🤲",
            "Ар бир күн бир кадам, ар бир кадам бир жетишкендик. Баштайлы! ⭐",
        ],
    },
    "ru": {
        "welcome":      "Добро пожаловать, *{name}*! 🎉 Ежедневное напоминание готово.",
        "stopped":      "Напоминания остановлены. Напишите /start для возобновления. 👋",
        "time_set":     "✅ Время напоминания установлено на *{time}*.",
        "time_usage":   "Использование: `/time 08:30`",
        "time_invalid": "Неверный формат. Пример: `/time 08:30`",
        "week_set":     "✅ Теперь неделя начинается с *{day}*!\nКаждый {day} будет отправляться еженедельная сводка. 📅",
        "week_usage":   "С какого дня начинается неделя?\n\n*Использование:* `/week <день>`\n*Варианты:* {options}",
        "week_invalid": "Неверный день. Пример: `/week пятница`",
        "lang_set":     "✅ Язык установлен на русский.",
        "lang_invalid": "Неверный язык. Варианты: `tr` `en` `ky` `ru`",
        "stats_header": "📊 *Статистика*\n🔥 Серия: *{streak} дней* | Начало недели: *{day}*\n",
        "stats_week":   "На этой неделе (с {from_date}):",
        "streak_line":  "🔥 Серия {n} дней!",
        "reminder_title":"📋 *Напоминание — {date}*",
        "click_below":  "_Отметь выполненные задачи кнопками ниже._",
        "all_done":     "\n\n🎉 *МашаАллах! Всё выполнено. БаракаАллах!*",
        "evening_nudge":"🌙 День заканчивается! Осталось *{n} задач*. Давай завершим! 💪",
        "weekly_title": "📊 *Еженедельная сводка*\n_{from_date} – {to_date}_\n",
        "weekly_stats": "🏆 Идеальных дней: *{perfect}/7* | 📈 Выполнение: *{pct}%*",
        "weekly_great": "🎉 Отличная неделя!",
        "weekly_good":  "💪 Ты отлично справляешься!",
        "weekly_ok":    "🤲 На следующей неделе можешь сделать лучше!",
        "weekly_next":  "\nНовая неделя начинается с *{day}*. Благословенной недели! 🌟",
        "btn_reset":     "🔄 Сбросить",
        "enter_prompt":  "✏️ Сколько {unit} {name} ты сделал? Напиши число:",
        "enter_invalid": "Неверное число. Введи положительное целое число:",
        "enter_cancel":  "Отменено.",
        "not_registered":"Сначала напишите /start.",
        "goal_label":   "цель",
        "extra_label":  "доп.",
        "days": {0:"Понедельник",1:"Вторник",2:"Среда",3:"Четверг",4:"Пятница",5:"Суббота",6:"Воскресенье"},
        "day_options":  "понедельник · вторник · среда · четверг · пятница · суббота · воскресенье",
        "intros": [
            "Бисмилла! Маленькие шаги ведут к великим путешествиям. 💪",
            "Доброго дня! Сегодняшние цели ждут тебя. ✨",
            "Новый день, новая возможность. Начнём! 🌅",
            "Пусть Аллах облегчит! Каждый день — кирпич, каждый кирпич — дворец. 🕌",
            "Ещё один прекрасный день! Каждый шаг ведёт тебя вперёд. 🌟",
            "Продолжай с терпением и решимостью. Ты можешь! 🤲",
            "Каждый день — шаг, каждый шаг — достижение. Начнём! ⭐",
        ],
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def t(lang: str, key: str, **kwargs) -> str:
    return I18N[lang][key].format(**kwargs)

def task_label(task: tuple, lang: str, qty: int = 0) -> str:
    key, goal, units, names = task
    unit = units.get(lang, units["tr"])
    name = names.get(lang, names["tr"])
    if qty > goal:
        return f"{qty} {unit} {name} (+{qty - goal} {t(lang, 'extra_label')})"
    return f"{goal} {unit} {name}"


# ── Database ──────────────────────────────────────────────────────────────────

def db():
    conn = sqlite3.connect("cetele.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                first_name    TEXT,
                reminder_time TEXT    DEFAULT '08:00',
                week_start    INTEGER DEFAULT 0,
                lang          TEXT    DEFAULT 'tr',
                active        INTEGER DEFAULT 1,
                joined_at     TEXT    DEFAULT (date('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS completions (
                user_id  INTEGER,
                date     TEXT,
                task_key TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date, task_key)
            )
        """)
        for col, dflt in [("lang", "'tr'"), ("quantity", "0")]:
            try:
                c.execute(f"ALTER TABLE {'users' if col == 'lang' else 'completions'} ADD COLUMN {col} INTEGER DEFAULT {dflt}")
            except Exception:
                pass

def get_user(user_id):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def upsert_user(user_id, username, first_name, lang=None):
    with db() as c:
        if lang:
            c.execute("""
                INSERT INTO users (user_id, username, first_name, lang) VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    active=1, username=excluded.username,
                    first_name=excluded.first_name, lang=excluded.lang
            """, (user_id, username or "", first_name or "", lang))
        else:
            c.execute("""
                INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    active=1, username=excluded.username, first_name=excluded.first_name
            """, (user_id, username or "", first_name or ""))

def all_active_users():
    with db() as c:
        return c.execute("SELECT * FROM users WHERE active = 1").fetchall()

def get_quantities(user_id, date_str) -> dict:
    with db() as c:
        rows = c.execute(
            "SELECT task_key, quantity FROM completions WHERE user_id = ? AND date = ?",
            (user_id, date_str),
        ).fetchall()
    return {r["task_key"]: r["quantity"] for r in rows}

def set_quantity(user_id, date_str, task_key, qty):
    with db() as c:
        c.execute("""
            INSERT INTO completions (user_id, date, task_key, quantity) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date, task_key) DO UPDATE SET quantity = excluded.quantity
        """, (user_id, date_str, task_key, qty))

def add_quantity(user_id, date_str, task_key, amount):
    with db() as c:
        c.execute("""
            INSERT INTO completions (user_id, date, task_key, quantity) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date, task_key) DO UPDATE SET quantity = quantity + excluded.quantity
        """, (user_id, date_str, task_key, amount))

def reset_day(user_id, date_str):
    with db() as c:
        c.execute("DELETE FROM completions WHERE user_id = ? AND date = ?", (user_id, date_str))

def is_done(qty, goal) -> bool:
    return qty >= goal

def all_done_today(user_id, date_str) -> bool:
    qtys = get_quantities(user_id, date_str)
    return all(qtys.get(key, 0) >= goal for key, goal, _, _ in TASKS)

def get_streak(user_id) -> int:
    streak = 0
    today = date.today()
    d = today if all_done_today(user_id, today.isoformat()) else today - timedelta(days=1)
    while all_done_today(user_id, d.isoformat()):
        streak += 1
        d -= timedelta(days=1)
    return streak

def week_rows(user_id, week_start_day) -> tuple:
    today = date.today()
    days_back = (today.weekday() - week_start_day) % 7
    week_start = today - timedelta(days=days_back)
    rows = []
    d = week_start
    while d <= today:
        qtys = get_quantities(user_id, d.isoformat())
        done = sum(1 for key, goal, _, _ in TASKS if qtys.get(key, 0) >= goal)
        rows.append((d, done))
        d += timedelta(days=1)
    return rows, week_start

def user_lang(user_id) -> str:
    user = get_user(user_id)
    return user["lang"] if user else "tr"


# ── Message builders ──────────────────────────────────────────────────────────

def build_text(user_id, date_str, intro_idx=0) -> str:
    lang = user_lang(user_id)
    qtys = get_quantities(user_id, date_str)
    streak = get_streak(user_id)
    date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d")
    intro = I18N[lang]["intros"][intro_idx % len(I18N[lang]["intros"])]

    lines = [intro, "", t(lang, "reminder_title", date=date_display)]
    if streak > 0:
        lines.append(t(lang, "streak_line", n=streak))
    lines.append("")

    for task in TASKS:
        key, goal, _, _ = task
        qty = qtys.get(key, 0)
        if is_done(qty, goal):
            icon = "✅"
        elif qty > 0:
            icon = "🔶"
        else:
            icon = "⬜"
        lines.append(f"{icon} {task_label(task, lang, qty)}")

    lines += ["", t(lang, "click_below")]
    return "\n".join(lines)

def build_keyboard(user_id, date_str):
    lang = user_lang(user_id)
    qtys = get_quantities(user_id, date_str)
    buttons = []

    for task in TASKS:
        key, goal, units, names = task
        qty = qtys.get(key, 0)
        name = names.get(lang, names["tr"])
        unit = units.get(lang, units["tr"])
        if not is_done(qty, goal):
            # Top row: mark fully done
            buttons.append([InlineKeyboardButton(
                f"✅ {task_label(task, lang)}",
                callback_data=f"done:{date_str}:{key}",
            )])
            # Second row: log partial — +1 and ✏️ (always available, even before minimum)
            partial_row = [InlineKeyboardButton(
                f"➕ +1 {name}",
                callback_data=f"more1:{date_str}:{key}",
            ), InlineKeyboardButton(
                "✏️",
                callback_data=f"enter:{date_str}:{key}",
            )]
            buttons.append(partial_row)
        else:
            # +1 always; +goal when goal > 1; ✏️ to type a custom amount
            row = [InlineKeyboardButton(
                f"➕ +1 {name}",
                callback_data=f"more1:{date_str}:{key}",
            )]
            if goal > 1:
                row.append(InlineKeyboardButton(
                    f"➕ +{goal} {unit}",
                    callback_data=f"more:{date_str}:{key}",
                ))
            row.append(InlineKeyboardButton(
                "✏️",
                callback_data=f"enter:{date_str}:{key}",
            ))
            buttons.append(row)

    all_complete = all(is_done(qtys.get(k, 0), g) for k, g, _, _ in TASKS)
    if not all_complete or any(qtys.get(k, 0) > 0 for k, _, _, _ in TASKS):
        buttons.append([InlineKeyboardButton(t(lang, "btn_reset"), callback_data=f"reset:{date_str}")])

    return InlineKeyboardMarkup(buttons) if buttons else None


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username, u.first_name)
    lang = user_lang(u.id)
    today = datetime.now(TZ).date().isoformat()
    text = build_text(u.id, today, intro_idx=datetime.now(TZ).weekday())
    await update.message.reply_text(
        t(lang, "welcome", name=u.first_name) + "\n\n" + text,
        parse_mode="Markdown",
        reply_markup=build_keyboard(u.id, today),
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = user_lang(uid)
    with db() as c:
        c.execute("UPDATE users SET active = 0 WHERE user_id = ?", (uid,))
    await update.message.reply_text(t(lang, "stopped"))

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not context.args or context.args[0] not in I18N:
        await update.message.reply_text(
            "🌐 Choose your language:\n\n`/lang tr` — Türkçe\n`/lang en` — English\n`/lang ky` — Кыргызча\n`/lang ru` — Русский",
            parse_mode="Markdown",
        )
        return
    new_lang = context.args[0]
    with db() as c:
        # Create a minimal record if the user doesn't exist yet (active=0 until /start).
        # Never touch active here — stopped users stay stopped, new users stay unregistered.
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, active) VALUES (?, ?, ?, 0)",
            (u.id, u.username or "", u.first_name or ""),
        )
        c.execute("UPDATE users SET lang = ? WHERE user_id = ?", (new_lang, u.id))
    await update.message.reply_text(t(new_lang, "lang_set"))

async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = user_lang(uid)
    if not context.args:
        await update.message.reply_text(t(lang, "time_usage"), parse_mode="Markdown")
        return
    try:
        datetime.strptime(context.args[0], "%H:%M")
    except ValueError:
        await update.message.reply_text(t(lang, "time_invalid"), parse_mode="Markdown")
        return
    with db() as c:
        c.execute("UPDATE users SET reminder_time = ? WHERE user_id = ?", (context.args[0], uid))
    await update.message.reply_text(t(lang, "time_set", time=context.args[0]), parse_mode="Markdown")

async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = user_lang(uid)
    if not context.args:
        await update.message.reply_text(
            t(lang, "week_usage", options=t(lang, "day_options")), parse_mode="Markdown"
        )
        return
    key = context.args[0].lower()
    if key not in DAY_INPUT:
        await update.message.reply_text(t(lang, "week_invalid"), parse_mode="Markdown")
        return
    day_num = DAY_INPUT[key]
    day_name = I18N[lang]["days"][day_num]
    with db() as c:
        c.execute("UPDATE users SET week_start = ? WHERE user_id = ?", (day_num, uid))
    await update.message.reply_text(t(lang, "week_set", day=day_name), parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if not user:
        await update.message.reply_text(t("tr", "not_registered"))
        return
    lang = user["lang"]
    streak = get_streak(uid)
    day_name = I18N[lang]["days"][user["week_start"]]
    rows, week_start = week_rows(uid, user["week_start"])
    lines = [t(lang, "stats_header", streak=streak, day=day_name),
             t(lang, "stats_week", from_date=week_start.strftime("%m/%d"))]
    for d, done in rows:
        bar = "✅" * done + "⬜" * (len(TASKS) - done)
        lines.append(f"  {d.strftime('%m/%d')} {bar} {done}/{len(TASKS)}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Button handler ────────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = user_lang(uid)
    data = query.data

    if data.startswith("done:"):
        _, date_str, key = data.split(":", 2)
        goal = next(g for k, g, _, _ in TASKS if k == key)
        set_quantity(uid, date_str, key, goal)
    elif data.startswith("more1:"):
        _, date_str, key = data.split(":", 2)
        add_quantity(uid, date_str, key, 1)
    elif data.startswith("more:"):
        _, date_str, key = data.split(":", 2)
        goal = next(g for k, g, _, _ in TASKS if k == key)
        add_quantity(uid, date_str, key, goal)
    elif data.startswith("reset:"):
        _, date_str = data.split(":", 1)
        reset_day(uid, date_str)
    else:
        return

    text = build_text(uid, date_str, intro_idx=datetime.now(TZ).weekday())
    keyboard = build_keyboard(uid, date_str)
    if all_done_today(uid, date_str):
        text += t(lang, "all_done")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ── Custom-amount conversation ────────────────────────────────────────────────

async def btn_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    lang = user_lang(uid)
    _, date_str, key = query.data.split(":", 2)
    task = next(task for task in TASKS if task[0] == key)
    _, goal, units, names = task
    unit = units.get(lang, units["tr"])
    name = names.get(lang, names["tr"])
    context.user_data["pending_add"] = {"date_str": date_str, "key": key}
    await query.message.reply_text(t(lang, "enter_prompt", unit=unit, name=name))
    return ENTER_AMOUNT

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = user_lang(uid)
    pending = context.user_data.get("pending_add")
    if not pending:
        return ConversationHandler.END
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(t(lang, "enter_invalid"))
        return ENTER_AMOUNT
    date_str = pending["date_str"]
    key = pending["key"]
    context.user_data.pop("pending_add", None)
    add_quantity(uid, date_str, key, amount)
    text = build_text(uid, date_str, intro_idx=datetime.now(TZ).weekday())
    keyboard = build_keyboard(uid, date_str)
    if all_done_today(uid, date_str):
        text += t(lang, "all_done")
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def cancel_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang(update.effective_user.id)
    context.user_data.pop("pending_add", None)
    await update.message.reply_text(t(lang, "enter_cancel"))
    return ConversationHandler.END


# ── Scheduled jobs ────────────────────────────────────────────────────────────

async def job_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TZ)
    time_str = now.strftime("%H:%M")
    today = now.date().isoformat()
    for user in all_active_users():
        if user["reminder_time"] != time_str:
            continue
        uid = user["user_id"]
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=build_text(uid, today, intro_idx=now.weekday()),
                parse_mode="Markdown",
                reply_markup=build_keyboard(uid, today),
            )
        except Exception as e:
            logger.warning("Reminder failed for %s: %s", uid, e)

async def job_evening_nudge(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(TZ).date().isoformat()
    for user in all_active_users():
        uid = user["user_id"]
        lang = user["lang"]
        qtys = get_quantities(uid, today)
        remaining = sum(1 for key, goal, _, _ in TASKS if not is_done(qtys.get(key, 0), goal))
        if remaining == 0:
            continue
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=t(lang, "evening_nudge", n=remaining),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning("Evening nudge failed for %s: %s", uid, e)

async def job_weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TZ)
    today_weekday = now.weekday()
    yesterday = now.date() - timedelta(days=1)
    for user in all_active_users():
        if user["week_start"] != today_weekday:
            continue
        uid = user["user_id"]
        lang = user["lang"]
        week_start = yesterday - timedelta(days=6)
        perfect, total = 0, 0
        lines = [t(lang, "weekly_title",
                   from_date=week_start.strftime("%m/%d"),
                   to_date=yesterday.strftime("%m/%d"))]
        for i in range(7):
            d = week_start + timedelta(days=i)
            qtys = get_quantities(uid, d.isoformat())
            done = sum(1 for key, goal, _, _ in TASKS if qtys.get(key, 0) >= goal)
            total += done
            if done == len(TASKS):
                perfect += 1
            lines.append(f"{d.strftime('%m/%d')} {'✅' * done}{'⬜' * (len(TASKS) - done)} {done}/{len(TASKS)}")
        pct = round(total / (7 * len(TASKS)) * 100)
        day_name = I18N[lang]["days"][user["week_start"]]
        msg_key = "weekly_great" if perfect == 7 else "weekly_good" if perfect >= 5 else "weekly_ok"
        lines += [
            "",
            t(lang, "weekly_stats", perfect=perfect, pct=pct),
            t(lang, msg_key),
            t(lang, "weekly_next", day=day_name),
        ]
        try:
            await context.bot.send_message(
                chat_id=uid, text="\n".join(lines), parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning("Weekly summary failed for %s: %s", uid, e)


# ── Entry point ───────────────────────────────────────────────────────────────

async def _set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_code: str):
    u = update.effective_user
    with db() as c:
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, active) VALUES (?, ?, ?, 0)",
            (u.id, u.username or "", u.first_name or ""),
        )
        c.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang_code, u.id))
    await update.message.reply_text(t(lang_code, "lang_set"))

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(CommandHandler("lang",     cmd_lang))
    app.add_handler(CommandHandler("english",  lambda u, c: _set_lang(u, c, "en")))
    app.add_handler(CommandHandler("turkish",  lambda u, c: _set_lang(u, c, "tr")))
    app.add_handler(CommandHandler("kyrgyz",   lambda u, c: _set_lang(u, c, "ky")))
    app.add_handler(CommandHandler("russian",  lambda u, c: _set_lang(u, c, "ru")))
    app.add_handler(CommandHandler("time",     cmd_time))
    app.add_handler(CommandHandler("week",     cmd_week))
    app.add_handler(CommandHandler("stats",    cmd_stats))

    # ConversationHandler must be added before the general CallbackQueryHandler
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(btn_enter_amount, pattern="^enter:")],
        states={ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)]},
        fallbacks=[CommandHandler("cancel", cancel_enter)],
    ))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(job_reminders, interval=60, first=5)
    app.job_queue.run_daily(job_evening_nudge, time=dtime(18, 0))   # 21:00 Istanbul
    app.job_queue.run_daily(job_weekly_summary, time=dtime(5, 0))   # 08:00 Istanbul

    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
