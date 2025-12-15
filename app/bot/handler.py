# app/bot/handler.py
import random
from datetime import datetime
from dateutil import parser
import pytz

from core.sheets import get_sheet, update_cell
from bot.helpers import send_message
from bot.keyboards import main_keyboard
from core.members import find_member, add_member_if_not_exists
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_pending  # از tasks.py استفاده کن اگر وجود داره، یا منطق رو اینجا کپی کن

# اگر tasks.py درست کار نمی‌کنه، منطق رو اینجا بگذار (از کد قبلی کپی کردم)
# اما اولویت با import از core.tasks

IRAN_TZ = pytz.timezone("Asia/Tehran")

def get_random_message():
    try:
        rows = get_sheet("RandomMessages")
        msgs = [r[0].strip() for r in rows[1:] if r and r[0].strip()]
        if msgs:
            return random.choice(msgs)
    except:
        pass
    return "یادت نره تسک‌هاتو انجام بدی! ⏰"

# ------------------- توابع ارسال برای scheduler -------------------
def send_week(chat_id, user_info=None):
    """ارسال لیست کارهای هفته (برای weekly job)"""
    member = find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks = get_tasks_week(team)  # از core.tasks
    if not tasks:
        send_message(chat_id, "این هفته کاری نداری! عالیه 👍")
    else:
        msg = "<b>کارهای این هفته:</b>\n\n"
        for t in tasks:
            msg += f"• {t['title']} ({t['date_fa']})\n"
        send_message(chat_id, msg)

def send_pending(chat_id, user_info=None):
    """ارسال تسک‌های انجام نشده (overdue + امروز) برای daily job"""
    member = find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks_today = get_tasks_today(team)
    tasks_overdue = get_tasks_pending(team)  # یا overdue جدا
    msg = ""
    if tasks_today:
        msg += "<b>کارهای امروز:</b>\n\n"
        for t in tasks_today:
            msg += f"• {t['title']} ({t['date_fa']})\n\n"
    if tasks_overdue:
        random_msg = get_random_message()
        msg += f"{random_msg}\n\n<b>تسک‌های عقب افتاده:</b>\n\n"
        for t in tasks_overdue:
            days_text = "امروز" if t.get("delay_days", 0) == 0 else f"{t['delay_days']} روز گذشته"
            msg += f"• {t['title']} ({days_text})\n"
    if not msg:
        send_message(chat_id, "هیچ تسک انجام نشده‌ای نداری! عالیه ✅")
    else:
        send_message(chat_id, msg or "تسک جدیدی نداری!")

# ------------------- هندلر اصلی webhook -------------------
def process_update(update):
    if "message" not in update:
        # هندل callback برای "تحویل دادم"
        if "callback_query" in update:
            cb = update["callback_query"]
            data = cb.get("data", "")
            chat_id = cb["message"]["chat"]["id"]
            if data.startswith("done|"):
                task_id = data.split("|")[1]
                from core.tasks import update_task_status
                if update_task_status(task_id, "done"):
                    send_message(chat_id, "عالی! تسک انجام شد ✅")
                else:
                    send_message(chat_id, "تسک پیدا نشد!")
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    user = message.get("from", {})

    add_member_if_not_exists(chat_id, user.get("first_name"), user.get("username"))

    member = find_member(chat_id)
    if not member or not member.get("team"):
        send_message(chat_id, "تیم شما ثبت نشده! با ادمین تماس بگیر.")
        return

    team = member["team"]

    if text in ["/strat", "/start"]:
        send_message(chat_id, "سلام! خوش برگشتی 👋", main_keyboard())

    elif text == "لیست کارهای امروز":
        tasks = get_tasks_today(team)
        if not tasks:
            send_message(chat_id, "امروز کاری نداری! 👍")
        else:
            msg = "<b>کارهای امروز:</b>\n\n"
            for t in tasks:
                msg += f"• {t['title']} ({t['date_fa']})\n\n"
            send_message(chat_id, msg)

    elif text == "لیست کارهای هفته":
        send_week(chat_id)

    elif text == "تسک های انجام نشده":
        send_pending(chat_id)

    # می‌تونی دکمه inline اضافه کنی برای تحویل دادم در لیست overdue
