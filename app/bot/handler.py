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
WORKSHEET_MESSAGES = "Messages"
COL_TASKID = 0
COL_TEAM = 1
COL_DATE_EN = 2
COL_DATE_FA = 3
COL_TIME = 5
COL_TITLE = 6
COL_STATUS = 9
COL_PRE2 = 10
COL_DUE = 11
COL_OVER1 = 12
COL_OVER2 = 13
COL_OVER3 = 14
COL_OVER4 = 15
COL_OVER5 = 16
COL_ESCALATED = 17
COL_DONE = 18

IRAN_TZ = pytz.timezone("Asia/Tehran")

def _get_tasks_rows():
    rows = get_sheet(WORKSHEET_TASKS)
    if not rows or len(rows) < 2:
        return []
    return rows

def _get_messages(type_filter):
    try:
        rows = get_sheet(WORKSHEET_MESSAGES)
        msgs = [row[1].strip() for row in rows[1:] if len(row) > 1 and str(row[0]).strip().upper() == type_filter and row[1].strip()]
        if msgs:
            return random.choice(msgs)
    except Exception as e:
        print(f"[MESSAGES ERROR] {e}")
    return "یادت نره تسک‌هاتو انجام بدی! ⏰"

def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip().replace("\u200e", "").replace("\u200f", "")
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

def get_flag_sent(row, days):
    if days == -2:
        return str(row[COL_PRE2]).strip().upper() == "YES" if len(row) > COL_PRE2 else False
    if days == 0:
        return str(row[COL_DUE]).strip().upper() == "YES" if len(row) > COL_DUE else False
    if 1 <= days <= 5:
        col = COL_OVER1 + (days - 1)
        return str(row[col]).strip().upper() == "YES" if len(row) > col else False
    return False

def set_flag_sent(row_index, days):
    if days == -2:
        update_cell(WORKSHEET_TASKS, row_index, COL_PRE2 + 1, "YES")
    if days == 0:
        update_cell(WORKSHEET_TASKS, row_index, COL_DUE + 1, "YES")
    if 1 <= days <= 5:
        col = COL_OVER1 + (days - 1) + 1
        update_cell(WORKSHEET_TASKS, row_index, col, "YES")

def mark_task_done(task_id):
    rows = _get_tasks_rows()
    for i, row in enumerate(rows[1:], start=2):
        if str(row[COL_TASKID]).strip() == task_id:
            update_cell(WORKSHEET_TASKS, i, COL_STATUS + 1, "Done")
            update_cell(WORKSHEET_TASKS, i, COL_DONE + 1, "YES")
            return True
    return False

# ------------------- تریگر روزانه (PRE2/DUE/OVR/ESC) -------------------
def send_daily_reminders():
    rows = _get_tasks_rows()
    for i, row in enumerate(rows[1:], start=2):
        if is_task_done(row):
            continue
        
        team = str(row[COL_TEAM]).strip()
        title = str(row[COL_TITLE]).strip()
        date_fa = str(row[COL_DATE_FA]).strip()
        time_str = str(row[COL_TIME]).strip() if len(row) > COL_TIME else ""
        time_part = f" ⏰ {time_str}" if time_str else ""
        task_id = str(row[COL_TASKID]).strip()
        days = get_days_overdue(row[COL_DATE_EN])
        
        members = get_members_by_team(team)
        if not members:
            continue
        
        msg_type = None
        if days == -2 and not get_flag_sent(row, -2):
            msg_type = "PRE2"
        elif days == 0 and not get_flag_sent(row, 0):
            msg_type = "DUE"
        elif 1 <= days <= 5 and not get_flag_sent(row, days):
            msg_type = "OVR"
        elif days > 5 and str(row[COL_ESCALATED]).strip().upper() != "YES":
            msg_type = "ESC"
            update_cell(WORKSHEET_TASKS, i, COL_ESCALATED + 1, "YES")
        
        if not msg_type:
            continue
        
        message_text = _get_messages(msg_type)
        if not message_text:
            continue
        
        # جایگزینی placeholderها (NAME رو از members می‌گیریم اگر باشه، فعلاً "تیم" یا "کاربر")
        name = "کاربر"
        message_text = message_text.replace("{NAME}", name).replace("{TITLE}", title).replace("{TEAM}", team).replace("{DAYS}", str(abs(days))).replace("{DATE_FA}", date_fa)
        
        target_members = members if msg_type != "ESC" else get_members_by_team("ALL")
        
        for member in target_members:
            chat_id = member["chat_id"]
            send_message(chat_id, message_text)
            
            task_msg = f"<b>{title}</b>\n📅 {date_fa}{time_part} ({'امروز' if days == 0 else f'{abs(days)} روز گذشته'})"
            buttons = [
                [{"text": "تحویل دادم ✅", "callback_data": f"done|{task_id}"}],
                [{"text": "نه هنوز ⏰", "callback_data": f"notyet|{task_id}"}] if days >= 0 else []
            ]
            send_buttons(chat_id, task_msg, buttons)
        
        set_flag_sent(i, days)

