# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
import json
from dateutil.parser import parse as date_parse
import pytz

from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"

IRAN_TZ = pytz.timezone("Asia/Tehran")

# Columns (با ستون جدید)
COL_TASKID = 0
COL_TEAM = 1
COL_DATE_EN = 2
COL_DATE_FA = 3
COL_TIME = 5
COL_TITLE = 6
COL_STATUS = 9
COL_DONE = 17  # Done در index 17
COL_REMINDERS = 18  # RemindersSent در 18

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
    except:
        print(f"[DEBUG] Parse date failed for: {v}")
        return None

def _load_tasks():
    rows = get_sheet(TASKS_SHEET)
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
        reminders = json.loads(reminders_str or '{}')

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

def _by_team(team, tasks=None):
    tasks = tasks or _load_tasks()
    team_norm = normalize_team(team)
    if team_norm == "all":
        return tasks
    return [t for t in tasks if t["team"] == team_norm]

def get_tasks_today(team):
    today = datetime.now(IRAN_TZ).date()
    return [t for t in _by_team(team) if t["deadline"] == today and not t["done"]]

def get_tasks_week(team):
    today = datetime.now(IRAN_TZ).date()
    end = today + timedelta(days=7)
    return [t for t in _by_team(team) if today <= t["deadline"] <= end and not t["done"]]

def get_tasks_overdue(team):
    return [t for t in _by_team(team) if t["delay_days"] > 0 and not t["done"]]

def get_tasks_nearing_deadline(team, days_left=2):
    today = datetime.now(IRAN_TZ).date()
    target = today + timedelta(days=days_left)
    return [t for t in _by_team(team) if t["deadline"] == target and not t["done"] and '2day' not in t["reminders"]]

def get_tasks_deadline_today(team):
    today = datetime.now(IRAN_TZ).date()
    return [t for t in _by_team(team) if t["deadline"] == today and not t["done"] and 'deadline' not in t["reminders"]]

def get_tasks_delayed(team, day):
    return [t for t in _by_team(team) if t["delay_days"] == day and not t["done"] and day not in t["reminders"].get('delays', [])]

def update_task_status(task_id, new_status):
    tasks = _load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            update_cell(TASKS_SHEET, t["row_index"], COL_STATUS + 1, new_status)
            if "done" in new_status.lower():
                update_cell(TASKS_SHEET, t["row_index"], COL_DONE + 1, "YES")
            return True
    return False

def update_task_reminder(task_id, key, value=None):
    tasks = _load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            reminders = t["reminders"]
            if key == 'delays':
                delays = reminders.get('delays', [])
                delays.append(value)
                reminders['delays'] = delays
            else:
                reminders[key] = value or datetime.now(IRAN_TZ).strftime("%Y-%m-%d")
            update_cell(TASKS_SHEET, t["row_index"], COL_REMINDERS + 1, json.dumps(reminders))
            return True
    return False
