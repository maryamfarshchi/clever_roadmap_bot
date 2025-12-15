# app/bot/handler.py
import random
from datetime import datetime
from dateutil import parser
import pytz

from core.sheets import get_sheet, update_cell
from bot.helpers import send_message, send_buttons
from bot.keyboards import main_keyboard
from core.members import find_member, add_member_if_not_exists, get_members_by_team

# تنظیمات
WORKSHEET_TASKS = "Tasks"
COL_TASKID = 0
COL_TEAM = 1
COL_DATE_EN = 2
COL_DATE_FA = 3
COL_TIME = 5
COL_TITLE = 6
COL_STATUS = 9
COL_DONE = 18

IRAN_TZ = pytz.timezone("Asia/Tehran")

def _get_tasks_rows():
    rows = get_sheet(WORKSHEET_TASKS)
    if not rows or len(rows) < 2:
        return []
    return rows

def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip().replace("\u200e", "").replace("\u200f", "").replace("\u202a", "")
    try:
        return datetime.strptime(date_str, "%m/%d/%Y")
    except:
        try:
            return parser.parse(date_str, dayfirst=False)
        except:
            return None

def get_days_overdue(date_str):
    due = parse_date(date_str)
    if not due:
        return 0
    today = datetime.now(IRAN_TZ).date()
    return (today - due.date()).days

def is_task_done(row):
    done = str(row[COL_DONE]).strip().upper() if len(row) > COL_DONE else ""
    status = str(row[COL_STATUS]).strip().lower() if len(row) > COL_STATUS else ""
    return done == "YES" or any(k in status for k in ["done", "yes", "انجام شد", "تحویل"])

def get_user_tasks(team, today_only=False):
    rows = _get_tasks_rows()
    tasks = []
    for row in rows[1:]:
        if len(row) <= COL_TEAM or str(row[COL_TEAM]).strip() != team:
            continue
        if is_task_done(row):
            continue
        days = get_days_overdue(row[COL_DATE_EN])
        if days < 0:
            continue
        if today_only and days != 0:
            continue
        time_str = str(row[COL_TIME]).strip() if len(row) > COL_TIME else ""
        time_part = f" ⏰ {time_str}" if time_str else ""
        days_text = " (امروز)" if days == 0 else f" ({days} روز گذشته)" if days > 0 else ""
        tasks.append({
            "task_id": str(row[COL_TASKID]).strip(),
            "title": str(row[COL_TITLE]).strip(),
            "date_fa": str(row[COL_DATE_FA]).strip(),
            "time_part": time_part,
            "days_text": days_text,
            "days": days
        })
    return tasks

def mark_task_done(task_id):
    rows = _get_tasks_rows()
    for i, row in enumerate(rows[1:], start=2):
        if str(row[COL_TASKID]).strip() == task_id:
            update_cell(WORKSHEET_TASKS, i, COL_STATUS + 1, "Done")
            update_cell(WORKSHEET_TASKS, i, COL_DONE + 1, "YES")
            return True
    return False

# ------------------- توابع scheduler -------------------
def send_week(chat_id, user_info=None):
    member = find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks = get_user_tasks(team)
    if not tasks:
        send_message(chat_id, "این هفته کاری نداری! استراحت کن 😎👍")
    else:
        send_message(chat_id, f"📋 <b>کارهای این هفته ({len(tasks)} تسک):</b>")
        for t in tasks:
            msg = f"<b>{t['title']}</b>\n📅 {t['date_fa']}{t['time_part']}{t['days_text']}"
            buttons = [[{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}]]
            send_buttons(chat_id, msg, buttons)

def send_pending(chat_id, user_info=None):
    member = find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks_today = get_user_tasks(team, today_only=True)
    tasks_overdue = [t for t in get_user_tasks(team) if t["days"] > 0]
    
    if tasks_today:
        send_message(chat_id, f"📋 <b>کارهای امروز ({len(tasks_today)} تسک):</b>")
        for t in tasks_today:
            msg = f"<b>{t['title']}</b>\n📅 {t['date_fa']}{t['time_part']}{t['days_text']}"
            buttons = [[{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}]]
            send_buttons(chat_id, msg, buttons)
    
    if tasks_overdue:
        send_message(chat_id, "یادت نره تسک‌هاتو انجام بدی! ⏰⚠️")
        send_message(chat_id, f"⚠️ <b>تسک‌های عقب افتاده ({len(tasks_overdue)} تسک):</b>")
        for t in tasks_overdue:
            msg = f"<b>{t['title']}</b>\n📅 {t['date_fa']}{t['time_part']}{t['days_text']}"
            buttons = [
                [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                [{"text": "نه هنوز ⏰", "callback_data": f"notyet|{t['task_id']}"}]
            ]
            send_buttons(chat_id, msg, buttons)
    
    if not tasks_today and not tasks_overdue:
        send_message(chat_id, "تسک انجام نشده‌ای نداری! فوق‌العاده‌ای 🔥✅")

# ------------------- webhook -------------------
def process_update(update):
    if "message" not in update:
        if "callback_query" in update:
            cb = update["callback_query"]
            data = cb.get("data", "")
            chat_id = cb["message"]["chat"]["id"]
            if data.startswith("done|"):
                task_id = data.split("|")[1]
                if mark_task_done(task_id):
                    send_message(chat_id, "عالی! تسک انجام شد ✅")
                else:
                    send_message(chat_id, "تسک پیدا نشد!")
            elif data.startswith("notyet|"):
                send_message(chat_id, "اوکی، بعداً یادآوری می‌کنم ⏰")
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

    if text in ["/start", "منوی اصلی"]:
        send_message(chat_id, "سلام! خوش برگشتی 👋", main_keyboard())

    elif text == "لیست کارهای امروز":
        tasks = get_user_tasks(team, today_only=True)
        if not tasks:
            send_message(chat_id, "امروز کاری نداری! 👍")
        else:
            send_message(chat_id, f"📋 <b>کارهای امروز ({len(tasks)} تسک):</b>")
            for t in tasks:
                msg = f"<b>{t['title']}</b>\n📅 {t['date_fa']}{t['time_part']}{t['days_text']}"
                buttons = [[{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}]]
                send_buttons(chat_id, msg, buttons)

    elif text == "لیست کارهای هفته":
        send_week(chat_id)

    elif text == "تسک های انجام نشده":
        send_pending(chat_id)
