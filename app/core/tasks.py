# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


# ----------------------------------------------------
# utils
# ----------------------------------------------------
def normalize(text):
    return str(text or "").strip()


def normalize_team(name):
    return normalize(name).lower()


def clean_date_string(en):
    if not en:
        return ""
    return re.sub(r"[\u200f\u200e\u202a-\u202e]", "", str(en)).strip()


def parse_date(en):
    try:
        en = clean_date_string(en)
        if not en:
            return None
        return datetime.strptime(en, DATE_FMT).date()
    except:
        return None


# ----------------------------------------------------
# build all tasks from sheet
# ----------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    today = datetime.today().date()
    tasks = []

    for row_idx, row in enumerate(rows[1:], start=2):

        # عمومی
        day_fa   = row[0] if len(row) > 0 else ""
        date_fa  = row[1] if len(row) > 1 else ""
        date_en  = row[2] if len(row) > 2 else ""
        time_str = row[3] if len(row) > 3 else ""

        deadline = parse_date(date_en)
        delay = (today - deadline).days if deadline else None

        # بلاک‌ها دقیقاً طبق شیت
        blocks = [
            (4,  "production"),     # 5-9
            (9,  "ai production"),  # 10-14
            (14, "digital"),        # 15-19
        ]

        for base, logical_team in blocks:

            if len(row) <= base + 4:
                continue

            title   = normalize(row[base])
            ctype   = normalize(row[base + 1])
            comment = normalize(row[base + 2])
            status  = normalize(row[base + 3]).lower()
            team    = normalize_team(row[base + 4])

            # ❗ قانون تو: title باید حتماً باشد
            if not title:
                continue

            # تیم باید match شود
            if team not in ("production", "ai production", "digital", "all"):
                continue

            tasks.append({
                "row_index": row_idx,
                "base": base,
                "team": team,
                "logical_team": logical_team,
                "title": title,
                "type": ctype,
                "comment": comment,
                "status": status,   # done / not yet / ""
                "is_done": status == "done",
                "date_fa": date_fa,
                "date_en": date_en,
                "day_fa": day_fa,
                "time": time_str,
                "deadline_date": deadline,
                "delay_days": delay,
            })

    return tasks


# ----------------------------------------------------
# team filter
# ----------------------------------------------------
def _filter_by_team(team):
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
        t for t in _filter_by_team(team)
        if t["deadline_date"] == today
    ]


# ----------------------------------------------------
# WEEK (future only)
# ----------------------------------------------------
def get_tasks_week(team):
    today = datetime.today().date()
    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] and 0 <= (t["deadline_date"] - today).days <= 7
    ]


# ----------------------------------------------------
# 🔥 PENDING (قانون تو)
# ----------------------------------------------------
def get_tasks_pending(team):
    """
    هر تسکی که:
    - title دارد
    - status != done
    مهم نیست تاریخش کیه
    """
    tasks = []

    for t in _filter_by_team(team):
        if not t["is_done"]:
            tasks.append(t)

    return tasks


# ----------------------------------------------------
# update status
# ----------------------------------------------------
def update_task_status(title, team, new_status="done"):
    team = normalize_team(team)

    for t in _filter_by_team(team):
        if t["title"] == title:
            status_col = t["base"] + 4  # status column (0-based)
            update_cell("Time Sheet", t["row_index"], status_col + 1, new_status)
            return True

    return False
