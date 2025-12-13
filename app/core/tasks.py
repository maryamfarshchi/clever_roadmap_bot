# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------
def normalize(s):
    return str(s or "").strip()


def normalize_team(s):
    return normalize(s).lower()


def clean_date(s):
    if not s:
        return ""
    return re.sub(r"[\u200e\u200f\u202a-\u202e]", "", str(s)).strip()


def parse_date(s):
    try:
        s = clean_date(s)
        if not s:
            return None
        return datetime.strptime(s, DATE_FMT).date()
    except:
        return None


# ----------------------------------------------------
# Load tasks from Tasks sheet (ONLY SOURCE)
# ----------------------------------------------------
def _load_tasks():
    rows = get_sheet("Tasks")
    if not rows or len(rows) < 2:
        return []

    header = rows[0]
    data = rows[1:]
    today = datetime.today().date()
    tasks = []

    for idx, row in enumerate(data):
        row_map = dict(zip(header, row))

        task_id = normalize(row_map.get("TaskID"))
        title = normalize(row_map.get("Content Title"))
        team = normalize_team(row_map.get("Team"))

        if not task_id or not title or not team:
            continue  # ❗ شرط تو: title حتماً باید باشه

        date_en = row_map.get("Date_EN")
        deadline = parse_date(date_en)

        delay = None
        if deadline:
            delay = (today - deadline).days

        tasks.append({
            "row_index": idx + 2,  # 1-based with header
            "task_id": task_id,
            "team": team,
            "title": title,
            "type": row_map.get("Content Type"),
            "comment": row_map.get("Comment"),
            "status": normalize(row_map.get("Status")).lower(),
            "date_en": date_en,
            "date_fa": row_map.get("Date_FA"),
            "day_fa": row_map.get("DayName"),
            "time": row_map.get("Time"),
            "deadline": deadline,
            "delay": delay,
        })

    return tasks


# ----------------------------------------------------
# Filters
# ----------------------------------------------------
def _by_team(team):
    team = normalize_team(team)
    tasks = _load_tasks()

    if team == "all":
        return tasks

    return [t for t in tasks if t["team"] == team]


# ----------------------------------------------------
# Public APIs
# ----------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _by_team(team)
        if t["deadline"] == today
    ]


def get_tasks_week(team):
    today = datetime.today().date()
    limit = today + timedelta(days=7)
    return [
        t for t in _by_team(team)
        if t["deadline"] and today <= t["deadline"] <= limit
    ]


def get_tasks_pending(team):
    return [
        t for t in _by_team(team)
        if t["deadline"] and t["status"] != "done"
    ]


# ----------------------------------------------------
# Update status (by TaskID)
# ----------------------------------------------------
def update_task_status(task_id, new_status="done"):
    tasks = _load_tasks()
    target = None

    for t in tasks:
        if t["task_id"] == task_id:
            target = t
            break

    if not target:
        return False

    row = target["row_index"]
    header = get_sheet("Tasks")[0]
    status_col = header.index("Status") + 1  # 1-based

    update_cell("Tasks", row, status_col, new_status)
    return True
