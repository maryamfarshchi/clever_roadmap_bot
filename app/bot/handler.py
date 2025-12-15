# sheet_handler.py
import gspread
from datetime import datetime
from dateutil import parser  # حتماً به requirements.txt اضافه کن: python-dateutil
import random

# فرض می‌کنیم gc و SPREADSHEET_ID در bot.py یا config تعریف شده
# اگر جداگانه import می‌کنی، اینجا اضافه کن

WORKSHEET_TASKS = "Tasks"
WORKSHEET_MEMBERS = "members"
WORKSHEET_RANDOM = "RandomMessages"
WORKSHEET_ESCALATE = "EscalateMessages"

# ایندکس ستون‌ها در شیت Tasks (بر اساس هدر)
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

def get_sheet():
    return gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_TASKS)

def get_members_sheet():
    return gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_MEMBERS)

def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    try:
        # اول فرمت اصلی: MM/DD/YYYY
        return datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        try:
            # اگر YYYY-MM-DD بود
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # اگر هر فرمتی بود (هوشمند)
                return parser.parse(date_str)
            except:
                return None

def get_days_overdue(date_str):
    due_date = parse_date(date_str)
    if not due_date:
        return 0
    today = datetime.now().date()
    due = due_date.date()
    return (today - due).days

def is_task_done(row):
    done_val = str(row[COL_DONE]).strip().upper()
    status_val = str(row[COL_STATUS]).strip()
    # اگر Done = YES یا Status شامل "Done" یا "انجام شد" باشه → انجام شده
    if done_val == "YES" or "done" in status_val.lower() or "انجام شد" in status_val:
        return True
    return False

def get_user_tasks(team, include_today=True, include_overdue=True):
    sheet = get_sheet()
    records = sheet.get_all_values()
    if len(records) < 2:
        return []
    
    header = records[0]
    tasks = []
    
    for i, row in enumerate(records[1:], start=2):
        if len(row) <= COL_TEAM:
            continue
        if row[COL_TEAM] != team:
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
            "task_id": row[COL_TASKID],
            "title": row[COL_TITLE],
            "date_fa": row[COL_DATE_FA],
            "date_en": row[COL_DATE_EN],
            "time": row[COL_TIME] or "",
            "type": row[COL_TYPE],
            "comment": row[COL_COMMENT],
            "status": row[COL_STATUS],
            "days_overdue": days,
            "team": team
        })
    
    return tasks

def get_today_tasks(team):
    return [t for t in get_user_tasks(team, include_overdue=False) if t["days_overdue"] == 0]

def get_overdue_tasks(team):
    return [t for t in get_user_tasks(team, include_today=False, include_overdue=True) if t["days_overdue"] > 0]

def mark_task_done(task_id):
    sheet = get_sheet()
    records = sheet.get_all_values()
    for i, row in enumerate(records[1:], start=2):
        if row[COL_TASKID] == task_id:
            sheet.update(f"J{i}", "Done")  # ستون Status
            sheet.update(f"S{i}", "YES")   # ستون Done (ستون ۱۹ام = S)
            return True
    return False

def mark_task_not_done(task_id):
    sheet = get_sheet()
    records = sheet.get_all_values()
    for i, row in enumerate(records[1:], start=2):
        if row[COL_TASKID] == task_id:
            sheet.update(f"J{i}", "Not Done")
            return True
    return False

def get_random_message():
    try:
        sh = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_RANDOM)
        vals = sh.get_all_values()
        messages = [row[0] for row in vals[1:] if row and row[0].strip()]
        if messages:
            return random.choice(messages)
    except:
        pass
    return "یادت نره این تسک رو انجام بدی! ⏰"

def get_escalate_message():
    try:
        sh = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_ESCALATE)
        vals = sh.get_all_values()
        messages = [row[0] for row in vals[1:] if row and row[0].strip()]
        if messages:
            return random.choice(messages)
    except:
        pass
    return "⚠️ هشدار: تسک زیر بیش از ۵ روز عقب افتاده!"
