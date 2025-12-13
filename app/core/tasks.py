# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell


DATE_FMT = "%m/%d/%Y"


# --------------------------------------------------
# Utils
# --------------------------------------------------
def normalize_team(v):
    return str(v or "").strip().lower()


def clean_date(v):
    """
    Google Sheet date may contain RTL / invisible chars
    """
    if not v:
        return ""
    return re.sub(r"[\u200e\u200f\u202a-\u202e]", "", str(v)).strip()


def parse_date(v):
    try:
        v = clean_date(v)
        if not v:
            return None
        return datetime.strptime(v, DATE_FMT).date()
    except:
        return None


# --------------------------------------------------
# ستون‌های هر تیم (0-based)
# --------------------------------------------------
TEAM_BLOCKS = {
    "production": 4,      # 5–9
    "ai production": 9,   # 10–14
    "digital": 14,        # 15–19
}


# --------------------------------------------------
# Build all tasks (هسته اصلی)
# --------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    today = datetime.today().date()
    tasks = []

    for row_idx, row in enumerate(rows[1:], start=2):  # row_idx = index واقعی شیت
        if not row:
            continue

        day_fa   = row[0] if len(row) > 0 else ""
        date_fa  = row[1] if len(row) > 1 else ""
        date_en  = row[2] if len(row) > 2 else ""
        time_str = row[3] if len(row) > 3 else ""

        deadline = parse_date(date_en)
        delay_days = (today - deadline).days if deadline else None

        for team_name, base in TEAM_BLOCKS.items():

            if len(row) <= base + 4:
                continue

            title   = str(row[base] or "").strip()
            ctype   = str(row[base + 1] or "").strip()
            comment = str(row[base + 2] or "").strip()
            status  = str(row[base + 3] or "").strip().lower()
            team    = normalize_team(row[base + 4])

            # 🔴 شرط‌های حیاتی
            if not title:
                continue

            if team != team_name:
                continue

            tasks.append({
                "row_index": row_idx,
                "base": base,
                "team": team,
                "title": title,
                "type": ctype,
                "comment": comment,
                "status": status,            # "" = انجام نشده
                "date_fa": date_fa,
                "date_en": date_en,
                "time": time_str,
                "deadline_date": deadline,
                "delay_days": delay_days,
            })

    return tasks


# --------------------------------------------------
# فیلتر تیم
# --------------------------------------------------
def _by_team(team):
    team = normalize_team(team)
    return [t for t in _build_tasks() if t["team"] == team]


# --------------------------------------------------
# Today
# --------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _by_team(team)
        if t["deadline_date"] == today
    ]


# --------------------------------------------------
# Week (7 days)
# --------------------------------------------------
def get_tasks_week(team):
    today = datetime.today().date()
    end = today + timedelta(days=7)
    return [
        t for t in _by_team(team)
        if t["deadline_date"] and today <= t["deadline_date"] <= end
    ]


# --------------------------------------------------
# Pending (مهم‌ترین)
# --------------------------------------------------
def get_tasks_pending(team):
    """
    هر تسکی که:
    - title دارد
    - team درست است
    - status != done
    """
    return [
        t for t in _by_team(team)
        if t["status"] != "done"
    ]


# --------------------------------------------------
# Update status
# --------------------------------------------------
def update_task_status(title, team, new_status="done"):
    team = normalize_team(team)

    for t in _build_tasks():
        if t["team"] == team and t["title"] == title:
            status_col = t["base"] + 3 + 1  # 1-based
            update_cell("Time Sheet", t["row_index"], status_col, new_status)
            return True

    return False
