# app/bot/handler.py

from bot.keyboards import main_keyboard
from bot.helpers import send_message, send_buttons
from core.members import find_member, add_member_if_not_exists, mark_welcomed
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_pending, update_task_status
from core.messages import get_random_message
from core.state import clear_user_state


# =================================================================
#   پردازش UPDATE (Message + Callback)
# =================================================================
def process_update(update):
    try:
        # ----------------------------
        #   اگر callback بود
        # ----------------------------
        if "callback_query" in update:
            return process_callback(update["callback_query"])

        # ----------------------------
        #   اگر message نبود
        # ----------------------------
        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        print("CHAT_ID =", chat_id)

        # ----------------------------
        #   پیدا کردن کاربر
        # ----------------------------
        user = find_member(chat_id)

        if not user:
            add_member_if_not_exists(
                chat_id=chat_id,
                name=chat.get("first_name", "") or "",
                username=chat.get("username", "") or ""
            )
            return send_message(
                chat_id,
                "👋 سلام! شما در سیستم ثبت نشده‌اید."
            )

        # ----------------------------
        # خوش‌آمد (فقط یک بار)
        # ----------------------------
        if user.get("welcomed") != "Yes":
            mark_welcomed(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname'] or user['name']} عزیز! 👋",
                main_keyboard()
            )

        # ----------------------------
        #   دستور /start
        # ----------------------------
        if text == "/start":
            clear_user_state(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname']} عزیز! 🌟",
                main_keyboard()
            )

        # ----------------------------
        #   منوی اصلی
        # ----------------------------
        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        # ----------------------------
        # اگر هیچی نبود
        # ----------------------------
        return send_message(chat_id, "❗ لطفاً از دکمه‌های منو استفاده کن.")

    except Exception as e:
        send_message(341781615, f"⚠ خطای بات:\n{str(e)}")
        print("PROCESS_UPDATE ERROR:", e)
        return



# =================================================================
# پردازش Callback (DONE / NOT_DONE)
# =================================================================
def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("DONE::"):
        title = data.replace("DONE::", "")
        update_task_status(title, "Done")
        send_message(chat_id, f"🎉 عالی! «{title}» تحویل شد ✔️")
        return

    if data.startswith("NOT_DONE::"):
        title = data.replace("NOT_DONE::", "")
        return send_message(chat_id, f"🔔 باشه! «{title}» هنوز انجام نشده.")

    return send_message(chat_id, "❗ داده نامعتبر.")



# =================================================================
#   ارسال کارهای امروز (بدون پیام‌های فان)
# =================================================================
def send_today(chat_id, user):
    team = user["team"]
    tasks = get_tasks_today(team)

    if not tasks:
        return send_message(chat_id, "🌤️ امروز هیچ کاری ثبت نشده.")

    for t in tasks:
        title = t['title']
        date_fa = t["date_fa"]
        status = t["status"]

        txt = (
            f"📌 *تسک امروز - تیم {team}*\n"
            f"📅 {date_fa}\n"
            f"✏️ *{title}*\n\n"
        )

        send_message(chat_id, txt)



# =================================================================
#   ارسال کارهای هفته + پیام رندوم WEEK
# =================================================================
def send_week(chat_id, user):
    team = user["team"]
    tasks = get_tasks_week(team)

    if not tasks:
        return send_message(chat_id, "📆 برای این هفته کاری ثبت نیست.")

    header = get_random_message("WEEK", TEAM=team)

    send_message(chat_id, header + "\n\n")

    for t in tasks:
        text = (
            f"👥 *{team}*\n"
            f"📅 {t['date_fa']}\n"
            f"✏️ {t['title']}\n"
        )
        send_message(chat_id, text)



# =================================================================
#   ارسال Pending + انتخاب پیام بر اساس وضعیت
# =================================================================
def send_pending(chat_id, user):
    team = user["team"]
    tasks = get_tasks_pending(team)

    if not tasks:
        return send_message(chat_id, "🎉 همه کارها انجام شده! عالیه 👌")

    for t in tasks:
        title = t["title"]
        date_fa = t["date_fa"]
        delay = t["delay_days"]
        deadline = t["deadline_date"]

        #  انتخاب نوع پیام
        if delay > 5:
            msg_type = "ESC"
        elif delay > 0:
            msg_type = "OVR"
        elif delay == 0:
            msg_type = "DUE"
        elif delay == -2:
            msg_type = "PRE2"
        else:
            msg_type = "DUE"

        #  متن فان
        funny = get_random_message(
            msg_type,
            NAME=user["customname"],
            TEAM=team,
            TITLE=title,
            DAYS=delay,
            DATE_FA=date_fa
        )

        # متن اصلی
        text = (
            f"📌 *تسک انجام‌نشده تیم {team}*\n"
            f"📅 {date_fa}\n"
            f"✏️ *{title}*\n\n"
            f"{funny}"
        )

        #  ESC پیام مدیریت
        if msg_type == "ESC":
            send_message(341781615, f"⚠ *ESCALATION*\n{funny}")

        # دکمه‌ها (فقط در DUE و OVR)
        if msg_type in ["DUE", "OVR"]:
            buttons = [
                [
                    {"text": "✔️ بله تحویل دادم", "callback_data": f"DONE::{title}"},
                    {"text": "❌ نه هنوز تحویل ندادم", "callback_data": f"NOT_DONE::{title}"}
                ]
            ]
            send_buttons(chat_id, text, buttons)
        else:
            send_message(chat_id, text)
