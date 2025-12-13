# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
import re
from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"
DATE_FMT = "%m/%d/%Y"


# ----------------------------
# Helpers
# ----------------------------
def _norm(s):
    return str(s or "").strip()

def _norm_team(s):
    return _norm(s).lower()

def _clean_invis(s):
    # حذف کاراکترهای مخفی RTL/LRM/RLM
    return re.sub(r"[\u200f\u200e\u202a\u202b\u202c\u202d\u202e]", "", str(s)).strip()

def parse_date_en(v):
    """
    قبول می‌کند:
    - '12/13/2025'
    - '2025-12-13'
    - عدد سریال گوگل شیت (مثل 45678 یا '45678')
    - datetime/date
    """
    if v is None or v == "":
        return None

    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()

    s = _clean_invis(v)

    # اگر عدد سریال بود
    try:
        if re.fullmatch(r"\d+(\.\d+)?", s):
            serial = float(s)
            # Google Sheets serial date base: 1899-12-30
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=serial)).date()
    except:
        pass

    # YYYY-MM-DD
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return datetime.strptime(s, "%Y-%m-%d").date()
    except:
        pass

    # MM/DD/YYYY (با تک رقمی هم اوکیه)
    try:
        return datetime.strptime(s, DATE_FMT).date()
    except:
        return None


def _extract_rows(raw):
    """
    get_sheet ممکنه list بده، یا dict (بسته به وب‌اپ).
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("values", "rows", "data"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]
    return []


# ----------------------------
# Load tasks from Tasks sheet
# ----------------------------
def _load_tasks():
    raw = get_sheet(TASKS_SHEET)
    rows = _extract_rows(raw)

    if not rows or len(rows) < 2:
        return []

    header = [str(x).strip() for x in rows[0]]
    data = rows[1:]

    def col(name, default=-1):
        try:
            return header.index(name)
        except:
            return default

    i_taskid = col("TaskID")
    i_team   = col("Team")
    i_dateen = col("Date_EN")
    i_datefa = col("Date_FA")
    i_day    = col("DayName")
    i_time   = col("Time")
    i_title  = col("Content Title")
    i_type   = col("Content Type")
    i_comm   = col("Comment")
    i_status = col("Status")
    i_done   = col("Done")  # آخر شیت معمولا

    # اگر هدر دقیق نبود، حداقل با ترتیب استاندارد جلو برو
    if i_taskid == -1 and len(header) >= 10:
        i_taskid, i_team, i_dateen, i_datefa, i_day, i_time, i_title, i_type, i_comm, i_status = range(10)
        # Done ممکنه آخر باشه:
        i_done = len(header) - 1

    today = datetime.now().date()
    out = []

    for r_idx, row in enumerate(data, start=2):  # چون ردیف 1 هدره
        if not row:
            continue

        task_id = _norm(row[i_taskid]) if i_taskid >= 0 and len(row) > i_taskid else ""
        team    = _norm_team(row[i_team]) if i_team >= 0 and len(row) > i_team else ""
        title   = _norm(row[i_title]) if i_title >= 0 and len(row) > i_title else ""

        # شرط تو: تایتل باید حتما داشته باشه
        if not title:
            continue

        date_en_raw = row[i_dateen] if i_dateen >= 0 and len(row) > i_dateen else ""
        deadline = parse_date_en(date_en_raw)

        status = _norm_team(row[i_status]) if i_status >= 0 and len(row) > i_status else ""
        done   = _norm_team(row[i_done]) if i_done >= 0 and len(row) > i_done else ""

        # اگر Done=Yes بود، done حساب کن حتی اگر status خالیه
        is_done = (status == "done") or (done == "yes") or (done == "true")

        delay_days = None
        if deadline:
            delay_days = (today - deadline).days

        out.append({
            "row_index": r_idx,
            "task_id": task_id,
            "team": team,
            "title": title,
            "type": _norm(row[i_type]) if i_type >= 0 and len(row) > i_type else "",
            "comment": _norm(row[i_comm]) if i_comm >= 0 and len(row) > i_comm else "",
            "status": status,          # done / not yet / ""
            "done": done,              # yes / ""
            "date_en": _clean_invis(date_en_raw),
            "date_fa": _norm(row[i_datefa]) if i_datefa >= 0 and len(row) > i_datefa else "",
            "day_name": _norm(row[i_day]) if i_day >= 0 and len(row) > i_day else "",
            "time": _norm(row[i_time]) if i_time >= 0 and len(row) > i_time else "",
            "deadline_date": deadline,
            "delay_days": delay_days,
            "is_done": is_done,
        })

    return out


def _by_team(team):
    team = _norm_team(team)
    tasks = _load_tasks()
    if team == "all":
        return tasks
    return [t for t in tasks if _norm_team(t["team"]) == team]


# ----------------------------
# Public API used by handler
# ----------------------------
def get_tasks_today(team):
    today = datetime.now().date()
    return [t for t in _by_team(team) if t["deadline_date"] and t["deadline_date"] == today and not t["is_done"]]


def get_tasks_week(team):
    today = datetime.now().date()
    week_limit = today + timedelta(days=7)
    return [
        t for t in _by_team(team)
        if t["deadline_date"] and today <= t["deadline_date"] <= week_limit and not t["is_done"]
    ]


def get_tasks_pending(team):
    # هر چیزی که done نیست و تاریخ دارد
    return [t for t in _by_team(team) if (not t["is_done"]) and t["deadline_date"]]


def update_task_status(task_id, new_status="done"):
    """
    با TaskID آپدیت می‌کند.
    new_status: "done" یا "not yet"
    """
    tasks = _load_tasks()
    target = None
    for t in tasks:
        if _norm(t["task_id"]) == _norm(task_id):
            target = t
            break

    if not target:
        return False

    # ستون Status در Tasks شیت = ستون 10 (J) طبق فرمت استاندارد
    # (TaskID..Status = 10 ستون)
    status_col = 10  # 1-based
    update_cell(TASKS_SHEET, target["row_index"], status_col, new_status)
    return True
