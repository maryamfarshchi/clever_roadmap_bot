# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


def normalize_team(name):
    return str(name or "").strip().lower()


def parse_date(en):
    if not en:
        return None
    try:
        return datetime.strptime(str(en), DATE_FMT).date()
    except Exception:
        return None


# ----------------------------------------------------
# ساخت همه تسک‌ها
# ----------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]
    today = datetime.today().date()
    tasks = []

    for idx, row in enumerate(data):
        if not row:
            continue

        # ستون‌های عمومی
        day_fa   = row[0] if len(row) > 0 else ""
        date_fa  = row[1] if len(row) > 1 else ""
        date_en  = row[2] if len(row) > 2 else ""
        time_str = row[3] if len(row) > 3 else ""

        deadline = parse_date(date_en)
        delay_days = (today - deadline).days if deadline else None

        # Production / AI / Digital
        groups = [
            (4, "production"),
            (9, "ai production"),
            (14, "digital"),
        ]

        for base, logical_team in groups:
            if len(row) <= base + 4:
                continue

            title   = row[base] or "بدون عنوان"
            ctype   = row[base + 1]
            comment = row[base + 2]
            status  = str(row[base + 3] or "").strip().lower()
            team    = normalize_team(row[base + 4])

            if team != logical_team:
                continue

            tasks.append({
                "row_index": idx + 2,
                "base": base,
                "team": team,
                "title": str(title),
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


def _filter_by_team(team):
    team = normalize_team(team)
    all_tasks = _build_tasks()

    if team == "all":
        return all_tasks

    return [t for t in all_tasks if t["team"] == team]


# ----------------------------------------------------
# APIها
# ----------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] == today
    ]


def get_tasks_week(team):
    today = datetime.today().date()
    week_limit = today + timedelta(days=7)
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] and today <= t["deadline_date"] <= week_limit
    ]


def get_tasks_pending(team):
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] and t["status"] != "done"
    ]


def update_task_status(title, team, new_status="done"):
    for t in _filter_by_team(team):
        if t["title"].strip() == title.strip():
            status_col = t["base"] + 3 + 1  # 1-based
            update_cell("Time Sheet", t["row_index"], status_col, new_status)
            return True
    return False
