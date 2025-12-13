# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


# ----------------------------------------------------
# Utils
# ----------------------------------------------------
def normalize_team(v):
    return str(v or "").strip().lower()


def clean_text(v):
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def clean_date_string(v):
    if not v:
        return ""
    return re.sub(r"[\u200e\u200f\u202a-\u202e]", "", str(v)).strip()


def parse_date(v):
    try:
        v = clean_date_string(v)
        if not v:
            return None
        return datetime.strptime(v, DATE_FMT).date()
    except:
        return None


# ----------------------------------------------------
# Build ALL tasks from Time Sheet
# ----------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]
    today = datetime.today().date()
    tasks = []

    # گروه‌ها دقیقاً مطابق شیت
    # 5-9  Production
    # 10-14 AI Production
    # 15-19 Digital
    GROUPS = [
        ("production", 5),
        ("ai production", 10),
        ("digital", 15),
    ]

    for row_idx, row in enumerate(data, start=2):

        # ستون‌های عمومی
        day_fa   = clean_text(row[0]) if len(row) > 0 else ""
        date_fa  = clean_text(row[1]) if len(row) > 1 else ""
        date_en  = row[2] if len(row) > 2 else ""
        time_val = clean_text(row[3]) if len(row) > 3 else ""

        deadline = parse_date(date_en)
        delay_days = (today - deadline).days if deadline else None

        for team_name, base in GROUPS:
            idx = base - 1  # چون row صفر‌بیسه

            title   = clean_text(row[idx])     if len(row) > idx     else ""
            ctype   = clean_text(row[idx + 1]) if len(row) > idx + 1 else ""
            comment = clean_text(row[idx + 2]) if len(row) > idx + 2 else ""
            status  = clean_text(row[idx + 3]) if len(row) > idx + 3 else ""
            teamcol = clean_text(row[idx + 4]) if len(row) > idx + 4 else ""

            # شرط‌های حیاتی
            if not title:
                continue
            if normalize_team(teamcol) not in ("digital", "production", "ai production", "all"):
                continue

            tasks.append({
                "row_index": row_idx,
                "base": base,
                "team": normalize_team(teamcol),
                "logical_team": team_name,
                "title": title,
                "type": ctype,
                "comment": comment,
                "status": status.lower(),  # done / not yet / ""
                "date_en": date_en,
                "date_fa": date_fa,
                "day_fa": day_fa,
                "time": time_val,
                "deadline": deadline,
                "delay_days": delay_days,
            })

    return tasks


# ----------------------------------------------------
# Filter by team (ALL supported)
# ----------------------------------------------------
def _by_team(team):
    team = normalize_team(team)
    all_tasks = _build_tasks()

    if team == "all":
        return all_tasks

    return [t for t in all_tasks if t["team"] == team]


# ----------------------------------------------------
# TODAY
# ----------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _by_team(team)
        if t["deadline"] == today
    ]


# ----------------------------------------------------
# WEEK
# ----------------------------------------------------
def get_tasks_week(team):
    today = datetime.today().date()
    limit = today + timedelta(days=7)

    return [
        t for t in _by_team(team)
        if t["deadline"] and today <= t["deadline"] <= limit
    ]


# ----------------------------------------------------
# PENDING (status خالی یا not yet)
# ----------------------------------------------------
def get_tasks_pending(team):
    return [
        t for t in _by_team(team)
        if t["deadline"]
        and t["status"] not in ("done", "yes")
    ]


# ----------------------------------------------------
# UPDATE STATUS
# ----------------------------------------------------
def update_task_status(title, team, new_status="done"):
    team = normalize_team(team)

    for t in _by_team(team):
        if t["title"] == clean_text(title):
            row = t["row_index"]
            status_col = t["base"] + 3  # status column (1-based)

            update_cell("Time Sheet", row, status_col, new_status)
            return True

    return False
