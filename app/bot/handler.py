# app/bot/sheet_handler.py  (یا اگر اسم فایل handler.py هست، همین رو جایگزین کن)

import random
from datetime import datetime
from dateutil import parser  # python-dateutil در requirements.txt هست
import pytz  # برای timezone ایران (در requirements.txt اضافه کن اگر نیست)

from core.sheets import get_sheet  # از core.sheets استفاده کن (requests-based)

# نام شیت‌ها
WORKSHEET_TASKS = "Tasks"
WORKSHEET_MEMBERS = "members"
WORKSHEET_RANDOM = "RandomMessages"
WORKSHEET_ESCALATE = "EscalateMessages"

# ایندکس ستون‌ها (بر اساس هدر Tasks)
COL_TASKID = 0
COL_TEAM = 1
COL_DATE_EN = 2
COL_DATE_FA = 3
COL_DAYNAME = 4
COL_TIME = 5
COL_TITLE = 6
COL_TYPE = 7
COL_COMMENT = 8
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

# timezone ایران
IRAN_TZ = pytz.timezone("Asia/Tehran")

def _get_tasks_rows():
    """دریافت rows از شیت Tasks با core.sheets"""
    rows = get_sheet(WORKSHEET_TASKS)
    if not rows or len(rows) < 2:
        return []
    return rows  # rows شامل هدر + داده‌هاست

def parse_date(date_str):
    """پارس هوشمند تاریخ MM/DD/YYYY با fallback"""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    # پاک کردن کاراکترهای RTL احتمالی
    date_str = date_str.replace("\u200e", "").replace("\u200f", "")
    
    try:
        # فرمت اصلی شیت
        return datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                return parser.parse(date_str, dayfirst=False)
            except:
                return None

def get_days_overdue(date_str):
    """تعداد روزهای overdue بر اساس تاریخ ایران"""
    due_date = parse_date(date_str)
    if not due_date:
        return 0
    today = datetime.now(IRAN_TZ).date()
    return (today - due_date.date()).days

def is_task_done(row):
    """تشخیص انجام شده از ستون Done یا Status"""
    if len(row) <= COL_DONE:
        return False
    done_val = str(row[COL_DONE]).strip().upper()
    status_val = str(row[COL_STATUS]).strip().lower() if len(row) > COL_STATUS else ""
    return done_val == "YES" or "done" in status_val or "yes" in status_val or "انجام شد" in status_val

def get_user_tasks(team, include_today=True, include_overdue=True):
    rows = _get_tasks_rows()
    if len(rows) < 2:
        return []
    
    tasks = []
    for i, row in enumerate(rows[1:], start=2):  # از ردیف ۲ (داده‌ها)
        if len(row) <= COL_TEAM or str(row[COL_TEAM]).strip() != team:
            continue
        if is_task_done(row):
            continue
        
        days = get_days_overdue(row[COL_DATE_EN])
        if days < 0:  # آینده
            continue
        if not include_today and days == 0:
            continue
        if not include_overdue and days > 0:
            continue
        
        tasks.append({
            "row": i,
            "task_id": row[COL_TASKID].strip() if len(row) > COL_TASKID else "",
            "title": row[COL_TITLE].strip() if len(row) > COL_TITLE else "",
            "date_fa": row[COL_DATE_FA].strip() if len(row) > COL_DATE_FA else "",
            "date_en": row[COL_DATE_EN],
            "time": (row[COL_TIME].strip() if len(row) > COL_TIME else "") or "",
            "type": row[COL_TYPE].strip() if len(row) > COL_TYPE else "",
            "comment": row[COL_COMMENT].strip() if len(row) > COL_COMMENT else "",
            "status": row[COL_STATUS].strip() if len(row) > COL_STATUS else "",
            "days_overdue": days,
            "team": team
        })
    
    return tasks

def get_today_tasks(team):
    return [t for t in get_user_tasks(team, include_overdue=False) if t["days_overdue"] == 0]

def get_overdue_tasks(team):
    overdue = get_user_tasks(team, include_today=False)
    return [t for t in overdue if t["days_overdue"] > 0]

def mark_task_done(task_id):
    """آپدیت Status به Done و Done به YES"""
    from core.sheets import update_cell
    rows = _get_tasks_rows()
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > COL_TASKID and row[COL_TASKID].strip() == task_id:
            update_cell(WORKSHEET_TASKS, i, COL_STATUS + 1, "Done")  # ستون J = 10ام (1-based)
            update_cell(WORKSHEET_TASKS, i, COL_DONE + 1, "YES")     # ستون S = 19ام (1-based)
            return True
    return False

def mark_task_not_done(task_id):
    from core.sheets import update_cell
    rows = _get_tasks_rows()
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > COL_TASKID and row[COL_TASKID].strip() == task_id:
            update_cell(WORKSHEET_TASKS, i, COL_STATUS + 1, "Not Done")
            return True
    return False

def get_random_message():
    try:
        rows = get_sheet(WORKSHEET_RANDOM)
        messages = [row[0].strip() for row in rows[1:] if row and row[0].strip()]
        if messages:
            return random.choice(messages)
    except Exception as e:
        print(f"[RANDOM MSG ERROR] {e}")
    return "یادت نره این تسک رو انجام بدی! ⏰"

def get_escalate_message():
    try:
        rows = get_sheet(WORKSHEET_ESCALATE)
        messages = [row[0].strip() for row in rows[1:] if row and row[0].strip()]
        if messages:
            return random.choice(messages)
    except Exception as e:
        print(f"[ESCALATE MSG ERROR] {e}")
    return "⚠️ هشدار: تسک زیر بیش از ۵ روز عقب افتاده!"
