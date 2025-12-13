# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


# ----------------------------------------------------
# Utils
# ----------------------------------------------------
def normalize(s):
    return str(s or "").strip()


def normalize_team(s):
    return normalize(s).lower()


def clean_date_string(en):
    if not en:
        return ""
    return re.sub(r"[\u200f\u200e\u202a-\u202e]", "", str(en)).strip()


def parse_date(en):
    try:
        cleaned = clean_date_string(en)
        if not cleaned:
            return None
        return datetime.strptime(cleaned, DATE_FMT).date()
    except:
        return None


def safe(row, idx):
    try:
        return row[idx]
    except:
        return ""


# ----------------------------------------------------
# Build tasks from sheet
# ----------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]
    today = datetime.today().date()
    tasks = []

    groups = [
        (4, "production"),
        (9, "ai production"),
        (14, "digital"),
    ]

    for i, row in enumerate(data):
        if not row:
            continue

        day_fa   = safe(row, 0)
        date_fa  = safe(row, 1)
        date_en  = safe(row, 2)
        time_str = safe(row, 3)

        deadline = parse_date(date_en)
        delay = (today - deadline).days if deadline else None

        for base, logical_team in groups:
            title   = normalize(safe(row, base))
            ctype   = normalize(safe(row, base + 1))
            comment = normalize(safe(row, base + 2))
            status  = normalize(safe(row, base + 3)).lower()
            team    = normalize_team(safe(row, base + 4))

            if team not in ("production", "ai production", "digital", "all"):
                continue

            # title خالی هم تسکه
            if not title:
                title = "بدون عنوان"

            # status خالی = انجام نشده
            is_done = status == "done"

            tasks.append({
                "row_index": i + 2,
                "base": base,
                "team": team,
                "title": title,
                "type": ctype,
                "comment": comment,
                "status": status,
                "is_done": is_done,
                "date_fa": date_fa,
                "date_en": date_en,
                "day_fa": day_fa,
                "time": time_str,
                "deadline_date": deadline,
                "delay_days": delay,
            })

    return tasks


# ----------------------------------------------------
# Filters
# ----------------------------------------------------
def _filter_by_team(team):
    team = normalize_team(team)
    if team == "all":
        return _build_tasks()
    return [t for t in _build_tasks() if t["team"] == team]


# ----------------------------------------------------
# Public APIs
# ----------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] == today and not t["is_done"]
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
        if not t["is_done"] and t["deadline_date"]
    ]


def update_task_status(title, team, new_status="done"):
    team = normalize_team(team)
    for t in _filter_by_team(team):
        if normalize(t["title"]) == normalize(title):
            row = t["row_index"]
            status_col = t["base"] + 3 + 1  # 1-based
            update_cell("Time Sheet", row, status_col, new_status)
            return True
    return False
