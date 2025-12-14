# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
import pytz

from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"
IRAN_TZ = pytz.timezone('Asia/Tehran')


def clean(s):
    return str(s or "").strip()


def normalize_team(s):
    return clean(s).lower()


def parse_date_any(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()

    s = clean(v)
    s = re.sub(r"[\u200e\u200f\u202a-\u202e\s]+", "", s)

    formats = [
        "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    print(f"[WARNING] Failed to parse date: '{v}' -> '{s}'")
    return None


def get_today_iran():
    return datetime.now(IRAN_TZ).date()


def _load_tasks():
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]
    today = get_today_iran()
    tasks = []

    for i, row in enumerate(data, start=2):
        task_id = clean(row[0] if len(row) > 0 else "")
        team = normalize_team(row[1] if len(row) > 1 else "")
        date_en = row[2] if len(row) > 2 else None
        date_fa = row[3] if len(row) > 3 else ""
        title = clean(row[6] if len(row) > 6 else "")

        done_raw = clean(row[18] if len(row) > 18 else "").lower()
        done = done_raw in ["yes", "y"]

        if not task_id or not team or not title:
            continue

        deadline = parse_date_any(date_en)
        delay = (today - deadline).days if deadline else None

        tasks.append({
            "row_index": i,
            "task_id": task_id,
            "team": team,
            "title": title,
            "date_fa": date_fa or "نامشخص",
            "deadline": deadline,
            "delay_days": delay,
            "done": done,
        })

    return tasks


def _by_team(team):
    team_norm = normalize_team(team)
    tasks = _load_tasks()
    if team_norm == "all":
        return tasks
    return [t for t in tasks if t["team"] == team_norm]


def get_tasks_today(team):
    today = get_today_iran()
    yesterday = today - timedelta(days=1)
    return [t for t in _by_team(team) if t["deadline"] and t["deadline"] in (today, yesterday)]


def get_tasks_week(team):
    today = get_today_iran()
    end = today + timedelta(days=7)
    return [t for t in _by_team(team) if t["deadline"] and today <= t["deadline"] <= end]


def get_tasks_pending(team):
    return [t for t in _by_team(team) if not t["done"]]


def update_task_status(task_id, new_status):
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return False

    task_id = str(task_id).strip()
    new_status_clean = clean(new_status)

    for i, row in enumerate(rows[1:], start=2):
        if clean(row[0] if len(row) > 0 else "") == task_id:
            update_cell(TASKS_SHEET, i, 10, new_status_clean)
            done_value = "Yes" if new_status_clean.lower() in ["yes", "done", "y"] else ""
            update_cell(TASKS_SHEET, i, 19, done_value)
            return True
    return False
