# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from pytz import timezone
from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"

# تایم‌زون ایران — از این به بعد همه جا از این استفاده می‌کنیم
IR_TZ = timezone('Asia/Tehran')

def now_iran():
    """همیشه تاریخ و ساعت فعلی ایران رو برمی‌گردونه"""
    return datetime.now(IR_TZ)

def today_iran():
    """فقط تاریخ (date) امروز ایران"""
    return now_iran().date()


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

    # فرمت‌های رایج در گوگل شیت
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
    today = today_iran()  # ← اینجا ایران

    tasks = []

    for i, row in enumerate(data, start=2):
        task_id = clean(row[0])
        team = normalize_team(row[1])
        date_en = row[2]
        date_fa = clean(row[3])
        title = clean(row[6])
        done_col = clean(row[18]).lower() if len(row) > 18 else ""  # ستون S

        if not task_id or not team or not title:
            continue

        deadline = parse_date_any(date_en)
        if not deadline:
            continue

        delay = (today - deadline).days

        tasks.append({
            "row_index": i,
            "task_id": task_id,
            "team": team,
            "title": title,
            "date_fa": date_fa,
            "deadline": deadline,
            "delay_days": delay,
            "done": done_col == "yes",
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


def get_tasks_pending(team):
    """فقطسک‌های انجام نشده که ددلاینشون گذشته یا امروز هست (یا فقط گذشته — انتخاب کن)"""
    today = today_iran()
    return [
        t for t in _by_team(team)
        if not t["done"] and t["deadline"] < today   # فقط overdue
        # اگر می‌خوای تسک‌های امروز هم بیاد: t["deadline"] <= today
    ]


def update_task_status(task_id, new_status):
    """
    new_status → "Yes" یا ""
    """
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return False

    for i, row in enumerate(rows[1:], start=2):
        if clean(row[0]) == task_id:
            # ستون J (Status) → شماره 10
            update_cell(TASKS_SHEET, i, 10, new_status)
            # ستون S (Done) → شماره 19
            done_value = "Yes" if new_status == "Yes" else "No"
            update_cell(TASKS_SHEET, i, 19, done_value)

            print(f"[TASK UPDATED] {task_id} → Status: {new_status}, Done: {done_value}")
            return True
    return False
