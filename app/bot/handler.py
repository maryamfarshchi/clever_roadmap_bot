# app/bot/handler.py
from bot.keyboards import main_keyboard
from bot.helpers import send_message
from core.members import find_member
from core.tasks import get_tasks_for
from core.messages import get_random_message
from core.state import get_user_state, set_user_state, clear_user_state

# ============================================================
#  پردازش آپدیت‌های دریافتی تلگرام
# ============================================================
def process_update(update):
    if "message" not in update:
        return

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    user = find_member(chat_id)

    # ============================================================
    #  ثبت کاربر جدید
    # ============================================================
    if not user:
        send_message(chat_id,
                     "سلام! 👋\nشما در سیستم ثبت نشده‌اید.\n"
                     "لطفاً با مدیر سیستم تماس بگیرید تا در *members sheet* اضافه شوید.")
        return

    state = get_user_state(chat_id)

    # ============================================================
    #  فرمان‌های ثابت منو
    # ============================================================
    if text == "لیست کارهای امروز":
        return send_today(chat_id, user)

    if text == "لیست کارهای هفته":
        return send_week(chat_id, user)

    if text == "تسک های انجام نشده":
        return send_pending(chat_id, user)

    if text == "/start":
        clear_user_state(chat_id)
        return send_message(chat_id,
                            f"سلام {user['customname']} عزیز! 🌟\n"
                            "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                            main_keyboard())

    # حالت‌های خاص در صورت نیاز…
    send_message(chat_id, "گزینه نامعتبر است. لطفاً از منو استفاده کنید.")


# ============================================================
#  ارسال «کارهای امروز»
# ============================================================
def send_today(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="today")

    if not tasks:
        return send_message(chat_id, "برای امروز هیچ کاری ثبت نشده 🌤️")

    text = f"📅 *کارهای امروز ({team})*\n\n"

    for t in tasks:
        line = f"🔹 *{t['title']}* ({t['type']})\n"
        if t['time']:
            line += f"⏰ ساعت: {t['time']}\n"
        if t['comment']:
            line += f"💬 توضیح: {t['comment']}\n"
        text += line + "\n"

    send_message(chat_id, text)


# ============================================================
#  ارسال «کارهای هفته»
# ============================================================
def send_week(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="week")

    if not tasks:
        return send_message(chat_id, "برای این هفته کاری ثبت نشده 📆")

    text = f"📆 *لیست کارهای هفته ({team})*\n\n"

    for t in tasks:
        line = f"🔸 *{t['title']}* ({t['type']})\n"
        line += f"📅 تاریخ: {t['date']}\n"
        if t['time']:
            line += f"⏰ {t['time']}\n"
        text += line + "\n"

    send_message(chat_id, text)


# ============================================================
#  ارسال «تسک‌های انجام نشده»
# ============================================================
def send_pending(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="pending")

    if not tasks:
        return send_message(chat_id, "🎉 همه کارها انجام شده! عالیه")

    text = f"⚠ *کارهای انجام نشده ({team})*\n\n"

    for t in tasks:
        message = get_random_message(
            "DUE",
            NAME=user["customname"],
            TEAM=user["team"],
            TITLE=t["title"],
        )
        line = message + "\n\n"
        text += line

    send_message(chat_id, text)
