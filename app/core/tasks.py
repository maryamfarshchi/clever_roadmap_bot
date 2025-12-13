# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"

RTL_CHARS = r"[\u200f\u200e\u202a\u202b\u202c\u202d\u202e]"

# ----------------------------------------------------
def clean_text(v):
    if v is None:
        return ""
    return re.sub(RTL_CHARS, "", str(v)).strip()

def normalize_team(v):
    return clean_text(v).lower()

def parse_date(v):
    try:
        v = clean_text(v)
        if not v:
            return None
        return datetime.strptime(v, DATE_FMT).date()
    except:
        return None

# ----------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    today = datetime.today().date()
    data = rows[1:]
    tasks = []

    for idx, row in enumerate(data):
        if len(row) < 19:
            continue

        day_fa   = clean_text(row[0])
        date_fa  = clean_text(row[1])
        date_en  = clean_text(row[2])
        time     = clean_text(row[3])

        deadline = parse_date(date_en)
        delay = (today - deadline).days if deadline else None

        groups = [
            (14, "digital"),
            (9,  "ai production"),
            (4,  "production"),
        ]

        for base, logical_team in groups:
            title   = clean_text(row[base])
            ctype   = clean_text(row[base + 1])
            comment = clean_text(row[base + 2])
            status  = clean_text(row[base + 3]).lower()
            team    = normalize_team(row[base + 4])

            # 🔥 شرط‌ها
            if not title:
                continue

            if team != logical_team:
                continue

            tasks.append({
                "row_index": idx + 2,
                "status_col": base + 3 + 1,
                "team": team,
                "title": title,
                "type": ctype,
                "comment": comment,
                "status": status,
                "date_fa": date_fa,
                "deadline_date": deadline,
                "delay_days": delay,
                "time": time
            })

    return tasks

# ----------------------------------------------------
def _filter_by_team(team):
    team = normalize_team(team)
    if team == "all":
        return _build_tasks()
    return [t for t in _build_tasks() if t["team"] == team]

# ----------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] == today
    ]

def get_tasks_week(team):
    today = datetime.today().date()
    end = today + timedelta(days=7)
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] and today <= t["deadline_date"] <= end
    ]

def get_tasks_pending(team):
    return [
        t for t in _filter_by_team(team)
        if t["status"] != "done" and t["deadline_date"]
    ]

# ----------------------------------------------------
def update_task_status(title, team, new_status="done"):
    team = normalize_team(team)
    for t in _filter_by_team(team):
        if t["title"] == title:
            update_cell("Time Sheet", t["row_index"], t["status_col"], new_status)
            return True
    return False
