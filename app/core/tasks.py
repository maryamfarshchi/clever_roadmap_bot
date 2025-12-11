# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


# ----------------------------------------------------
#  Normalize team text
# ----------------------------------------------------
def normalize_team(name):
    return str(name or "").strip().lower()


# ----------------------------------------------------
#  Clean Google Sheets date (remove RTL chars)
# ----------------------------------------------------
def clean_date_string(en):
    if not en:
        return ""
    # حذف کاراکترهای مخفی RTL و LRM و RLM
    return re.sub(r"[\u200f\u200e\u202a\u202b\u202c\u202d\u202e]", "", str(en)).strip()


# ----------------------------------------------------
#  Parse date
# ----------------------------------------------------
def parse_date(en):
    try:
        cleaned = clean_date_string(en)
        if not cleaned:
            return None
        return datetime.strptime(cleaned, DATE_FMT)
    except:
        return None


# ----------------------------------------------------
#  ساخت لیست کامل تسک‌ها از شیت
# ----------------------------------------------------
def _build_tasks():
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    data = rows[1:]  # رد شدن از هدر
    all_tasks = []
    today = datetime.today().date()

    for idx, row in enumerate(data):
        if not row:
            continue

        # ستون‌های 1 تا 4
        day_fa = row[0] if len(row) > 0 else ""
        date_fa = row[1] if len(row) > 1 else ""
        date_en = clean_date_string(row[2]) if len(row) > 2 else ""
        time_str = row[3] if len(row) > 3 else ""

        dt = parse_date(date_en)
        deadline_date = dt.date() if dt else None

        # هر تیم یک بلوک 5 تایی:
        groups = [
            (0, "production"),
            (1, "ai production"),
            (2, "digital"),
        ]

        for k, _logical_team in groups:
            base = 4 + 5 * k

            if len(row) <= base:
                continue

            title = row[base] if len(row) > base else ""
            content_type = row[base + 1] if len(row) > base + 1 else ""
            comment = row[base + 2] if len(row) > base + 2 else ""
            status = row[base + 3] if len(row) > base + 3 else ""
            team_name_cell = row[base + 4] if len(row) > base + 4 else ""

            if not title or not team_name_cell:
                continue

            team_norm = normalize_team(team_name_cell)
            if team_norm not in ("production", "ai production", "digital", "all"):
                continue

            delay_days = None
            if deadline_date:
                delay_days = (today - deadline_date).days

            # ساخت تسک
            all_tasks.append(
                {
                    "row_index": idx + 2,       # 1-based index
                    "group_index": k,           # 0=Prod,1=AI,2=Digital
                    "team": team_norm,
                    "title": str(title).strip(),
                    "type": content_type,
                    "comment": comment,
                    "status": str(status or "").strip().lower(),   # done / not yet / ""
                    "date_en": date_en,
                    "date_fa": date_fa,
                    "day_fa": day_fa,
                    "time": time_str,
                    "deadline_date": deadline_date,
                    "delay_days": delay_days,
                }
            )

    return all_tasks


# ----------------------------------------------------
#  دریافت تسک‌های تیم
# ----------------------------------------------------
def _filter_by_team(team):
    team_norm = normalize_team(team)

    # اگر یوزر ALL باشد، کل تیم‌ها را می‌آورد
    if team_norm == "all":
        return [t for t in _build_tasks()]

    return [t for t in _build_tasks() if t["team"] == team_norm]


# ----------------------------------------------------
#  تسک‌های امروز
# ----------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    tasks = []
    for t in _filter_by_team(team):
        if t["deadline_date"] and t["deadline_date"] == today:
            tasks.append(t)
    return tasks


# ----------------------------------------------------
#  تسک‌های این هفته (هفت روز آینده)
# ----------------------------------------------------
def get_tasks_week(team):
    today = datetime.today().date()
    week_limit = today + timedelta(days=7)
    tasks = []
    for t in _filter_by_team(team):
        d = t["deadline_date"]
        if d and today <= d <= week_limit:
            tasks.append(t)
    return tasks


# ----------------------------------------------------
#  Pending tasks
# ----------------------------------------------------
def get_tasks_pending(team):
    """
    تسک‌هایی که هنوز status = done ندارند
    و ددلاین دارند، یعنی:
    - امروز
    - گذشته
    - آینده نزدیک
    """
    tasks = []
    for t in _filter_by_team(team):
        if t["status"] == "done":
            continue
        if not t["deadline_date"]:
            continue
        tasks.append(t)
    return tasks


# ----------------------------------------------------
#  آپدیت وضعیت تسک
# ----------------------------------------------------
def update_task_status(title, team, new_status="done"):
    """
    نخستین تسکی که عنوان و تیمش مطابق باشد آپدیت می‌شود.
    """
    tasks = _filter_by_team(team)
    target = None

    for t in tasks:
        if str(t["title"]).strip() == str(title).strip():
            target = t
            break

    if not target:
        return False

    row_index = target["row_index"]
    group_idx = target["group_index"]

    # base = 4 + 5*k
    base = 4 + 5 * group_idx
    status_col = base + 3 + 1   # چون ما 0-based داریم → 1-based شیت

    update_cell("Time Sheet", row_index, status_col, new_status)
    return True
