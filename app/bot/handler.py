# app/bot/handler.py

from bot.keyboards import main_keyboard
from bot.helpers import send_message, send_buttons
from core.members import find_member, add_member_if_not_exists, mark_welcomed
from core.tasks import get_tasks_for
from core.messages import get_random_message
from core.state import clear_user_state


# ============================================================
#  پردازش آپدیت (Message + CallbackQuery)
# ============================================================
def process_update(update):
    try:
        # ----------------------------------------------------
        #  اگر CallbackQuery بود
        # ----------------------------------------------------
        if "callback_query" in update:
            return process_callback(update["callback_query"])

        # ----------------------------------------------------
        #  فقط Message
        # ----------------------------------------------------
        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        print("CHAT_ID =", chat_id)

        # ----------------------------------------------------
        #  پیدا کردن کاربر در members
        # ----------------------------------------------------
        user = find_member(chat_id)

        if not user:
            add_member_if_not_exists(
                chat_id=chat_id,
                name=chat.get("first_name", "") or "",
                username=chat.get("username", "") or ""
            )

            return send_message(
                chat_id,
                "👋 سلام! شما در سیستم ثبت نشده‌اید.\n"
                "لطفاً با مدیر سیستم تماس بگیرید تا در *members sheet* اضافه شوید."
            )

        # ----------------------------------------------------
        # خوش‌آمدگویی (فقط یک بار)
        # ----------------------------------------------------
        if user.get("welcomed", "") != "Yes":
            mark_welcomed(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname'] or user['name']} عزیز! 👋\n"
                "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                main_keyboard()
            )

        # ----------------------------------------------------
        # فرمان /start
        # ----------------------------------------------------
        if text == "/start":
            clear_user_state(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname']} عزیز! 🌟\n"
                "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                main_keyboard()
            )

        # ----------------------------------------------------
        # منو
        # ----------------------------------------------------
        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        # ----------------------------------------------------
        # گزینه نامعتبر
        # ----------------------------------------------------
        return send_message(chat_id, "❗ لطفاً از دکمه‌های منو استفاده کن.")

    except Exception as e:
        send_message(341781615, f"⚠ خطای بات:\n{str(e)}")
        print("PROCESS_UPDATE ERROR:", e)
        return



# ============================================================
#  پردازش Callback های دکمه‌ها
# ============================================================
def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("DONE::"):
        title = data.replace("DONE::", "")
        return send_message(chat_id, f"🎉 عالی! «{title}» تحویل شد. مرسی ازت ✔️")

    if data.startswith("NOT_DONE::"):
        title = data.replace("NOT_DONE::", "")
        return send_message(chat_id, f"🔔 اوکی! «{title}» هنوز انجام نشده. یادم باشه پیگیری کنم ❗")

    return send_message(chat_id, "❗ داده نامعتبر.")



# ============================================================
#  ارسال «کارهای امروز»
# ============================================================
def send_today(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="today")

    if not tasks:
        return send_message(chat_id, "🌤️ امروز هیچ کاری ثبت نشده.")

    text = f"📅 *کارهای امروز ({team})*\n\n"
    for t in tasks:
        line = f"🔹 *{t['title']}* ({t['type']})\n"
        if t.get('time'):
            line += f"⏰ ساعت: {t['time']}\n"
        if t.get('comment'):
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
        return send_message(chat_id, "📆 برای این هفته کاری ثبت نیست.")

    text = f"📆 *لیست کارهای هفته ({team})*\n\n"
    for t in tasks:
        line = f"🔸 *{t['title']}* ({t['type']})\n"
        line += f"📅 تاریخ: {t['date']}\n"
        if t.get('time'):
            line += f"⏰ {t['time']}\n"
        text += line + "\n"

    send_message(chat_id, text)



# ============================================================
#  ارسال «تسک‌های انجام نشده» با دکمه + پیام فان
# ============================================================
def send_pending(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="pending")

    if not tasks:
        return send_message(chat_id, "🎉 همه کارها انجام شده! عالیه 👌")

    for t in tasks:
        title = t.get("title", "")
        date = t.get("date", "")
        date_fa = t.get("date_fa", date)
        delay_days = t.get("delay_days", 0)

        # -------------------------
        # انتخاب نوع پیام
        # -------------------------
        if delay_days > 0:
            msg_type = "OVR"     # task is overdue
        else:
            msg_type = "DUE"     # deadline is today

        # -------------------------
        # ساخت پیام نهایی
        # -------------------------
        funny = get_random_message(
            msg_type,
            NAME=user["customname"],
            TEAM=team,
            TITLE=title,
            DAYS=delay_days,
            DATE_FA=date_fa
        )

        # -------------------------
        # متن نهایی (فرمت مشابه اسکرین‌شات)
        # -------------------------
        text = (
            f"📌 *تسک انجام‌نشده تیم {team}*\n"
            f"📆 *{date_fa}*\n"
            f"✏️ *{title}*\n\n"
            f"{funny}"
        )

        # -------------------------
        # دکمه‌ها
        # -------------------------
        buttons = [
            [
                {"text": "✔️ بله تحویل دادم", "callback_data": f"DONE::{title}"},
                {"text": "❌ نه هنوز تحویل ندادم", "callback_data": f"NOT_DONE::{title}"}
            ]
        ]

        send_buttons(chat_id, text, buttons)
