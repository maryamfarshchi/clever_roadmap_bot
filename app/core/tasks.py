# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def normalize(s):
    return str(s or "").strip()

def normalize_team(s):
    return normalize(s).lower()

def clean_date(en):
    if not en:
        return ""
    return re.sub(r"[\u200f\u200e\u202a-\u202e]", "", str(en)).strip()

def parse_date(en):
    try:
        en = clean_date(en)
        if not en:
            return None
        return datetime.strptime(en, DATE_FMT).date()
    except:
        return None


# --------------------------------------------------
# Load all tasks from Tasks sheet
# --------------------------------------------------
def _load_tasks():
    rows = get_sheet("Tasks")
    if not rows or len(rows) < 2:
        return []

    header = rows[0]
    data = rows[1:]

    col = {name: i for i, name in enumerate(header)}

    today = datetime.today().date()
    tasks = []

    for i, row in enumerate(data, start=2):
        title = normalize(row[col["Content Title"]])
        if not title:
            continue  # ❗ بدون عنوان = تسک نیست

        team = normalize_team(row[col["Team"]])
        date_en = row[col["Date_EN"]]
        deadline = parse_date(date_en)

        status = normalize(row[col["Status"]]).lower()
        done_flag = normalize(row[col["Done"]]).lower() == "yes"

        # اگر Done = Yes → انجام شده
        if done_flag:
            status = "done"

        delay = None
        if deadline:
            delay = (today - deadline).days

        tasks.append({
            "row_index": i,
            "task_id": normalize(row[col["TaskID"]]),
            "team": team,
            "title": title,
            "type": normalize(row[col["Content Type"]]),
            "comment": normalize(row[col["Comment"]]),
            "status": status,              # done / not yet / ""
            "done": done_flag,
            "date_en": date_en,
            "date_fa": normalize(row[col["Date_FA"]]),
            "day_fa": normalize(row[col["DayName"]]),
            "time": normalize(row[col["Time"]]),
            "deadline": deadline,
            "delay_days": delay,
        })

    return tasks


# --------------------------------------------------
# Filters
# --------------------------------------------------
def _by_team(team):
    team = normalize_team(team)
    tasks = _load_tasks()

    if team == "all":
        return tasks

    return [t for t in tasks if t["team"] == team]


# --------------------------------------------------
# Public APIs
# --------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _by_team(team)
        if t["deadline"] == today and t["status"] != "done"
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
        if t["deadline"] and t["status"] != "done"
    ]


# --------------------------------------------------
# Update task status
# --------------------------------------------------
def update_task_status(task_id, new_status="done"):
    rows = get_sheet("Tasks")
    if not rows:
        return False

    header = rows[0]
    col = {name: i for i, name in enumerate(header)}

    for i, row in enumerate(rows[1:], start=2):
        if normalize(row[col["TaskID"]]) == normalize(task_id):
            update_cell("Tasks", i, col["Status"] + 1, new_status)
            if new_status == "done":
                update_cell("Tasks", i, col["Done"] + 1, "Yes")
            return True

    return False
