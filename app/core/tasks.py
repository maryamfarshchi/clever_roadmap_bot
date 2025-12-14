# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
import pytz  # <-- حتماً pytz رو به requirements.txt اضافه کن

from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"

# تنظیم timezone ایران
IRAN_TZ = pytz.timezone('Asia/Tehran')


# ---------------- Helpers ----------------
def clean(s):
    return str(s or "").strip()


def normalize_team(s):
    return clean(s).lower()


def parse_date_any(v):
    """
    پارس تاریخ از انواع فرمت‌های ممکن در گوگل شیت
    """
    if not v:
        return None

    # اگر قبلاً datetime باشه
    if isinstance(v, datetime):
        return v.date()

    s = clean(v)
    # حذف کاراکترهای RTL و فضاهای اضافی
    s = re.sub(r"[\u200e\u200f\u202a-\u202e\s]+", "", s)

    # فرمت‌های احتمالی تاریخ
    formats = [
        "%m/%d/%Y",   # 12/14/2025
        "%d/%m/%Y",   # 14/12/2025
        "%Y/%m/%d",   # 2025/12/14
        "%Y-%m-%d",   # 2025-12-14
        "%d-%m-%Y",   # 14-12-2025
        "%m-%d-%Y",   # 12-14-2025
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    # اگر هیچ فرمتی کار نکرد، لاگ کن برای دیباگ
    print(f"[WARNING] Failed to parse date: '{v}' -> cleaned: '{s}'")
    return None


def get_today_iran():
    """تاریخ امروز به وقت ایران"""
    return datetime.now(IRAN_TZ).date()


# ---------------- Load tasks ----------------
def _load_tasks():
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        print("[INFO] Tasks sheet is empty or has no data rows.")
        return []

    data = rows[1:]  # رد کردن هدر
    today = get_today_iran()

    tasks = []

    for i, row in enumerate(data, start=2):
        # ایندکس ستون‌ها بر اساس شیت Tasks
        task_id = clean(row[0] if len(row) > 0 else "")
        team = normalize_team(row[1] if len(row) > 1 else "")
        date_en = row[2] if len(row) > 2 else None
        date_fa = row[3] if len(row) > 3 else ""
        title = clean(row[6] if len(row) > 6 else "")

        # ستون Done (S) - ایندکس 18
        done_raw = clean(row[18] if len(row) > 18 else "").lower()
        done = done_raw == "yes" or done_raw == "y"

        # فیلترهای ضروری
        if not task_id or not team or not title:
            continue

        deadline = parse_date_any(date_en)
        delay = (today - deadline).days if deadline else None

        tasks.append({
            "row_index": i,
            "task_id": task_id,
            "team": team,
            "title": title,
            "date_fa": date_fa or "نامشخص",
            "deadline": deadline,
            "delay_days": delay,
            "done": done,
        })

    print(f"[INFO] Loaded {len(tasks)} tasks from sheet.")
    return tasks


def _by_team(team):
    team_norm = normalize_team(team)
    tasks = _load_tasks()
    if team_norm == "all":
        return tasks
    return [t for t in tasks if t["team"] == team_norm]


# ---------------- Public APIs ----------------
def get_tasks_today(team):
    today = get_today_iran()
    yesterday = today - timedelta(days=1)
    return [t for t in _by_team(team) if t["deadline"] in (today, yesterday)]


def get_tasks_week(team):
    today = get_today_iran()
    end = today + timedelta(days=7)
    return [t for t in _by_team(team) if t["deadline"] and today <= t["deadline"] <= end]


def get_tasks_pending(team):
    """همه تسک‌های انجام‌نشده (بدون توجه به تاریخ)"""
    return [t for t in _by_team(team) if not t["done"]]


def update_task_status(task_id, new_status):
    """
    آپدیت وضعیت تسک
    new_status: معمولاً "Yes" یا خالی
    """
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return False

    task_id = str(task_id).strip()
    new_status_clean = clean(new_status)

    for i, row in enumerate(rows[1:], start=2):
        current_id = clean(row[0] if len(row) > 0 else "")
        if current_id == task_id:
            # آپدیت ستون Status (J - ایندکس 9 در لیست، اما 10 در گوگل شیت)
            update_cell(TASKS_SHEET, i, 10, new_status_clean)

            # آپدیت ستون Done (S - ایندکس 18 در لیست، 19 در گوگل شیت)
            done_value = "Yes" if new_status_clean.lower() in ["yes", "done", "y"] else ""
            update_cell(TASKS_SHEET, i, 19, done_value)

            print(f"[INFO] Task {task_id} status updated to '{new_status_clean}', Done = '{done_value}'")
            return True

    print(f"[WARNING] Task ID {task_id} not found for status update.")
    return False
