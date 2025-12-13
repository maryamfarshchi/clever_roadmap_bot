# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"

# ----------------------------------------------------
# Normalize
# ----------------------------------------------------
def normalize_team(name):
    return str(name or "").strip().lower()

# ----------------------------------------------------
# Clean date from Google Sheet (RTL fix)
# ----------------------------------------------------
def clean_date_string(val):
    if not val:
        return ""
    return re.sub(r"[\u200e\u200f\u202a-\u202e]", "", str(val)).strip()

# ----------------------------------------------------
# Parse EN date
# ----------------------------------------------------
def parse_date(en):
    try:
        cleaned = clean_date_string(en)
        if not cleaned:
            return None
        return datetime.strptime(cleaned, DATE_FMT).date()
    except:
        return None

# ----------------------------------------------------
# Build all tasks from sheet
# ----------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]
    today = datetime.today().date()
    tasks = []

    for row_idx, row in enumerate(data, start=2):
        if not row:
            continue

        day_fa   = row[0] if len(row) > 0 else ""
        date_fa  = row[1] if len(row) > 1 else ""
        date_en  = row[2] if len(row) > 2 else ""
        time_str = row[3] if len(row) > 3 else ""

        deadline = parse_date(date_en)

        # blocks: Production / AI / Digital
        blocks = [
            (4,  "production"),
            (9,  "ai production"),
            (14, "digital"),
        ]

        for base, logical_team in blocks:
            if len(row) <= base + 4:
                continue

            title   = str(row[base] or "").strip()
            ctype   = row[base + 1]
            comment = row[base + 2]
            status  = str(row[base + 3] or "").strip().lower()
            team_nm = normalize_team(row[base + 4])

            # ⛔️ شرط حیاتی
            if not title:
                continue

            if team_nm not in ("production", "ai production", "digital", "all"):
                continue

            delay_days = None
            if deadline:
                delay_days = (today - deadline).days

            tasks.append({
                "row_index": row_idx,
                "base": base,
                "team": team_nm,
                "title": title,
                "type": ctype,
                "comment": comment,
                "status": status,
                "date_fa": date_fa,
                "date_en": date_en,
                "day_fa": day_fa,
                "time": time_str,
                "deadline_date": deadline,
                "delay_days": delay_days,
            })

    return tasks

# ----------------------------------------------------
# Filter by team (ALL supported)
# ----------------------------------------------------
def _filter_by_team(team):
    team = normalize_team(team)
    all_tasks = _build_tasks()

    if team == "all":
        return all_tasks

    return [t for t in all_tasks if t["team"] == team]

# ----------------------------------------------------
# Today tasks
# ----------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] == today
    ]

# ----------------------------------------------------
# Week tasks
# ----------------------------------------------------
def get_tasks_week(team):
    today = datetime.today().date()
    end = today + timedelta(days=7)
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] and today <= t["deadline_date"] <= end
    ]

# ----------------------------------------------------
# Pending tasks
# ----------------------------------------------------
def get_tasks_pending(team):
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] and t["status"] != "done"
    ]

# ----------------------------------------------------
# Update status
# ----------------------------------------------------
def update_task_status(title, team, new_status="done"):
    team = normalize_team(team)
    tasks = _filter_by_team(team)

    for t in tasks:
        if t["title"] == title:
            status_col = t["base"] + 3 + 1  # 1-based
            update_cell("Time Sheet", t["row_index"], status_col, new_status)
            return True

    return False
