# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
import re
import json
import pytz

from core.sheets import get_sheet, update_cell, invalidate  # invalidate اضافه شده
from core.logging import log_error

TASKS_SHEET = "Tasks"
TIME_SHEET = "Time Sheet"  # نام شیت تایم‌شیت - اگر متفاوت بود، تغییر بده

IRAN_TZ = pytz.timezone("Asia/Tehran")

# 0-based columns in sheet
COL_TASKID    = 0
COL_TEAM      = 1
COL_DATE_EN   = 2
COL_DATE_FA   = 3
COL_TIME      = 5
COL_TITLE     = 6
COL_TYPE      = 7  # اضافه برای type (Content Type)
COL_COMMENT   = 8  # اضافه برای comment
COL_STATUS    = 9
COL_DONE      = 17
COL_REMINDERS = 18

def clean(s):
    return str(s or "").strip()

def normalize_team(s):
    return clean(s).lower().replace("ai production", "aiproduction").replace(" ", "")

# Jalali -> Gregorian (pure python)
def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    jy += 1595
    days = -355668 + (365 * jy) + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186

    gy = 400 * (days // 146097)
    days %= 146097

    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1

    gy += 4 * (days // 1461)
    days %= 1461

    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    mdays = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > mdays[gm]:
        gd -= mdays[gm]
        gm += 1
    return date(gy, gm, gd)

def parse_jalali_date(date_fa: str):
    s = clean(date_fa)
    if not s:
        return None
    s = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s)
    s = s.replace("-", "/")
    parts = [p for p in s.split("/") if p.strip()]
    if len(parts) != 3:
        return None
    try:
        y = int(parts[0]); m = int(parts[1]); d = int(parts[2])
    except ValueError:
        return None
    if y < 1200 or y > 1600 or m < 1 or m > 12 or d < 1 or d > 31:
        return None
    return jalali_to_gregorian(y, m, d)

async def load_tasks():
    rows = await get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []

    out = []
    today = datetime.now(IRAN_TZ).date()

    for i, row in enumerate(rows[1:], start=2):
        task_id = clean(row[COL_TASKID]) if len(row) > COL_TASKID else ""
        if not task_id:
            continue

        date_fa = clean(row[COL_DATE_FA]) if len(row) > COL_DATE_FA else ""
        date_en = parse_jalali_date(date_fa)

        if not date_en:
            continue

        delay_days = (today - date_en).days if date_en else 0

        reminders_str = clean(row[COL_REMINDERS]) if len(row) > COL_REMINDERS else "{}"
        try:
            reminders = json.loads(reminders_str)
        except json.JSONDecodeError:
            reminders = {}

        out.append({
            "row_index": i,
            "task_id": task_id,
            "team": normalize_team(row[COL_TEAM]) if len(row) > COL_TEAM else "",
            "date_en": date_en,
            "date_fa": date_fa,
            "time": clean(row[COL_TIME]) if len(row) > COL_TIME else "",
            "title": clean(row[COL_TITLE]) if len(row) > COL_TITLE else "",
            "type": clean(row[COL_TYPE]) if len(row) > COL_TYPE else "",  # اضافه برای type
            "comment": clean(row[COL_COMMENT]) if len(row) > COL_COMMENT else "",  # اضافه برای comment
            "status": clean(row[COL_STATUS]) if len(row) > COL_STATUS else "In Progress",
            "done": (clean(row[COL_DONE]).lower() == "yes") if len(row) > COL_DONE else False,
            "reminders": reminders,
            "delay_days": delay_days,
        })
    return out

async def load_time_sheet():
    rows = await get_sheet(TIME_SHEET)
    if not rows or len(row) < 2:
        return []

    out = []
    for i, row in enumerate(rows[1:], start=2):
        # فرض بر این که ساختار Time Sheet مشابه Tasks هست، اما تنظیم کن اگر متفاوت
        task_id = clean(row[0])  # adjust columns as per your Time Sheet
        team = normalize_team(row[8] or row[13] or row[18])  # team columns
        out.append({
            "row_index": i,
            "task_id": task_id,
            "team": team,
        })
    return out

async def get_tasks_today(team: str):
    tasks = await load_tasks()
    today = datetime.now(IRAN_TZ).date()
    return [t for t in tasks if t["date_en"] == today and normalize_team(t["team"]) == normalize_team(team) and not t["done"]]

async def get_tasks_week(team: str):
    tasks = await load_tasks()
    today = datetime.now(IRAN_TZ).date()
    week_end = today + timedelta(days=7)
    return [t for t in tasks if today <= t["date_en"] <= week_end and normalize_team(t["team"]) == normalize_team(team)]

async def get_tasks_not_done(team: str):
    tasks = await load_tasks()
    today = datetime.now(IRAN_TZ).date()
    return [t for t in tasks if t["date_en"] < today and normalize_team(t["team"]) == normalize_team(team) and not t["done"]]

async def update_task_status(task_id: str, new_status: str):
    tasks = await load_tasks()
    updated_tasks = False
    for t in tasks:
        if t["task_id"] == task_id:
            ok1 = await update_cell(TASKS_SHEET, t["row_index"], COL_STATUS + 1, new_status)
            ok2 = True
            if "done" in new_status.lower():
                ok2 = await update_cell(TASKS_SHEET, t["row_index"], COL_DONE + 1, "YES")
            updated_tasks = ok1 and ok2
            break

    # آپدیت Time Sheet (اگر task_id پیدا بشه)
    time_sheet_tasks = await load_time_sheet()
    updated_time_sheet = False
    for ts in time_sheet_tasks:
        if ts["task_id"] == task_id:
            # دینامیک کردن ستون status بر اساس تیم
            status_col_map = {
                'production': 8,  # 1-based برای ستون 8
                'aiproduction': 13,  # 1-based برای ستون 13
                'digital': 18   # 1-based برای ستون 18
            }
            status_col = status_col_map.get(ts["team"], COL_STATUS + 1)  # default به COL_STATUS + 1 اگر تیم پیدا نشد
            ok1_ts = await update_cell(TIME_SHEET, ts["row_index"], status_col, new_status)
            ok2_ts = True
            if "done" in new_status.lower():
                ok2_ts = await update_cell(TIME_SHEET, ts["row_index"], COL_DONE + 1, "YES")
            updated_time_sheet = ok1_ts and ok2_ts
            break

    return updated_tasks or updated_time_sheet

async def set_task_reminders_json(task_id: str, reminders_dict: dict):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            payload = json.dumps(reminders_dict or {}, ensure_ascii=False)
            ok = await update_cell(TASKS_SHEET, t["row_index"], COL_REMINDERS + 1, payload)
            if ok:
                invalidate("Tasks")  # جدید: بعد آپدیت، کش رو invalidate کن تا تکرار جلوگیری بشه
            return ok
    return False

async def update_task_reminder(task_id: str, key: str, value):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            reminders = t["reminders"] or {}
            reminders[key] = value
            ok = await set_task_reminders_json(task_id, reminders)
            if ok:
                invalidate("Tasks")  # جدید: بعد آپدیت، کش رو invalidate کن
            return ok
    return False
