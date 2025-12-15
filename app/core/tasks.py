# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from dateutil.parser import parse as date_parse  # fallback هوشمند
import pytz  # برای timezone ایران

from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"

IRAN_TZ = pytz.timezone("Asia/Tehran")

# ---------------- Helpers ----------------
def clean(s):
    return str(s or "").strip()

def normalize_team(s):
    return clean(s).lower().replace("ai production", "aiproduction")  # برای هماهنگی

def parse_date_any(v):
    """
    پارس هوشمند تاریخ از شیت (string با MM/DD/YYYY)
    """
    if not v:
        return None

    s = clean(v)
    # پاک کردن کاراکترهای RTL
    s = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s)

    # اول سعی با فرمت اصلی
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        pass

    # fallback هوشمند (هر فرمتی رو بگیره)
    try:
        return date_parse(s, dayfirst=False, yearfirst=False).date()
    except:
        print(f"[DEBUG] Parse date failed for: {v}")
        return None


# ---------------- Load tasks ----------------
def _load_tasks():
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        print("[DEBUG] Tasks sheet empty or error")
        return []

    data = rows[1:]
    today = datetime.now(IRAN_TZ).date()  # تاریخ ایران
    print(f"[DEBUG] Today (Iran): {today}")

    tasks = []

    for i, row in enumerate(data, start=2):
        if len(row) < 19:
            continue  # ردیف ناقص

        task_id = clean(row[0])
        team = normalize_team(row[1])
        date_en = row[2]
        date_fa = clean(row[3])
        title = clean(row[6])
        status = clean(row[9]).lower()
        done = clean(row[18]).lower()

        if not task_id or not team or not title:
            continue

        deadline = parse_date_any(date_en)
        if not deadline:
            print(f"[DEBUG] Skip task {task_id} - bad date: {date_en}")
            continue

        delay = (today - deadline).days
        print(f"[DEBUG] Task {task_id} | Deadline: {deadline} | Delay: {delay} | Status: {status} | Done: {done}")

        # تشخیص انجام شده: از هر دو ستون
        is_done = (done == "yes" or done == "y") or ("done" in status or "yes" in status or "انجام شد" in status)

        tasks.append({
            "row_index": i,
            "task_id": task_id,
            "team": team,
            "title": title,
            "date_fa": date_fa,
            "deadline": deadline,
            "delay_days": delay,
            "done": is_done,
            "status": status,
        })

    return tasks


def _by_team(team):
    team_norm = normalize_team(team)
    tasks = _load_tasks()
    if team_norm == "all":
        return tasks
    return [t for t in tasks if t["team"] == team_norm]


# ---------------- Public APIs ----------------
def get_tasks_today(team):
    """کارهای امروز (delay == 0) + دیروز (برای جبران timezone)"""
    today = datetime.now(IRAN_TZ).date()
    yesterday = today - timedelta(days=1)
    return [
        t for t in _by_team(team)
        if t["deadline"] in (today, yesterday) and not t["done"]
    ]


def get_tasks_week(team):
    today = datetime.now(IRAN_TZ).date()
    end = today + timedelta(days=7)
    return [
        t for t in _by_team(team)
        if today <= t["deadline"] <= end and not t["done"]
    ]


def get_tasks_pending(team):
    """همه تسک‌های انجام نشده (گذشته + امروز، آینده رو حذف کن اگر نمی‌خوای)"""
    return [
        t for t in _by_team(team)
        if not t["done"] and t["delay_days"] >= 0  # فقط گذشته و امروز
    ]


def update_task_status(task_id, new_status):
    rows = get_sheet(TASKS_SHEET)
    for i, row in enumerate(rows[1:], start=2):
        if clean(row[0]) == task_id:
            update_cell(TASKS_SHEET, i, 10, new_status)  # Status
            if "done" in new_status.lower():
                update_cell(TASKS_SHEET, i, 19, "YES")  # Done
            return True
    return False
