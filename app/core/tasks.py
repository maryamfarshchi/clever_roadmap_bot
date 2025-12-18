# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
import re
import json
import pytz

from core.sheets import get_sheet, update_cell
from core.logging import log_error

TASKS_SHEET = "Tasks"
IRAN_TZ = pytz.timezone("Asia/Tehran")

# 0-based columns in sheet
COL_TASKID    = 0
COL_TEAM      = 1
COL_DATE_EN   = 2
COL_DATE_FA   = 3
COL_TIME      = 5
COL_TITLE     = 6
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
    try:
        return jalali_to_gregorian(y, m, d)
    except Exception:
        return None

async def load_tasks():
    rows = await get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []

    today = datetime.now(IRAN_TZ).date()
    tasks = []

    for i, row in enumerate(rows[1:], start=2):
        if len(row) <= COL_REMINDERS:
            continue

        task_id = clean(row[COL_TASKID])
        team = normalize_team(row[COL_TEAM])
        date_fa = clean(row[COL_DATE_FA]).lstrip("'")
        time_str = clean(row[COL_TIME])
        title = clean(row[COL_TITLE])

        status = clean(row[COL_STATUS]).lower()
        done_val = clean(row[COL_DONE]).lower()

        reminders_raw = clean(row[COL_REMINDERS]) or "{}"
        try:
            reminders = json.loads(reminders_raw)
            if not isinstance(reminders, dict):
                reminders = {}
        except Exception:
            reminders = {}

        if not task_id or not team or not title:
            continue

        deadline = parse_jalali_date(date_fa)
        if not deadline:
            # اگر هنوز date_fa خراب بود، حذف نکن، ولی لاگ بزن
            log_error(f"Deadline parse failed TaskID={task_id} DateFA={date_fa}")
            continue

        delay = (today - deadline).days
        is_done = (done_val in ["yes", "y"]) or ("done" in status) or ("انجام" in status)

        tasks.append({
            "row_index": i,
            "task_id": task_id,
            "team": team,
            "title": title,
            "date_fa": date_fa,
            "time": time_str,
            "deadline": deadline,
            "delay_days": delay,
            "done": is_done,
            "status": status,
            "reminders": reminders
        })

    return tasks

def _by_team(team: str, tasks: list):
    t = normalize_team(team)
    if t == "all":
        return tasks
    return [x for x in tasks if x["team"] == t]

async def get_tasks_today(team: str):
    tasks = await load_tasks()
    today = datetime.now(IRAN_TZ).date()
    return [t for t in _by_team(team, tasks) if t["deadline"] == today and not t["done"]]

async def get_tasks_week(team: str):
    tasks = await load_tasks()
    today = datetime.now(IRAN_TZ).date()
    end = today + timedelta(days=7)
    out = [t for t in _by_team(team, tasks) if today <= t["deadline"] <= end and not t["done"]]
    out.sort(key=lambda x: x["deadline"])
    return out

async def get_tasks_not_done(team: str):
    tasks = await load_tasks()
    out = [t for t in _by_team(team, tasks) if not t["done"]]
    out.sort(key=lambda x: x["deadline"])
    return out

async def update_task_status(task_id: str, new_status: str):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            ok1 = await update_cell(TASKS_SHEET, t["row_index"], COL_STATUS + 1, new_status)
            ok2 = True
            if "done" in new_status.lower():
                ok2 = await update_cell(TASKS_SHEET, t["row_index"], COL_DONE + 1, "YES")
            return ok1 and ok2
    return False

async def set_task_reminders_json(task_id: str, reminders_dict: dict):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            payload = json.dumps(reminders_dict or {}, ensure_ascii=False)
            return await update_cell(TASKS_SHEET, t["row_index"], COL_REMINDERS + 1, payload)
    return False

async def update_task_reminder(task_id: str, key: str, value):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            reminders = t["reminders"] or {}
            reminders[key] = value
            return await set_task_reminders_json(task_id, reminders)
    return False
