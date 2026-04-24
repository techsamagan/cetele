import os, logging, sqlite3, random, string
from datetime import datetime, date, timedelta, time as dtime
from zoneinfo import ZoneInfo
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes,
)

# ── States ────────────────────────────────────────────────────────────────────
ENTER_AMOUNT = 1
REPORT_FROM  = 2
REPORT_TO    = 3
ENTER_TIME   = 4
GROUP_NAME   = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.environ["BOT_TOKEN"]
TZ = ZoneInfo("Europe/Istanbul")

# ── Tasks ─────────────────────────────────────────────────────────────────────
TASKS = [
    ("quran",    2,  {"tr":"sayfa","en":"pages",   "ky":"барак","ru":"стр."}, {"tr":"Kuran",   "en":"Quran",   "ky":"Куран",   "ru":"Коран"}),
    ("risale",   2,  {"tr":"sayfa","en":"pages",   "ky":"барак","ru":"стр."}, {"tr":"Risale",  "en":"Risale",  "ky":"Рисала",  "ru":"Рисале"}),
    ("pirlanta", 3,  {"tr":"sayfa","en":"pages",   "ky":"барак","ru":"стр."}, {"tr":"Pırlanta","en":"Pırlanta","ky":"Пырланта","ru":"Пырланта"}),
    ("cevsen",   5,  {"tr":"bab",  "en":"sections","ky":"баб",  "ru":"глав"}, {"tr":"Cevşen",  "en":"Cevşen",  "ky":"Жевшен",  "ru":"Джевшен"}),
    ("meal",     1,  {"tr":"sayfa","en":"page",    "ky":"барак","ru":"стр."}, {"tr":"Meal",    "en":"Meal",    "ky":"Мэал",    "ru":"Мэал"}),
    ("vaaz",     20, {"tr":"dakika","en":"min",    "ky":"мүн",  "ru":"мин"},  {"tr":"Vaaz",    "en":"Vaaz",    "ky":"Ваз",     "ru":"Ваз"}),
]

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

MENU = {
    "tr": {"today":"📋 Bugün","stats":"📊 İstatistik","group":"👥 Grup","settings":"⚙️ Ayarlar"},
    "en": {"today":"📋 Today","stats":"📊 Stats",     "group":"👥 Group","settings":"⚙️ Settings"},
    "ky": {"today":"📋 Бүгүн","stats":"📊 Статистика","group":"👥 Топ",  "settings":"⚙️ Орнотуулар"},
    "ru": {"today":"📋 Сегодня","stats":"📊 Статистика","group":"👥 Группа","settings":"⚙️ Настройки"},
}
ALL_MENU_TEXTS = {v for m in MENU.values() for v in m.values()}
PRESET_TIMES   = ["05:00","06:00","07:00","08:00","09:00","10:00","11:00","12:00"]
STREAK_MILESTONES = {7, 14, 30, 50, 100}

