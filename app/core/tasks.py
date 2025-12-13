# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"
TASKS_SHEET = "Tasks"


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def clean(s):
    return str(s or "").strip()


def normalize_team(s):
    return clean(s).lower()


def parse_date(en):
    try:
        en = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", clean(en))
        return datetime.strptime(en, DATE_FMT).date()
    except:
        return None


# -------------------------------------------------
# Load all tasks from Tasks sheet
# -------------------------------------------------
def _load_tasks():
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]
    today = datetime.today().date()
    tasks = []

    for i, row in enumerate(data, start=2):
        try:
            task_id = clean(row[0])
            team = normalize_team(row[1])
            date_en = row[2]
            date_fa = row[3]
            title = clean(row[6])
            status = clean(row[9]).lower()
            done = clean(row[18]).lower()

            if not task_id or not team or not title:
                continue

            deadline = parse_date(date_en)
            delay = (today - deadline).days if deadline else None

            tasks.append({
                "row_index": i,
                "task_id": task_id,
                "team": team,
                "title": title,
                "date_fa": date_fa,
                "deadline": deadline,
                "delay_days": delay,
                "done": done == "yes",
                "status": status,
            })
        except:
            continue

    return tasks


# -------------------------------------------------
# Filters
# -------------------------------------------------
def _by_team(team):
    team = normalize_team(team)
    tasks = _load_tasks()
    if team == "all":
        return tasks
    return [t for t in tasks if t["team"] == team]


# -------------------------------------------------
# Public APIs
# -------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _by_team(team)
        if t["deadline"] == today
    ]


def get_tasks_week(team):
    today = datetime.today().date()
    end = today + timedelta(days=7)
    return [
        t for t in _by_team(team)
        if t["deadline"] and today <= t["deadline"] <= end
    ]


def get_tasks_pending(team):
    return [
        t for t in _by_team(team)
        if not t["done"] and t["deadline"]
    ]


def update_task_status(task_id, new_status):
    rows = get_sheet(TASKS_SHEET)
    for i, row in enumerate(rows[1:], start=2):
        if clean(row[0]) == task_id:
            # Status (J)
            update_cell(TASKS_SHEET, i, 10, new_status)
            # Done (S)
            if new_status == "done":
                update_cell(TASKS_SHEET, i, 19, "Yes")
            return True
    return False