# سازگاری با scheduler قدیمی
def send_pending(chat_id, user_info=None):
    send_daily_reminders()  # حالا pending همون daily هست

def send_week(chat_id, user_info=None):
    send_message(chat_id, "لیست کارهای هفته هنوز پیاده‌سازی نشده، بعداً اضافه می‌کنم اگر خواستی!")

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
        send_message(chat_id, "سلام! خوش برگشتی 👋\nدکمه‌های زیر رو بزن:", main_keyboard())

    elif text == "لیست کارهای امروز":
        tasks = []
        for row in _get_tasks_rows()[1:]:
            if str(row[COL_TEAM]).strip() == team and not is_task_done(row) and get_days_overdue(row[COL_DATE_EN]) == 0:
                tasks.append(row)
        if not tasks:
            send_message(chat_id, "امروز کاری نداری! استراحت کن 😎👍")
        else:
            send_message(chat_id, f"📋 <b>کارهای امروز ({len(tasks)} تسک):</b>")
            for row in tasks:
                title = str(row[COL_TITLE]).strip()
                date_fa = str(row[COL_DATE_FA]).strip()
                time_str = str(row[COL_TIME]).strip() if len(row) > COL_TIME else ""
                time_part = f" ⏰ {time_str}" if time_str else ""
                task_id = str(row[COL_TASKID]).strip()
                msg = f"<b>{title}</b>\n📅 {date_fa}{time_part} (امروز)"
                buttons = [[{"text": "تحویل دادم ✅", "callback_data": f"done|{task_id}"}]]
                send_buttons(chat_id, msg, buttons)

    elif text == "تسک های انجام نشده":
        tasks = []
        for row in _get_tasks_rows()[1:]:
            if str(row[COL_TEAM]).strip() == team and not is_task_done(row) and get_days_overdue(row[COL_DATE_EN]) >= 0:
                tasks.append(row)
        if not tasks:
            send_message(chat_id, "تسک انجام نشده‌ای نداری! فوق‌العاده‌ای 🔥✅")
        else:
            send_message(chat_id, f"⚠️ <b>تسک‌های عقب افتاده ({len(tasks)} تسک):</b>")
            for row in tasks:
                title = str(row[COL_TITLE]).strip()
                date_fa = str(row[COL_DATE_FA]).strip()
                time_str = str(row[COL_TIME]).strip() if len(row) > COL_TIME else ""
                time_part = f" ⏰ {time_str}" if time_str else ""
                days = get_days_overdue(row[COL_DATE_EN])
                days_text = " (امروز)" if days == 0 else f" ({days} روز گذشته)"
                task_id = str(row[COL_TASKID]).strip()
                msg = f"<b>{title}</b>\n📅 {date_fa}{time_part}{days_text}"
                buttons = [
                    [{"text": "تحویل دادم ✅", "callback_data": f"done|{task_id}"}],
                    [{"text": "نه هنوز ⏰", "callback_data": f"notyet|{task_id}"}]
                ]
                send_buttons(chat_id, msg, buttons)