# ── Translations ──────────────────────────────────────────────────────────────
I18N = {
"tr": {
    "onboard_welcome": "Selam! 🌙 Ben *Cetele* — günlük ibadet takip botun.\n\nÖnce dilini seç:",
    "onboard_time":    "Harika! ⏰ Sana hatırlatıcıyı hangi saatte göndereyim?",
    "onboard_done":    "✅ Hazır! Her gün saat *{time}*'de hatırlatıcın gelecek.\n\nHayırlı olsun! 🤲\n\nAşağıdaki menüyü kullanabilirsin 👇",
    "welcome":         "Hoş geldin, *{name}*! 🎉",
    "stopped":         "Hatırlatıcılar durduruldu. Tekrar başlamak için /start yaz. 👋",
    "reminder_title":  "📋 *Hatırlatıcı — {date}*",
    "streak_line":     "🔥 {n} günlük seri!",
    "progress":        "{bar}  {done}/{total} tamamlandı",
    "click_below":     "_Butonlarla işaretle:_",
    "all_done":        "\n\n🎉 *Maşallah! Hepsini tamamladın. Hayırlı olsun!*",
    "almost_there":    "🎯 Son 1 görev kaldı! Hadi bitir! 💪",
    "streak_7":        "🔥 7 günlük seri! Harika gidiyorsun!",
    "streak_14":       "🔥🔥 14 gün kesintisiz! Muhteşem!",
    "streak_30":       "🔥🔥🔥 30 gün! Allah kabul etsin! 🤲",
    "streak_50":       "⭐ 50 gün! Sen bir efsanesin!",
    "streak_100":      "👑 100 gün! Maşallah, Allah razı olsun!",
    "btn_all_done":    "✅ Hepsini Tamamla",
    "btn_reset":       "🔄 Sıfırla",
    "btn_back":        "◀️ Geri",
    "settings_title":  "⚙️ *Ayarlar*\n\nNe değiştirmek istiyorsun?",
    "settings_lang":   "🌐 Dil: {lang}",
    "settings_time":   "⏰ Hatırlatıcı: {time}",
    "settings_week":   "📅 Hafta başı: {day}",
    "settings_help_btn":"❓ Yardım",
    "time_picker":     "⏰ Hatırlatıcı saatini seç:\n_(İstanbul saatiyle)_",
    "time_custom_btn": "✏️ Özel saat yaz",
    "time_set":        "✅ Hatırlatıcı saatin *{time}* olarak ayarlandı.",
    "time_ask":        "Hangi saatte hatırlatayım?\nFormat: *SS:DD* (örn: 08:30)",
    "time_invalid":    "Geçersiz format. Örnek: `08:30`",
    "time_usage":      "Kullanım: `/time 08:30`",
    "lang_picker":     "🌐 Dil seç:",
    "lang_set":        "✅ Dil Türkçe olarak ayarlandı.",
    "lang_invalid":    "Geçersiz dil.",
    "week_picker":     "📅 Haftanın başlangıç gününü seç:",
    "week_set":        "✅ Hafta başı *{day}* olarak ayarlandı.",
    "help_text":       (
        "❓ *Nasıl Kullanılır?*\n\n"
        "📋 *Bugün* — Günlük görevlerini gör ve işaretle\n"
        "📊 *İstatistik* — Serin ve haftalık ilerleme\n"
        "👥 *Grup* — Grup oluştur, üyeleri gör, rapor al\n"
        "⚙️ *Ayarlar* — Dil, saat ve hafta başı\n\n"
        "Görev tamamladıktan sonra:\n"
        "➕ *+1* — Bir tane daha ekle\n"
        "✏️ — Kaç yaptığını kendin yaz\n\n"
        "/cancel — Herhangi bir işlemi iptal et"
    ),
    "stats_header":    "📊 *İstatistikler*\n🔥 Seri: *{streak} gün* | Hafta başı: *{day}*\n",
    "stats_week":      "Bu hafta ({from_date} itibaren):",
    "evening_nudge":   "🌙 Güne az kaldı! Henüz *{n} görev* kaldı. Hadi bitirelim! 💪",
    "weekly_title":    "📊 *Haftalık Özet*\n_{from_date} – {to_date}_\n",
    "weekly_stats":    "🏆 Mükemmel gün: *{perfect}/7* | 📈 Tamamlama: *%{pct}*",
    "weekly_great":    "🎉 Harika bir hafta!",
    "weekly_good":     "💪 Çok iyi gidiyorsun!",
    "weekly_ok":       "🤲 Gelecek hafta daha iyisini yapabilirsin!",
    "weekly_next":     "\nYeni haftan *{day}* gününden başlıyor. Hayırlı olsun! 🌟",
    "not_registered":  "Önce /start ile kayıt ol.",
    "goal_label":      "hedef",
    "extra_label":     "ekstra",
    "enter_prompt":    "✏️ Kaç {unit} {name} yaptın? Sayıyı yaz:\n_(İptal için /cancel)_",
    "enter_invalid":   "Geçersiz sayı. Pozitif bir tam sayı gir:",
    "enter_cancel":    "İptal edildi.",
    "group_menu":      "👥 *Grup*\n\nBir grup oluşturabilir veya grubunu yönetebilirsin.",
    "group_btn_new":   "➕ Yeni Grup Oluştur",
    "group_btn_mine":  "📋 Grubum",
    "group_btn_report":"📊 Rapor Al",
    "group_btn_link":  "🔗 Davet Linki",
    "group_btn_members":"👥 Üyeler",
    "group_btn_leave": "🚪 Gruptan Ayrıl",
    "group_ask_name":  "Grubun adı ne olsun?\n_(İptal için /cancel)_",
    "group_created":   "✅ *{name}* grubu oluşturuldu!\n\nDavet linki:\n`{link}`\n\nBu linki paylaş — katılanlar raporunda görünür. 👥",
    "group_exists":    "Zaten bir grubun var.",
    "group_not_found": "Grup bulunamadı.",
    "group_joined":    "✅ *{name}* grubuna katıldın!\nİlerlemen grup sahibiyle paylaşılacak. 🤝",
    "group_already":   "Zaten bu grubun üyesisin.",
    "group_info":      "👥 *{name}*\n👑 Sen sahipsin\n👤 Üye sayısı: {count}",
    "group_link_msg":  "🔗 Davet linki:\n`{link}`",
    "group_members_title":"👥 *{name}* üyeleri:",
    "group_no_members":"Henüz üye yok. Linki paylaş!",
    "group_left":      "Gruptan ayrıldın.",
    "group_not_member":"Herhangi bir grubun üyesi değilsin.",
    "not_owner":       "Grubun yok. 👥 Grup → Yeni Grup ile oluşturabilirsin.",
    "report_ask_from": "📅 Rapor başlangıç tarihi?\n_(örn: 04/01 veya 2026-04-01)_",
    "report_ask_to":   "📅 Bitiş tarihi?\n_(örn: 04/23)_",
    "report_date_bad": "Geçersiz tarih. Tekrar dene (örn: 04/01):",
    "report_range_bad":"Başlangıç tarihi bitiş tarihinden önce olmalı.",
    "report_title":    "📊 *{name} — Grup Raporu*\n📅 {from_date} – {to_date}\n",
    "report_no_members":"Grupta henüz üye yok.",
    "report_cancel":   "İptal edildi.",
    "unknown":         "Seni anlamadım 😅 Aşağıdaki menüyü kullan 👇",
    "days":      {0:"Pazartesi",1:"Salı",2:"Çarşamba",3:"Perşembe",4:"Cuma",5:"Cumartesi",6:"Pazar"},
    "days_short":{0:"Pzt",1:"Sal",2:"Çar",3:"Per",4:"Cum",5:"Cmt",6:"Paz"},
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
    "onboard_welcome": "Hello! 🌙 I'm *Cetele* — your daily worship tracker.\n\nFirst, choose your language:",
    "onboard_time":    "Great! ⏰ What time should I send your daily reminder?",
    "onboard_done":    "✅ All set! Your reminder will arrive at *{time}* every day.\n\nMay it be blessed! 🤲\n\nUse the menu below 👇",
    "welcome":         "Welcome, *{name}*! 🎉",
    "stopped":         "Reminders stopped. Type /start to resume. 👋",
    "reminder_title":  "📋 *Reminder — {date}*",
    "streak_line":     "🔥 {n}-day streak!",
    "progress":        "{bar}  {done}/{total} done",
    "click_below":     "_Mark tasks with the buttons below:_",
    "all_done":        "\n\n🎉 *Mashallah! All tasks done. Blessed day!*",
    "almost_there":    "🎯 Just 1 task left! Go finish it! 💪",
    "streak_7":        "🔥 7-day streak! You're doing great!",
    "streak_14":       "🔥🔥 14 days straight! Amazing!",
    "streak_30":       "🔥🔥🔥 30 days! May Allah accept it! 🤲",
    "streak_50":       "⭐ 50 days! You're a legend!",
    "streak_100":      "👑 100 days! Mashallah, may Allah be pleased!",
    "btn_all_done":    "✅ Mark All Done",
    "btn_reset":       "🔄 Reset",
    "btn_back":        "◀️ Back",
    "settings_title":  "⚙️ *Settings*\n\nWhat would you like to change?",
    "settings_lang":   "🌐 Language: {lang}",
    "settings_time":   "⏰ Reminder: {time}",
    "settings_week":   "📅 Week starts: {day}",
    "settings_help_btn":"❓ Help",
    "time_picker":     "⏰ Choose your reminder time:\n_(Istanbul timezone)_",
    "time_custom_btn": "✏️ Enter custom time",
    "time_set":        "✅ Reminder time set to *{time}*.",
    "time_ask":        "What time should I remind you?\nFormat: *HH:MM* (e.g. 08:30)",
    "time_invalid":    "Invalid format. Example: `08:30`",
    "time_usage":      "Usage: `/time 08:30`",
    "lang_picker":     "🌐 Choose your language:",
    "lang_set":        "✅ Language set to English.",
    "lang_invalid":    "Invalid language.",
    "week_picker":     "📅 Which day should your week start?",
    "week_set":        "✅ Week start set to *{day}*.",
    "help_text":       (
        "❓ *How to use Cetele*\n\n"
        "📋 *Today* — See and mark your daily tasks\n"
        "📊 *Stats* — Your streak and weekly progress\n"
        "👥 *Group* — Create a group, see members, get reports\n"
        "⚙️ *Settings* — Language, reminder time, week start\n\n"
        "After completing minimum tasks:\n"
        "➕ *+1* — Add one more\n"
        "✏️ — Type exactly how many you did\n\n"
        "/cancel — Cancel any action"
    ),
    "stats_header":    "📊 *Statistics*\n🔥 Streak: *{streak} days* | Week starts: *{day}*\n",
    "stats_week":      "This week (from {from_date}):",
    "evening_nudge":   "🌙 Day is ending! *{n} tasks* remaining. Let's finish! 💪",
    "weekly_title":    "📊 *Weekly Summary*\n_{from_date} – {to_date}_\n",
    "weekly_stats":    "🏆 Perfect days: *{perfect}/7* | 📈 Completion: *{pct}%*",
    "weekly_great":    "🎉 What a great week!",
    "weekly_good":     "💪 You're doing great!",
    "weekly_ok":       "🤲 You can do even better next week!",
    "weekly_next":     "\nYour new week starts on *{day}*. Blessed week! 🌟",
    "not_registered":  "Please /start first.",
    "goal_label":      "goal",
    "extra_label":     "extra",
    "enter_prompt":    "✏️ How many {unit} of {name} did you do? Type the number:\n_(Type /cancel to abort)_",
    "enter_invalid":   "Invalid number. Enter a positive whole number:",
    "enter_cancel":    "Cancelled.",
    "group_menu":      "👥 *Group*\n\nCreate a group or manage your existing one.",
    "group_btn_new":   "➕ Create New Group",
    "group_btn_mine":  "📋 My Group",
    "group_btn_report":"📊 Get Report",
    "group_btn_link":  "🔗 Invite Link",
    "group_btn_members":"👥 Members",
    "group_btn_leave": "🚪 Leave Group",
    "group_ask_name":  "What should the group be called?\n_(Type /cancel to abort)_",
    "group_created":   "✅ Group *{name}* created!\n\nInvite link:\n`{link}`\n\nShare this link — whoever joins appears in your report. 👥",
    "group_exists":    "You already have a group.",
    "group_not_found": "Group not found.",
    "group_joined":    "✅ You joined *{name}*!\nYour progress will be shared with the group owner. 🤝",
    "group_already":   "You're already a member of this group.",
    "group_info":      "👥 *{name}*\n👑 You are the owner\n👤 Members: {count}",
    "group_link_msg":  "🔗 Invite link:\n`{link}`",
    "group_members_title":"👥 Members of *{name}*:",
    "group_no_members":"No members yet. Share the link!",
    "group_left":      "You left the group.",
    "group_not_member":"You're not a member of any group.",
    "not_owner":       "You don't have a group. Use 👥 Group → Create New Group.",
    "report_ask_from": "📅 Report start date?\n_(e.g. 04/01 or 2026-04-01)_",
    "report_ask_to":   "📅 End date?\n_(e.g. 04/23)_",
    "report_date_bad": "Invalid date. Try again (e.g. 04/01):",
    "report_range_bad":"Start date must be before end date.",
    "report_title":    "📊 *{name} — Group Report*\n📅 {from_date} – {to_date}\n",
    "report_no_members":"No members in this group yet.",
    "report_cancel":   "Cancelled.",
    "unknown":         "I didn't understand that 😅 Use the menu below 👇",
    "days":      {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"},
    "days_short":{0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"},
    "intros": [
        "Bismillah! Small steps lead to great journeys. 💪",
        "Good day! Your goals for today are waiting. ✨",
        "A new day, a new opportunity. Let's go! 🌅",
        "May Allah make it easy! Every day a brick, every brick a palace. 🕌",
        "Another beautiful day! Every step takes you further. 🌟",
        "Keep going with patience and determination. You can do it! 🤲",
        "Every day a step, every step a gain. Let's begin! ⭐",
    ],
},
"ky": {
    "onboard_welcome": "Салам! 🌙 Мен *Cetele* — күнүмдүк ибадат трекериң.\n\nАлгач тилиңди тандап ал:",
    "onboard_time":    "Жакшы! ⏰ Күнүмдүк эскертмени канча убакта жөнөтөйүн?",
    "onboard_done":    "✅ Даяр! Ар күнү саат *{time}*'де эскертме келет.\n\nКутлу болсун! 🤲\n\nТөмөндөгү менюну колдон 👇",
    "welcome":         "Кош келдиң, *{name}*! 🎉",
    "stopped":         "Эскертмелер токтотулду. Кайра баштоо үчүн /start жаз. 👋",
    "reminder_title":  "📋 *Эскертме — {date}*",
    "streak_line":     "🔥 {n} күндүк серия!",
    "progress":        "{bar}  {done}/{total} аткарылды",
    "click_below":     "_Баскычтар менен белги кой:_",
    "all_done":        "\n\n🎉 *Машаллах! Баарын бүтүрдүң. Кутлу болсун!*",
    "almost_there":    "🎯 1 тапшырма калды! Бүтүрүп кой! 💪",
    "streak_7":        "🔥 7 күндүк серия! Абдан жакшы!",
    "streak_14":       "🔥🔥 14 күн үзгүлтүксүз! Сонун!",
    "streak_30":       "🔥🔥🔥 30 күн! Аллах кабыл алсын! 🤲",
    "streak_50":       "⭐ 50 күн! Сен легендасың!",
    "streak_100":      "👑 100 күн! Машаллах, Аллах разы болсун!",
    "btn_all_done":    "✅ Баарын Аткар",
    "btn_reset":       "🔄 Баштапкы абалга",
    "btn_back":        "◀️ Артка",
    "settings_title":  "⚙️ *Орнотуулар*\n\nЭмнени өзгөртөсүң?",
    "settings_lang":   "🌐 Тил: {lang}",
    "settings_time":   "⏰ Эскертме: {time}",
    "settings_week":   "📅 Апта башы: {day}",
    "settings_help_btn":"❓ Жардам",
    "time_picker":     "⏰ Эскертме убактысын тандап ал:\n_(Стамбул убактысы менен)_",
    "time_custom_btn": "✏️ Өз убактыңды жаз",
    "time_set":        "✅ Эскертме убактысы *{time}* деп коюлду.",
    "time_ask":        "Канча убакта эскертейин?\nФормат: *СС:МM* (мис: 08:30)",
    "time_invalid":    "Туура эмес формат. Мисал: `08:30`",
    "time_usage":      "Колдонуу: `/time 08:30`",
    "lang_picker":     "🌐 Тилди тандап ал:",
    "lang_set":        "✅ Тил кыргызча деп коюлду.",
    "lang_invalid":    "Туура эмес тил.",
    "week_picker":     "📅 Апта кайсы күндөн башталсын?",
    "week_set":        "✅ Апта башы *{day}* деп коюлду.",
    "help_text":       (
        "❓ *Кантип колдонуу керек?*\n\n"
        "📋 *Бүгүн* — Күнүмдүк тапшырмаларды көр жана белги кой\n"
        "📊 *Статистика* — Сериялар жана жумалык жетишкендиктер\n"
        "👥 *Топ* — Топ түз, мүчөлөрдү көр, отчет ал\n"
        "⚙️ *Орнотуулар* — Тил, убакыт, апта башы\n\n"
        "Минималдуу тапшырманы бүткөндөн кийин:\n"
        "➕ *+1* — Бирди кошуу\n"
        "✏️ — Канча жасаганыңды өзүң жаз\n\n"
        "/cancel — Каалаган аракетти жокко чыгар"
    ),
    "stats_header":    "📊 *Статистика*\n🔥 Серия: *{streak} күн* | Апта башы: *{day}*\n",
    "stats_week":      "Бул апта ({from_date} дан):",
    "evening_nudge":   "🌙 Күн бүтүп баратат! Дагы *{n} тапшырма* калды. Бүтүрөлү! 💪",
    "weekly_title":    "📊 *Жумалык Жыйынтык*\n_{from_date} – {to_date}_\n",
    "weekly_stats":    "🏆 Мүнөзсүз күндөр: *{perfect}/7* | 📈 Аткаруу: *{pct}%*",
    "weekly_great":    "🎉 Эң сонун апта!",
    "weekly_good":     "💪 Абдан жакшы баратасың!",
    "weekly_ok":       "🤲 Кийинки аптада дагы жакшыраак кыла аласың!",
    "weekly_next":     "\nЖаңы аптаң *{day}* күнүнөн башталат. Кутлу апта! 🌟",
    "not_registered":  "Алгач /start менен катталыңыз.",
    "goal_label":      "максат",
    "extra_label":     "кошумча",
    "enter_prompt":    "✏️ Канча {unit} {name} жасадың? Санды жаз:\n_(Жокко чыгаруу үчүн /cancel)_",
    "enter_invalid":   "Жараксыз сан. Оң бүтүн сан кир:",
    "enter_cancel":    "Жокко чыгарылды.",
    "group_menu":      "👥 *Топ*\n\nТоп түзүп же учурдагы тобуңду башкарып аласың.",
    "group_btn_new":   "➕ Жаңы Топ Түз",
    "group_btn_mine":  "📋 Менин Топтум",
    "group_btn_report":"📊 Отчет Ал",
    "group_btn_link":  "🔗 Чакыруу Шилтемеси",
    "group_btn_members":"👥 Мүчөлөр",
    "group_btn_leave": "🚪 Топтон Чык",
    "group_ask_name":  "Топтун аты кандай болсун?\n_(Жокко чыгаруу үчүн /cancel)_",
    "group_created":   "✅ *{name}* тобу түзүлдү!\n\nЧакыруу шилтемеси:\n`{link}`\n\nБу шилтемени бөлүш — кимдир кошулса сенде көрүнөт. 👥",
    "group_exists":    "Сенде мурунтан топ бар.",
    "group_not_found": "Топ табылган жок.",
    "group_joined":    "✅ *{name}* тобуна кошулдуң!\nЖетишкендигиң топ ээси менен бөлүшүлөт. 🤝",
    "group_already":   "Сен мурунтан бул топтун мүчөсүсүң.",
    "group_info":      "👥 *{name}*\n👑 Сен ээсисиң\n👤 Мүчөлөр: {count}",
    "group_link_msg":  "🔗 Чакыруу шилтемеси:\n`{link}`",
    "group_members_title":"👥 *{name}* топтун мүчөлөрү:",
    "group_no_members":"Азырынча мүчө жок. Шилтемени бөлүш!",
    "group_left":      "Топтон чыктың.",
    "group_not_member":"Сен эч кандай топтун мүчөсү эмессиң.",
    "not_owner":       "Сенде топ жок. 👥 Топ → Жаңы Топ Түз.",
    "report_ask_from": "📅 Отчет башталган күнү?\n_(мис: 04/01 же 2026-04-01)_",
    "report_ask_to":   "📅 Аяктаган күнү?\n_(мис: 04/23)_",
    "report_date_bad": "Туура эмес күн. Кайра аракет кыл (мис: 04/01):",
    "report_range_bad":"Башталган күн аяктаган күндөн мурун болушу керек.",
    "report_title":    "📊 *{name} — Топ Отчету*\n📅 {from_date} – {to_date}\n",
    "report_no_members":"Топто азырынча мүчө жок.",
    "report_cancel":   "Жокко чыгарылды.",
    "unknown":         "Сени түшүнбөдүм 😅 Төмөндөгү менюну колдон 👇",
    "days":      {0:"Дүйшөмбү",1:"Шейшемби",2:"Шаршемби",3:"Бейшемби",4:"Жума",5:"Ишемби",6:"Жекшемби"},
    "days_short":{0:"Дүй",1:"Шей",2:"Шар",3:"Бей",4:"Жум",5:"Ише",6:"Жек"},
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
    "onboard_welcome": "Привет! 🌙 Я *Cetele* — твой ежедневный трекер ибадата.\n\nСначала выбери язык:",
    "onboard_time":    "Отлично! ⏰ В какое время отправлять ежедневное напоминание?",
    "onboard_done":    "✅ Готово! Каждый день в *{time}* будет приходить напоминание.\n\nБаракаАллах! 🤲\n\nИспользуй меню ниже 👇",
    "welcome":         "Добро пожаловать, *{name}*! 🎉",
    "stopped":         "Напоминания остановлены. Напишите /start для возобновления. 👋",
    "reminder_title":  "📋 *Напоминание — {date}*",
    "streak_line":     "🔥 Серия {n} дней!",
    "progress":        "{bar}  {done}/{total} выполнено",
    "click_below":     "_Отмечай кнопками ниже:_",
    "all_done":        "\n\n🎉 *МашаАллах! Всё выполнено. БаракаАллах!*",
    "almost_there":    "🎯 Осталась 1 задача! Давай завершим! 💪",
    "streak_7":        "🔥 7-дневная серия! Отлично идёшь!",
    "streak_14":       "🔥🔥 14 дней подряд! Потрясающе!",
    "streak_30":       "🔥🔥🔥 30 дней! Пусть Аллах примет! 🤲",
    "streak_50":       "⭐ 50 дней! Ты легенда!",
    "streak_100":      "👑 100 дней! МашаАллах, да будет доволен Аллах!",
    "btn_all_done":    "✅ Выполнить Всё",
    "btn_reset":       "🔄 Сбросить",
    "btn_back":        "◀️ Назад",
    "settings_title":  "⚙️ *Настройки*\n\nЧто хочешь изменить?",
    "settings_lang":   "🌐 Язык: {lang}",
    "settings_time":   "⏰ Напоминание: {time}",
    "settings_week":   "📅 Начало недели: {day}",
    "settings_help_btn":"❓ Помощь",
    "time_picker":     "⏰ Выбери время напоминания:\n_(Стамбульское время)_",
    "time_custom_btn": "✏️ Ввести своё время",
    "time_set":        "✅ Время напоминания установлено на *{time}*.",
    "time_ask":        "В какое время напоминать?\nФормат: *ЧЧ:ММ* (напр: 08:30)",
    "time_invalid":    "Неверный формат. Пример: `08:30`",
    "time_usage":      "Использование: `/time 08:30`",
    "lang_picker":     "🌐 Выбери язык:",
    "lang_set":        "✅ Язык установлен на русский.",
    "lang_invalid":    "Неверный язык.",
    "week_picker":     "📅 С какого дня начинается неделя?",
    "week_set":        "✅ Начало недели установлено на *{day}*.",
    "help_text":       (
        "❓ *Как пользоваться Cetele*\n\n"
        "📋 *Сегодня* — Просматривай и отмечай ежедневные задачи\n"
        "📊 *Статистика* — Серии и еженедельный прогресс\n"
        "👥 *Группа* — Создай группу, смотри участников, получай отчёты\n"
        "⚙️ *Настройки* — Язык, время, начало недели\n\n"
        "После выполнения минимума:\n"
        "➕ *+1* — Добавить ещё одно\n"
        "✏️ — Ввести точное количество\n\n"
        "/cancel — Отменить любое действие"
    ),
    "stats_header":    "📊 *Статистика*\n🔥 Серия: *{streak} дней* | Начало недели: *{day}*\n",
    "stats_week":      "На этой неделе (с {from_date}):",
    "evening_nudge":   "🌙 День заканчивается! Осталось *{n} задач*. Давай завершим! 💪",
    "weekly_title":    "📊 *Еженедельная сводка*\n_{from_date} – {to_date}_\n",
    "weekly_stats":    "🏆 Идеальных дней: *{perfect}/7* | 📈 Выполнение: *{pct}%*",
    "weekly_great":    "🎉 Отличная неделя!",
    "weekly_good":     "💪 Ты отлично справляешься!",
    "weekly_ok":       "🤲 На следующей неделе можешь сделать лучше!",
    "weekly_next":     "\nНовая неделя начинается с *{day}*. Благословенной недели! 🌟",
    "not_registered":  "Сначала напишите /start.",
    "goal_label":      "цель",
    "extra_label":     "доп.",
    "enter_prompt":    "✏️ Сколько {unit} {name} ты сделал? Напиши число:\n_(Для отмены /cancel)_",
    "enter_invalid":   "Неверное число. Введи положительное целое число:",
    "enter_cancel":    "Отменено.",
    "group_menu":      "👥 *Группа*\n\nСоздай группу или управляй существующей.",
    "group_btn_new":   "➕ Создать Новую Группу",
    "group_btn_mine":  "📋 Моя Группа",
    "group_btn_report":"📊 Получить Отчёт",
    "group_btn_link":  "🔗 Ссылка-приглашение",
    "group_btn_members":"👥 Участники",
    "group_btn_leave": "🚪 Покинуть Группу",
    "group_ask_name":  "Как назовём группу?\n_(Для отмены /cancel)_",
    "group_created":   "✅ Группа *{name}* создана!\n\nСсылка-приглашение:\n`{link}`\n\nПоделись ссылкой — все вступившие видны в отчёте. 👥",
    "group_exists":    "У тебя уже есть группа.",
    "group_not_found": "Группа не найдена.",
    "group_joined":    "✅ Ты вступил в *{name}*!\nТвои результаты будут видны владельцу. 🤝",
    "group_already":   "Ты уже являешься участником этой группы.",
    "group_info":      "👥 *{name}*\n👑 Ты владелец\n👤 Участников: {count}",
    "group_link_msg":  "🔗 Ссылка-приглашение:\n`{link}`",
    "group_members_title":"👥 Участники *{name}*:",
    "group_no_members":"Пока нет участников. Поделись ссылкой!",
    "group_left":      "Ты покинул группу.",
    "group_not_member":"Ты не являешься участником ни одной группы.",
    "not_owner":       "У тебя нет группы. Используй 👥 Группа → Создать Новую Группу.",
    "report_ask_from": "📅 Дата начала отчёта?\n_(напр: 04/01 или 2026-04-01)_",
    "report_ask_to":   "📅 Дата окончания?\n_(напр: 04/23)_",
    "report_date_bad": "Неверная дата. Попробуй снова (напр: 04/01):",
    "report_range_bad":"Дата начала должна быть раньше даты окончания.",
    "report_title":    "📊 *{name} — Групповой отчёт*\n📅 {from_date} – {to_date}\n",
    "report_no_members":"В группе пока нет участников.",
    "report_cancel":   "Отменено.",
    "unknown":         "Не понял тебя 😅 Используй меню ниже 👇",
    "days":      {0:"Понедельник",1:"Вторник",2:"Среда",3:"Четверг",4:"Пятница",5:"Суббота",6:"Воскресенье"},
    "days_short":{0:"Пн",1:"Вт",2:"Ср",3:"Чт",4:"Пт",5:"Сб",6:"Вс"},
    "intros": [
        "Бисмилла! Маленькие шаги ведут к великим путешествиям. 💪",
        "Доброго дня! Сегодняшние цели ждут тебя. ✨",
        "Новый день, новая возможность. Начнём! 🌅",
        "Пусть Аллах облегчит! Каждый день — кирпич, каждый кирпич — дворец. 🕌",
        "Ещё один прекрасный день! Каждый шаг ведёт вперёд. 🌟",
        "Продолжай с терпением и решимостью. Ты можешь! 🤲",
        "Каждый день — шаг, каждый шаг — достижение. Начнём! ⭐",
    ],
},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def t(lang: str, key: str, **kw) -> str:
    return I18N.get(lang, I18N["tr"])[key].format(**kw)

def task_label(task, lang, qty=0) -> str:
    key, goal, units, names = task
    unit = units.get(lang, units["tr"])
    name = names.get(lang, names["tr"])
    if qty > goal:
        return f"{qty} {unit} {name} (+{qty-goal} {t(lang,'extra_label')})"
    return f"{goal} {unit} {name}"

def progress_bar(done, total, width=6) -> str:
    filled = round(done / total * width) if total else 0
    return "▓" * filled + "░" * (width - filled)

def milestone_msg(lang, streak) -> str | None:
    key = f"streak_{streak}" if streak in STREAK_MILESTONES else None
    return t(lang, key) if key else None

def parse_date(text: str):
    for fmt in ("%m/%d", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            d = datetime.strptime(text.strip(), fmt)
            if fmt == "%m/%d":
                d = d.replace(year=date.today().year)
            return d.date()
        except ValueError:
            continue
    return None

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
                onboarded     INTEGER DEFAULT 0,
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id   TEXT PRIMARY KEY,
                owner_id   INTEGER NOT NULL,
                name       TEXT NOT NULL,
                created_at TEXT DEFAULT (date('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                group_id  TEXT,
                user_id   INTEGER,
                joined_at TEXT DEFAULT (date('now')),
                PRIMARY KEY (group_id, user_id)
            )
        """)
        for stmt in [
            "ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'tr'",
            "ALTER TABLE users ADD COLUMN onboarded INTEGER DEFAULT 0",
            "ALTER TABLE completions ADD COLUMN quantity INTEGER DEFAULT 0",
        ]:
            try: c.execute(stmt)
            except Exception: pass

def get_user(user_id):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def upsert_user(uid, username, fname):
    with db() as c:
        c.execute("""
            INSERT INTO users (user_id,username,first_name) VALUES (?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                active=1, username=excluded.username, first_name=excluded.first_name
        """, (uid, username or "", fname or ""))

def all_active_users():
    with db() as c:
        return c.execute("SELECT * FROM users WHERE active=1").fetchall()

def get_quantities(uid, date_str) -> dict:
    with db() as c:
        rows = c.execute(
            "SELECT task_key, quantity FROM completions WHERE user_id=? AND date=?",
            (uid, date_str),
        ).fetchall()
    return {r["task_key"]: r["quantity"] for r in rows}

def set_quantity(uid, date_str, key, qty):
    with db() as c:
        c.execute("""
            INSERT INTO completions (user_id,date,task_key,quantity) VALUES (?,?,?,?)
            ON CONFLICT(user_id,date,task_key) DO UPDATE SET quantity=excluded.quantity
        """, (uid, date_str, key, qty))

def add_quantity(uid, date_str, key, amt):
    with db() as c:
        c.execute("""
            INSERT INTO completions (user_id,date,task_key,quantity) VALUES (?,?,?,?)
            ON CONFLICT(user_id,date,task_key) DO UPDATE SET quantity=quantity+excluded.quantity
        """, (uid, date_str, key, amt))

def reset_day(uid, date_str):
    with db() as c:
        c.execute("DELETE FROM completions WHERE user_id=? AND date=?", (uid, date_str))

def is_done(qty, goal) -> bool:
    return qty >= goal

def all_done_today(uid, date_str) -> bool:
    qtys = get_quantities(uid, date_str)
    return all(qtys.get(k, 0) >= g for k, g, _, _ in TASKS)

def get_streak(uid) -> int:
    streak = 0
    today = date.today()
    d = today if all_done_today(uid, today.isoformat()) else today - timedelta(days=1)
    while all_done_today(uid, d.isoformat()):
        streak += 1
        d -= timedelta(days=1)
    return streak

def week_rows(uid, week_start_day):
    today = date.today()
    days_back = (today.weekday() - week_start_day) % 7
    week_start = today - timedelta(days=days_back)
    rows = []
    d = week_start
    while d <= today:
        qtys = get_quantities(uid, d.isoformat())
        done = sum(1 for k, g, _, _ in TASKS if qtys.get(k, 0) >= g)
        rows.append((d, done))
        d += timedelta(days=1)
    return rows, week_start

def user_lang(uid) -> str:
    u = get_user(uid)
    return u["lang"] if u else "tr"

# Group DB
def _gid() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=7))

def create_group(owner_id, name) -> str:
    gid = _gid()
    with db() as c:
        c.execute("INSERT INTO groups (group_id,owner_id,name) VALUES (?,?,?)", (gid, owner_id, name))
    return gid

def get_owner_group(uid):
    with db() as c:
        return c.execute("SELECT * FROM groups WHERE owner_id=?", (uid,)).fetchone()

def get_group(gid):
    with db() as c:
        return c.execute("SELECT * FROM groups WHERE group_id=?", (gid,)).fetchone()

def get_members(gid) -> list:
    with db() as c:
        return c.execute(
            "SELECT u.* FROM users u JOIN group_members gm ON u.user_id=gm.user_id WHERE gm.group_id=?",
            (gid,),
        ).fetchall()

def member_count(gid) -> int:
    with db() as c:
        return c.execute("SELECT COUNT(*) FROM group_members WHERE group_id=?", (gid,)).fetchone()[0]

def add_member(gid, uid):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO group_members (group_id,user_id) VALUES (?,?)", (gid, uid))

def is_member(gid, uid) -> bool:
    with db() as c:
        return c.execute(
            "SELECT 1 FROM group_members WHERE group_id=? AND user_id=?", (gid, uid)
        ).fetchone() is not None

def remove_member(gid, uid):
    with db() as c:
        c.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (gid, uid))

def user_groups(uid) -> list:
    with db() as c:
        return c.execute(
            "SELECT g.* FROM groups g JOIN group_members gm ON g.group_id=gm.group_id WHERE gm.user_id=?",
            (uid,),
        ).fetchall()

# ── Builders ──────────────────────────────────────────────────────────────────

def build_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    m = MENU[lang]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(m["today"]), KeyboardButton(m["stats"])],
         [KeyboardButton(m["group"]), KeyboardButton(m["settings"])]],
        resize_keyboard=True,
    )

def build_text(uid, date_str, intro_idx=0) -> str:
    lang = user_lang(uid)
    qtys = get_quantities(uid, date_str)
    streak = get_streak(uid)
    date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d")
    intro = I18N[lang]["intros"][intro_idx % len(I18N[lang]["intros"])]
    done_count = sum(1 for k, g, _, _ in TASKS if qtys.get(k, 0) >= g)
    bar = progress_bar(done_count, len(TASKS))

    lines = [intro, "", t(lang, "reminder_title", date=date_display)]
    if streak > 0:
        lines.append(t(lang, "streak_line", n=streak))
    lines.append(t(lang, "progress", bar=bar, done=done_count, total=len(TASKS)))
    lines.append("")

    for task in TASKS:
        key, goal, _, _ = task
        qty = qtys.get(key, 0)
        icon = "✅" if is_done(qty, goal) else ("🔶" if qty > 0 else "⬜")
        lines.append(f"{icon} {task_label(task, lang, qty)}")

    lines += ["", t(lang, "click_below")]
    return "\n".join(lines)

def build_keyboard(uid, date_str):
    lang = user_lang(uid)
    qtys = get_quantities(uid, date_str)
    buttons = []
    all_complete = all(is_done(qtys.get(k, 0), g) for k, g, _, _ in TASKS)

    if not all_complete:
        buttons.append([InlineKeyboardButton(
            t(lang, "btn_all_done"),
            callback_data=f"alldone:{date_str}",
        )])

    for task in TASKS:
        key, goal, units, names = task
        qty = qtys.get(key, 0)
        name = names.get(lang, names["tr"])
        unit = units.get(lang, units["tr"])
        if not is_done(qty, goal):
            buttons.append([InlineKeyboardButton(
                f"✅ {task_label(task, lang)}",
                callback_data=f"done:{date_str}:{key}",
            )])
            buttons.append([
                InlineKeyboardButton(f"➕ +1 {name}", callback_data=f"more1:{date_str}:{key}"),
                InlineKeyboardButton("✏️", callback_data=f"enter:{date_str}:{key}"),
            ])
        else:
            row = [InlineKeyboardButton(f"➕ +1 {name}", callback_data=f"more1:{date_str}:{key}")]
            if goal > 1:
                row.append(InlineKeyboardButton(f"➕ +{goal} {unit}", callback_data=f"more:{date_str}:{key}"))
            row.append(InlineKeyboardButton("✏️", callback_data=f"enter:{date_str}:{key}"))
            buttons.append(row)

    if any(qtys.get(k, 0) > 0 for k, _, _, _ in TASKS):
        buttons.append([InlineKeyboardButton(t(lang, "btn_reset"), callback_data=f"reset:{date_str}")])

    return InlineKeyboardMarkup(buttons) if buttons else None

def build_settings_keyboard(uid) -> InlineKeyboardMarkup:
    lang = user_lang(uid)
    user = get_user(uid)
    day_name = I18N[lang]["days"][user["week_start"]]
    lang_names = {"tr":"Türkçe","en":"English","ky":"Кыргызча","ru":"Русский"}
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "settings_lang", lang=lang_names.get(lang, lang)), callback_data="settings:lang")],
        [InlineKeyboardButton(t(lang, "settings_time", time=user["reminder_time"]),      callback_data="settings:time")],
        [InlineKeyboardButton(t(lang, "settings_week", day=day_name),                    callback_data="settings:week")],
        [InlineKeyboardButton(t(lang, "settings_help_btn"),                              callback_data="settings:help")],
    ])

def build_lang_keyboard(prefix="settings:setlang") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇹🇷 Türkçe",   callback_data=f"{prefix}:tr"),
         InlineKeyboardButton("🇬🇧 English",  callback_data=f"{prefix}:en")],
        [InlineKeyboardButton("🇰🇬 Кыргызча", callback_data=f"{prefix}:ky"),
         InlineKeyboardButton("🇷🇺 Русский",  callback_data=f"{prefix}:ru")],
        [InlineKeyboardButton("◀️", callback_data="settings:main")],
    ])

def build_time_keyboard(prefix="settings:settime") -> InlineKeyboardMarkup:
    rows = []
    row = []
    for tm in PRESET_TIMES:
        row.append(InlineKeyboardButton(tm, callback_data=f"{prefix}:{tm}"))
        if len(row) == 4:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("✏️", callback_data=f"{prefix}:custom")])
    rows.append([InlineKeyboardButton("◀️", callback_data="settings:main")])
    return InlineKeyboardMarkup(rows)

def build_week_keyboard(lang, prefix="settings:setweek") -> InlineKeyboardMarkup:
    days = I18N[lang]["days_short"]
    row1 = [InlineKeyboardButton(days[i], callback_data=f"{prefix}:{i}") for i in range(4)]
    row2 = [InlineKeyboardButton(days[i], callback_data=f"{prefix}:{i}") for i in range(4, 7)]
    return InlineKeyboardMarkup([row1, row2, [InlineKeyboardButton("◀️", callback_data="settings:main")]])

def build_group_keyboard(uid, lang) -> InlineKeyboardMarkup:
    group = get_owner_group(uid)
    memberships = user_groups(uid)
    buttons = []
    if not group:
        buttons.append([InlineKeyboardButton(t(lang, "group_btn_new"),     callback_data="group:new")])
    else:
        buttons.append([InlineKeyboardButton(t(lang, "group_btn_mine"),    callback_data="group:info")])
        buttons.append([InlineKeyboardButton(t(lang, "group_btn_link"),    callback_data="group:link")])
        buttons.append([InlineKeyboardButton(t(lang, "group_btn_members"), callback_data="group:members")])
        buttons.append([InlineKeyboardButton(t(lang, "group_btn_report"),  callback_data="group:report")])
    if memberships:
        buttons.append([InlineKeyboardButton(t(lang, "group_btn_leave"),   callback_data="group:leave")])
    return InlineKeyboardMarkup(buttons)

# ── Onboarding ────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username, u.first_name)
    lang = user_lang(u.id)
    user = get_user(u.id)

    # Handle group invite deep link
    if context.args and context.args[0].startswith("join_"):
        gid = context.args[0][5:]
        group = get_group(gid)
        if not group:
            await update.message.reply_text(t(lang, "group_not_found"))
            return
        if group["owner_id"] == u.id:
            await update.message.reply_text("👑")
            return
        if is_member(gid, u.id):
            await update.message.reply_text(t(lang, "group_already"))
            return
        add_member(gid, u.id)
        await update.message.reply_text(t(lang, "group_joined", name=group["name"]), parse_mode="Markdown")
        return

    # First-time onboarding
    if not user or not user["onboarded"]:
        await update.message.reply_text(
            t(lang, "onboard_welcome"),
            parse_mode="Markdown",
            reply_markup=build_lang_keyboard(prefix="onboard:lang"),
        )
        return

    today = datetime.now(TZ).date().isoformat()
    await update.message.reply_text(
        t(lang, "welcome", name=u.first_name) + "\n\n" + build_text(u.id, today, datetime.now(TZ).weekday()),
        parse_mode="Markdown",
        reply_markup=build_reply_keyboard(lang),
    )
    await update.message.reply_text(
        "👇", reply_markup=build_keyboard(u.id, today)
    )

# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = user_lang(uid)
    with db() as c:
        c.execute("UPDATE users SET active=0 WHERE user_id=?", (uid,))
    await update.message.reply_text(t(lang, "stopped"))

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_stats(update.effective_user.id, update.message.reply_text)

async def show_stats(uid, reply_fn):
    user = get_user(uid)
    if not user:
        await reply_fn("Please /start first.")
        return
    lang = user["lang"]
    streak = get_streak(uid)
    day_name = I18N[lang]["days"][user["week_start"]]
    rows, week_start = week_rows(uid, user["week_start"])
    lines = [t(lang, "stats_header", streak=streak, day=day_name),
             t(lang, "stats_week", from_date=week_start.strftime("%m/%d"))]
    for d, done in rows:
        bar = progress_bar(done, len(TASKS))
        lines.append(f"  {d.strftime('%m/%d')} {bar} {done}/{len(TASKS)}")
    await reply_fn("\n".join(lines), parse_mode="Markdown")

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_settings(update.effective_user.id, update.message.reply_text)

async def show_settings(uid, reply_fn):
    lang = user_lang(uid)
    await reply_fn(t(lang, "settings_title"), parse_mode="Markdown", reply_markup=build_settings_keyboard(uid))

async def _set_lang(update, context, lang_code):
    u = update.effective_user
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users (user_id,username,first_name,active) VALUES (?,?,?,0)",
                  (u.id, u.username or "", u.first_name or ""))
        c.execute("UPDATE users SET lang=? WHERE user_id=?", (lang_code, u.id))
    await update.message.reply_text(t(lang_code, "lang_set"))

async def cmd_lang(update, context):
    u = update.effective_user
    if not context.args or context.args[0] not in I18N:
        await update.message.reply_text("🌐", reply_markup=build_lang_keyboard())
        return
    await _set_lang(update, context, context.args[0])

# ── Menu text handler ─────────────────────────────────────────────────────────

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_lang(uid)
    text = update.message.text
    m    = MENU[lang]
    today = datetime.now(TZ).date().isoformat()

    if text == m["today"]:
        msg = build_text(uid, today, datetime.now(TZ).weekday())
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=build_reply_keyboard(lang))
        await update.message.reply_text("👇", reply_markup=build_keyboard(uid, today))

    elif text == m["stats"]:
        await show_stats(uid, update.message.reply_text)

    elif text == m["group"]:
        await update.message.reply_text(
            t(lang, "group_menu"), parse_mode="Markdown",
            reply_markup=build_group_keyboard(uid, lang),
        )

    elif text == m["settings"]:
        await show_settings(uid, update.message.reply_text)

# ── Unknown message handler ───────────────────────────────────────────────────

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_lang(uid)
    await update.message.reply_text(
        t(lang, "unknown"),
        reply_markup=build_reply_keyboard(lang),
    )

# ── Group name conversation ───────────────────────────────────────────────────

async def group_ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = user_lang(query.from_user.id)
    if get_owner_group(query.from_user.id):
        await query.message.reply_text(t(lang, "group_exists"))
        return ConversationHandler.END
    await query.message.reply_text(t(lang, "group_ask_name"), parse_mode="Markdown")
    return GROUP_NAME

async def group_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_lang(uid)
    name = update.message.text.strip()
    if get_owner_group(uid):
        await update.message.reply_text(t(lang, "group_exists"))
        return ConversationHandler.END
    gid  = create_group(uid, name)
    me   = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start=join_{gid}"
    await update.message.reply_text(t(lang, "group_created", name=name, link=link), parse_mode="Markdown")
    return ConversationHandler.END

async def group_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang(update.effective_user.id)
    await update.message.reply_text(t(lang, "report_cancel"))
    return ConversationHandler.END

# ── Report conversation ───────────────────────────────────────────────────────

async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = query.from_user.id
    lang = user_lang(uid)
    if not get_owner_group(uid):
        await query.message.reply_text(t(lang, "not_owner"), parse_mode="Markdown")
        return ConversationHandler.END
    context.user_data["report_gid"] = get_owner_group(uid)["group_id"]
    await query.message.reply_text(t(lang, "report_ask_from"), parse_mode="Markdown")
    return REPORT_FROM

async def report_get_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_lang(uid)
    d = parse_date(update.message.text)
    if not d:
        await update.message.reply_text(t(lang, "report_date_bad"))
        return REPORT_FROM
    context.user_data["report_from"] = d
    await update.message.reply_text(t(lang, "report_ask_to"), parse_mode="Markdown")
    return REPORT_TO

async def report_get_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_lang(uid)
    d    = parse_date(update.message.text)
    if not d:
        await update.message.reply_text(t(lang, "report_date_bad"))
        return REPORT_TO
    from_date = context.user_data.pop("report_from", None)
    if d < from_date:
        await update.message.reply_text(t(lang, "report_range_bad"))
        return REPORT_TO
    gid     = context.user_data.pop("report_gid", None)
    group   = get_group(gid)
    members = get_members(gid)
    if not members:
        await update.message.reply_text(t(lang, "report_no_members"))
        return ConversationHandler.END
    days = (d - from_date).days + 1
    lines = [t(lang, "report_title",
               name=group["name"],
               from_date=from_date.strftime("%m/%d"),
               to_date=d.strftime("%m/%d"))]
    for member in members:
        mid  = member["user_id"]
        name = member["first_name"] or member["username"] or str(mid)
        total_done, icons = 0, []
        cur = from_date
        while cur <= d:
            qtys = get_quantities(mid, cur.isoformat())
            done    = sum(1 for k, g, _, _ in TASKS if qtys.get(k, 0) >= g)
            partial = sum(1 for k, g, _, _ in TASKS if 0 < qtys.get(k, 0) < g)
            total_done += done
            icons.append("✅" if done == len(TASKS) else ("🔶" if done or partial else "⬜"))
            cur += timedelta(days=1)
        pct = round(total_done / (days * len(TASKS)) * 100)
        lines.append(f"\n👤 *{name}* — {total_done}/{days*len(TASKS)} ({pct}%)")
        lines.append("".join(icons))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    return ConversationHandler.END

async def report_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang(update.effective_user.id)
    context.user_data.pop("report_gid", None)
    context.user_data.pop("report_from", None)
    await update.message.reply_text(t(lang, "report_cancel"))
    return ConversationHandler.END

# ── Custom-amount conversation ────────────────────────────────────────────────

async def btn_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = query.from_user.id
    lang = user_lang(uid)
    _, date_str, key = query.data.split(":", 2)
    task = next(task for task in TASKS if task[0] == key)
    _, goal, units, names = task
    context.user_data["pending_add"] = {"date_str": date_str, "key": key}
    await query.message.reply_text(
        t(lang, "enter_prompt",
          unit=units.get(lang, units["tr"]),
          name=names.get(lang, names["tr"])),
        parse_mode="Markdown",
    )
    return ENTER_AMOUNT

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid     = update.effective_user.id
    lang    = user_lang(uid)
    pending = context.user_data.get("pending_add")
    if not pending:
        return ConversationHandler.END
    try:
        amount = int(update.message.text.strip())
        if amount <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text(t(lang, "enter_invalid"))
        return ENTER_AMOUNT
    date_str = pending["date_str"]
    key      = pending["key"]
    context.user_data.pop("pending_add", None)
    add_quantity(uid, date_str, key, amount)
    text     = build_text(uid, date_str, datetime.now(TZ).weekday())
    keyboard = build_keyboard(uid, date_str)
    if all_done_today(uid, date_str):
        text += t(lang, "all_done")
        mil = milestone_msg(lang, get_streak(uid))
        if mil: text += f"\n\n{mil}"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def cancel_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang(update.effective_user.id)
    context.user_data.pop("pending_add", None)
    await update.message.reply_text(t(lang, "enter_cancel"))
    return ConversationHandler.END

# ── Custom time conversation ──────────────────────────────────────────────────

async def ask_custom_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = user_lang(query.from_user.id)
    await query.message.reply_text(t(lang, "time_ask"), parse_mode="Markdown")
    return ENTER_TIME

async def receive_custom_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = user_lang(uid)
    try:
        datetime.strptime(update.message.text.strip(), "%H:%M")
    except ValueError:
        await update.message.reply_text(t(lang, "time_invalid"), parse_mode="Markdown")
        return ENTER_TIME
    time_str = update.message.text.strip()
    with db() as c:
        c.execute("UPDATE users SET reminder_time=? WHERE user_id=?", (time_str, uid))
    await update.message.reply_text(t(lang, "time_set", time=time_str), parse_mode="Markdown")
    return ConversationHandler.END

async def cancel_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌")
    return ConversationHandler.END

# ── Inline button handler ─────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = query.from_user.id
    lang = user_lang(uid)
    data = query.data

    # ── Onboarding ──
    if data.startswith("onboard:lang:"):
        new_lang = data.split(":")[-1]
        with db() as c:
            c.execute("UPDATE users SET lang=? WHERE user_id=?", (new_lang, uid))
        await query.edit_message_text(
            t(new_lang, "onboard_time"),
            reply_markup=build_time_keyboard(prefix="onboard:time"),
        )
        return

    if data.startswith("onboard:time:"):
        time_val = data.split(":", 2)[-1]
        if time_val == "custom":
            await query.message.reply_text(t(lang, "time_ask"), parse_mode="Markdown")
            context.user_data["time_context"] = "onboard"
            # handled by custom time conversation
            return
        with db() as c:
            c.execute("UPDATE users SET reminder_time=?, onboarded=1 WHERE user_id=?", (time_val, uid))
        today = datetime.now(TZ).date().isoformat()
        await query.edit_message_text(t(lang, "onboard_done", time=time_val), parse_mode="Markdown")
        await query.message.reply_text(
            build_text(uid, today, datetime.now(TZ).weekday()),
            parse_mode="Markdown",
            reply_markup=build_reply_keyboard(lang),
        )
        await query.message.reply_text("👇", reply_markup=build_keyboard(uid, today))
        return

    # ── Settings ──
    if data == "settings:main":
        await query.edit_message_text(t(lang, "settings_title"), parse_mode="Markdown",
                                      reply_markup=build_settings_keyboard(uid))
        return
    if data == "settings:lang":
        await query.edit_message_text(t(lang, "lang_picker"),
                                      reply_markup=build_lang_keyboard())
        return
    if data.startswith("settings:setlang:"):
        new_lang = data.split(":")[-1]
        with db() as c:
            c.execute("UPDATE users SET lang=? WHERE user_id=?", (new_lang, uid))
        await query.edit_message_text(t(new_lang, "settings_title"), parse_mode="Markdown",
                                      reply_markup=build_settings_keyboard(uid))
        return
    if data == "settings:time":
        await query.edit_message_text(t(lang, "time_picker"), parse_mode="Markdown",
                                      reply_markup=build_time_keyboard())
        return
    if data.startswith("settings:settime:"):
        time_val = data.split(":", 2)[-1]
        if time_val == "custom":
            await query.message.reply_text(t(lang, "time_ask"), parse_mode="Markdown")
            return
        with db() as c:
            c.execute("UPDATE users SET reminder_time=? WHERE user_id=?", (time_val, uid))
        await query.edit_message_text(t(lang, "settings_title"), parse_mode="Markdown",
                                      reply_markup=build_settings_keyboard(uid))
        return
    if data == "settings:week":
        await query.edit_message_text(t(lang, "week_picker"),
                                      reply_markup=build_week_keyboard(lang))
        return
    if data.startswith("settings:setweek:"):
        day_num = int(data.split(":")[-1])
        day_name = I18N[lang]["days"][day_num]
        with db() as c:
            c.execute("UPDATE users SET week_start=? WHERE user_id=?", (day_num, uid))
        await query.edit_message_text(t(lang, "settings_title"), parse_mode="Markdown",
                                      reply_markup=build_settings_keyboard(uid))
        return
    if data == "settings:help":
        await query.edit_message_text(t(lang, "help_text"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton(t(lang, "btn_back"), callback_data="settings:main")
                                      ]]))
        return

    # ── Group ──
    if data == "group:info":
        group = get_owner_group(uid)
        if not group:
            await query.answer(t(lang, "not_owner"), show_alert=True)
            return
        cnt = member_count(group["group_id"])
        await query.edit_message_text(t(lang, "group_info", name=group["name"], count=cnt),
                                      parse_mode="Markdown",
                                      reply_markup=build_group_keyboard(uid, lang))
        return
    if data == "group:link":
        group = get_owner_group(uid)
        if not group:
            await query.answer(t(lang, "not_owner"), show_alert=True)
            return
        me   = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start=join_{group['group_id']}"
        await query.message.reply_text(t(lang, "group_link_msg", link=link), parse_mode="Markdown")
        return
    if data == "group:members":
        group = get_owner_group(uid)
        if not group:
            await query.answer(t(lang, "not_owner"), show_alert=True)
            return
        members = get_members(group["group_id"])
        if not members:
            await query.answer(t(lang, "group_no_members"), show_alert=True)
            return
        names = "\n".join(f"• {m['first_name'] or m['username'] or str(m['user_id'])}" for m in members)
        await query.message.reply_text(
            t(lang, "group_members_title", name=group["name"]) + "\n" + names,
            parse_mode="Markdown",
        )
        return
    if data == "group:leave":
        memberships = user_groups(uid)
        if not memberships:
            await query.answer(t(lang, "group_not_member"), show_alert=True)
            return
        for g in memberships:
            remove_member(g["group_id"], uid)
        await query.answer(t(lang, "group_left"), show_alert=True)
        await query.edit_message_text(t(lang, "group_menu"), parse_mode="Markdown",
                                      reply_markup=build_group_keyboard(uid, lang))
        return

    # ── Task actions ──
    date_str = None
    if data.startswith("alldone:"):
        date_str = data.split(":", 1)[1]
        for key, goal, _, _ in TASKS:
            set_quantity(uid, date_str, key, goal)
    elif data.startswith("done:"):
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
        date_str = data.split(":", 1)[1]
        reset_day(uid, date_str)
    else:
        return

    text     = build_text(uid, date_str, datetime.now(TZ).weekday())
    keyboard = build_keyboard(uid, date_str)
    done     = all_done_today(uid, date_str)
    qtys     = get_quantities(uid, date_str)
    remaining = sum(1 for k, g, _, _ in TASKS if not is_done(qtys.get(k, 0), g))

    if done:
        text += t(lang, "all_done")
        mil = milestone_msg(lang, get_streak(uid))
        if mil: text += f"\n\n{mil}"
    elif remaining == 1:
        await query.answer(t(lang, "almost_there"), show_alert=False)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ── Scheduled jobs ────────────────────────────────────────────────────────────

async def job_reminders(context: ContextTypes.DEFAULT_TYPE):
    now      = datetime.now(TZ)
    time_str = now.strftime("%H:%M")
    today    = now.date().isoformat()
    for user in all_active_users():
        if user["reminder_time"] != time_str or not user["onboarded"]:
            continue
        uid  = user["user_id"]
        lang = user["lang"]
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=build_text(uid, today, now.weekday()),
                parse_mode="Markdown",
                reply_markup=build_reply_keyboard(lang),
            )
            kb = build_keyboard(uid, today)
            if kb:
                await context.bot.send_message(chat_id=uid, text="👇", reply_markup=kb)
        except Exception as e:
            logger.warning("Reminder failed for %s: %s", uid, e)

async def job_evening_nudge(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(TZ).date().isoformat()
    for user in all_active_users():
        if not user["onboarded"]: continue
        uid  = user["user_id"]
        lang = user["lang"]
        qtys = get_quantities(uid, today)
        remaining = sum(1 for k, g, _, _ in TASKS if not is_done(qtys.get(k, 0), g))
        if remaining == 0: continue
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
    yesterday = now.date() - timedelta(days=1)
    for user in all_active_users():
        if user["week_start"] != now.weekday() or not user["onboarded"]: continue
        uid  = user["user_id"]
        lang = user["lang"]
        week_start = yesterday - timedelta(days=6)
        perfect = total = 0
        lines = [t(lang, "weekly_title",
                   from_date=week_start.strftime("%m/%d"),
                   to_date=yesterday.strftime("%m/%d"))]
        for i in range(7):
            d    = week_start + timedelta(days=i)
            qtys = get_quantities(uid, d.isoformat())
            done = sum(1 for k, g, _, _ in TASKS if qtys.get(k, 0) >= g)
            total += done
            if done == len(TASKS): perfect += 1
            bar = progress_bar(done, len(TASKS))
            lines.append(f"{d.strftime('%m/%d')} {bar} {done}/{len(TASKS)}")
        pct     = round(total / (7 * len(TASKS)) * 100)
        day_name = I18N[lang]["days"][user["week_start"]]
        msg_key = "weekly_great" if perfect == 7 else "weekly_good" if perfect >= 5 else "weekly_ok"
        lines  += ["", t(lang, "weekly_stats", perfect=perfect, pct=pct),
                   t(lang, msg_key), t(lang, "weekly_next", day=day_name)]
        try:
            await context.bot.send_message(chat_id=uid, text="\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            logger.warning("Weekly summary failed for %s: %s", uid, e)

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("stop",    cmd_stop))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("lang",    cmd_lang))
    app.add_handler(CommandHandler("english", lambda u, c: _set_lang(u, c, "en")))
    app.add_handler(CommandHandler("turkish", lambda u, c: _set_lang(u, c, "tr")))
    app.add_handler(CommandHandler("kyrgyz",  lambda u, c: _set_lang(u, c, "ky")))
    app.add_handler(CommandHandler("russian", lambda u, c: _set_lang(u, c, "ru")))

    # Report conversation (triggered by inline button group:report)
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(report_start, pattern="^group:report$")],
        states={
            REPORT_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_get_from)],
            REPORT_TO:   [MessageHandler(filters.TEXT & ~filters.COMMAND, report_get_to)],
        },
        fallbacks=[CommandHandler("cancel", report_cancel)],
    ))

    # Group name conversation (triggered by inline button group:new)
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(group_ask_name, pattern="^group:new$")],
        states={GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, group_create)]},
        fallbacks=[CommandHandler("cancel", group_cancel)],
    ))

    # Custom time conversation (triggered by settings:settime:custom or onboard:time:custom)
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_custom_time, pattern=r"^(settings:settime|onboard:time):custom$")],
        states={ENTER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_time)]},
        fallbacks=[CommandHandler("cancel", cancel_time)],
    ))

    # Custom amount conversation (triggered by enter: button)
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(btn_enter_amount, pattern="^enter:")],
        states={ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)]},
        fallbacks=[CommandHandler("cancel", cancel_enter)],
    ))

    # General inline button handler
    app.add_handler(CallbackQueryHandler(button_handler))

    # Reply keyboard menu handler
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(
        "|".join(map(lambda s: f"^{s}$", ALL_MENU_TEXTS))
    ), handle_menu))

    # Unknown message fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

    app.job_queue.run_repeating(job_reminders,      interval=60, first=5)
    app.job_queue.run_daily(job_evening_nudge,  time=dtime(18, 0))
    app.job_queue.run_daily(job_weekly_summary, time=dtime(5, 0))

    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
