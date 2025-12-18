# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
import json
from dateutil.parser import parse as date_parse
import pytz

from core.sheets import get_sheet, update_cell
from core.logging import log_error

TASKS_SHEET = "Tasks"
IRAN_TZ = pytz.timezone("Asia/Tehran")

COL_TASKID = 0
COL_TEAM = 1
COL_DATE_EN = 2
COL_DATE_FA = 3
COL_TIME = 5
COL_TITLE = 6
COL_STATUS = 9
COL_DONE = 17
COL_REMINDERS = 18

def clean(s):
    return str(s or "").strip()

def normalize_team(s):
    return clean(s).lower().replace("ai production", "aiproduction").replace(" ", "")

def parse_date_any(v):
    if not v:
        return None
    s = clean(v)
    s = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s)
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        pass
    try:
        return date_parse(s, dayfirst=False, yearfirst=False).date()
    except Exception:
        log_error(f"Parse date failed for: {v}")
        return None

async def load_tasks():
    rows = await get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]
    today = datetime.now(IRAN_TZ).date()
    tasks = []

    for i, row in enumerate(data, start=2):
        if len(row) < COL_REMINDERS + 1:
            continue

        task_id = clean(row[COL_TASKID])
        team = normalize_team(row[COL_TEAM])
        date_en = row[COL_DATE_EN]
        date_fa = clean(row[COL_DATE_FA])
        time_str = clean(row[COL_TIME])
        title = clean(row[COL_TITLE])
        status = clean(row[COL_STATUS]).lower()
        done = clean(row[COL_DONE]).lower()

        reminders_str = clean(row[COL_REMINDERS])
        try:
            reminders = json.loads(reminders_str or "{}")
        except Exception:
            reminders = {}

        if not task_id or not team or not title:
            continue

        deadline = parse_date_any(date_en)
        if not deadline:
            continue

        delay = (today - deadline).days
        is_done = (done in ["yes", "y"]) or any(k in status for k in ["done", "yes", "انجام شد"])

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

def _filter_by_team(team, tasks):
    t = normalize_team(team)
    if t == "all":
        return tasks
    return [x for x in tasks if x["team"] == t]

async def get_tasks_today(team):
    today = datetime.now(IRAN_TZ).date()
    tasks = await load_tasks()
    return [t for t in _filter_by_team(team, tasks) if t["deadline"] == today and not t["done"]]

async def get_tasks_week(team):
    today = datetime.now(IRAN_TZ).date()
    end = today + timedelta(days=7)
    tasks = await load_tasks()
    return [t for t in _filter_by_team(team, tasks) if today <= t["deadline"] <= end and not t["done"]]

async def get_tasks_overdue(team):
    tasks = await load_tasks()
    return [t for t in _filter_by_team(team, tasks) if t["delay_days"] > 0 and not t["done"]]

async def update_task_status(task_id, new_status):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            ok1 = await update_cell(TASKS_SHEET, t["row_index"], COL_STATUS + 1, new_status)
            ok2 = True
            if "done" in new_status.lower():
                ok2 = await update_cell(TASKS_SHEET, t["row_index"], COL_DONE + 1, "YES")
            return ok1 and ok2
    return False

async def update_task_reminder(task_id, key, value=None):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            reminders = t["reminders"] or {}
            if key == "delays":
                delays = reminders.get("delays", [])
                delays.append(value)
                reminders["delays"] = delays
            else:
                reminders[key] = value or datetime.now(IRAN_TZ).strftime("%Y-%m-%d")
            return await update_cell(TASKS_SHEET, t["row_index"], COL_REMINDERS + 1, json.dumps(reminders, ensure_ascii=False))
    return False
