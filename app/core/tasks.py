# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from pytz import timezone
from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"

# تایم‌زون ایران
IR_TZ = timezone('Asia/Tehran')

def today_iran():
    return datetime.now(IR_TZ).date()

# ---------------- Helpers ----------------
def clean(s):
    return str(s or "").strip()

def normalize_team(s):
    return clean(s).lower()

def parse_date_any(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()
    s = clean(v)
    s = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s)
    for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return None

# ---------------- Load tasks ----------------
def _load_tasks():
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []
    data = rows[1:]
    today = today_iran()
    tasks = []
    for i, row in enumerate(data, start=2):
        if len(row) < 1:
            continue
        task_id = clean(row[0])
        team = normalize_team(row[1])
        date_en = row[2] if len(row) > 2 else None
        date_fa = clean(row[3]) if len(row) > 3 else ""
        title = clean(row[6]) if len(row) > 6 else ""
        # ستون Status (J) → index 9
        status_col = clean(row[9]).lower() if len(row) > 9 else ""
        # ستون Done (S) → index 18
        done_col = clean(row[18]).lower() if len(row) > 18 else ""
        if not task_id or not team or not title:
            continue
        deadline = parse_date_any(date_en)
        if not deadline:
            continue
        delay = (today - deadline).days
        # انجام شده اگر حداقل یکی از Status یا Done برابر Yes باشه
        is_done = (status_col == "yes") or (done_col == "yes")
        tasks.append({
            "row_index": i,
            "task_id": task_id,
            "team": team,
            "title": title,
            "date_fa": date_fa,
            "deadline": deadline,
            "delay_days": delay,
            "done": is_done,
        })
    return tasks

def _by_team(team):
    team = normalize_team(team)
    tasks = _load_tasks()
    return tasks if team == "all" else [t for t in tasks if t["team"] == team]

# ---------------- Public APIs ----------------
def get_tasks_today(team):
    today = today_iran()
    yesterday = today - timedelta(days=1)
    return [t for t in _by_team(team) if t["deadline"] in (today, yesterday)]

def get_tasks_week(team):
    today = today_iran()
    end = today + timedelta(days=7)
    return [t for t in _by_team(team) if today <= t["deadline"] <= end]

# ★ همه تسک‌های انجام نشده (بدون محدودیت تاریخ)
def get_tasks_pending(team):
    return [t for t in _by_team(team) if not t["done"]]

def update_task_status(task_id, new_status):
    """
    new_status: "Yes" یا ""
    """
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return False
    for i, row in enumerate(rows[1:], start=2):
        if clean(row[0]) == task_id:
            # آپدیت Status (ستون J → 10)
            update_cell(TASKS_SHEET, i, 10, new_status)
            # آپدیت Done (ستون S → 19)
            done_value = "Yes" if new_status == "Yes" else "No"
            update_cell(TASKS_SHEET, i, 19, done_value)
            print(f"[TASK UPDATED] {task_id} → Status: {new_status} | Done: {done_value}")
            return True
    print(f"[TASK UPDATE FAILED] TaskID {task_id} not found")
    return False
