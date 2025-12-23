# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
import re
import json
import pytz

from core.sheets import get_sheet, update_cell, invalidate
from core.logging import log_error

TASKS_SHEET = "Tasks"
TIME_SHEET = "Time Sheet"

IRAN_TZ = pytz.timezone("Asia/Tehran")

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def clean(s):
    s = str(s or "").strip()
    # حذف کاراکترهای کنترل جهت
    s = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s)
    # تبدیل ارقام فارسی/عربی به انگلیسی
    return s.translate(_FA_DIGITS).strip()

def normalize_team(s: str) -> str:
    return clean(s).lower().replace("ai production", "aiproduction").replace(" ", "")

PERSIAN_WEEKDAYS = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنجشنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یکشنبه",
}

def weekday_fa(d: date) -> str:
    return PERSIAN_WEEKDAYS.get(d.weekday(), "")

def parse_time_hhmm(s: str):
    s = clean(s)
    if not s:
        return None
    m = re.match(r"^(\d{1,2})[:٫](\d{1,2})$", s)
    if not m:
        return None
    h = int(m.group(1))
    mi = int(m.group(2))
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return (h, mi)
    return None

# Jalali -> Gregorian
def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    jy += 1595
    days = -355668 + (365 * jy) + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186

    gy = 400 * (days // 146097)
    days %= 146097

    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1

    gy += 4 * (days // 1461)
    days %= 1461

    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    mdays = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > mdays[gm]:
        gd -= mdays[gm]
        gm += 1
    return date(gy, gm, gd)

def parse_jalali_date(date_fa: str):
    s = clean(date_fa).replace("-", "/")
    if not s:
        return None
    parts = [p for p in s.split("/") if p.strip()]
    if len(parts) != 3:
        return None
    try:
        y = int(parts[0]); m = int(parts[1]); d = int(parts[2])
    except ValueError:
        return None
    if y < 1200 or y > 1600 or m < 1 or m > 12 or d < 1 or d > 31:
        return None
    return jalali_to_gregorian(y, m, d)

def _find_col(headers, aliases, fallback_index=None):
    hs = [clean(h).lower() for h in headers]
    for a in aliases:
        a = a.lower()
        for i, h in enumerate(hs):
            if h == a:
                return i
    for a in aliases:
        a = a.lower()
        for i, h in enumerate(hs):
            if a in h:
                return i
    return fallback_index

async def get_tasks_schema(rows):
    headers = rows[0] if rows and isinstance(rows[0], list) else []

    schema = {
        "task_id": 0,
        "team": 1,
        "date_fa": 3,
        "time": 5,
        "title": 6,
        "type": 7,
        "comment": 8,
        "status": 9,
        "done": 17,
        "reminders": 18,
    }

    if headers:
        schema["task_id"]   = _find_col(headers, ["taskid", "task_id", "id", "کد", "شناسه", "task id"], schema["task_id"])
        schema["team"]      = _find_col(headers, ["team", "تیم"], schema["team"])
        schema["date_fa"]   = _find_col(headers, ["date fa", "date_fa", "jalali", "تاریخ", "deadline"], schema["date_fa"])
        schema["time"]      = _find_col(headers, ["time", "ساعت"], schema["time"])
        schema["title"]     = _find_col(headers, ["content title", "title", "task", "عنوان", "شرح", "نام تسک"], schema["title"])
        schema["type"]      = _find_col(headers, ["content type", "type", "سبک محتوا", "نوع محتوا"], schema["type"])
        schema["comment"]   = _find_col(headers, ["comment", "description", "توضیحات", "توضیحات بیشتر", "کامنت"], schema["comment"])
        schema["status"]    = _find_col(headers, ["status", "وضعیت"], schema["status"])
        schema["done"]      = _find_col(headers, ["done", "is_done", "انجام شد", "تحویل شد"], schema["done"])
        schema["reminders"] = _find_col(headers, ["reminders", "یادآوری", "reminder"], schema["reminders"])

    return schema

def format_task_block(t: dict, include_delay: bool = False) -> str:
    title = clean(t.get("title")) or "بدون عنوان"
    day = clean(t.get("day_fa"))
    date_fa = clean(t.get("date_fa"))
    time = clean(t.get("time"))

    lines = [f"📌 <b>{title}</b>"]
    if day or date_fa:
        lines.append(f"🗓️ {day} | {date_fa}".strip())
    if time:
        lines.append(f"⏰ {time}")

    ctype = clean(t.get("type"))
    if ctype:
        lines.append(f"🧩 <b>سبک محتوا:</b> {ctype}")

    comment = clean(t.get("comment"))
    if comment:
        lines.append(f"💬 <b>توضیحات بیشتر:</b> {comment}")

    if include_delay and int(t.get("delay_days", 0)) > 0:
        lines.append(f"⏳ <b>{t['delay_days']} روز تاخیر</b>")

    return "\n".join(lines)

def group_tasks_by_date(tasks: list):
    mp = {}
    for t in tasks:
        d = t["date_en"]
        mp.setdefault(d, []).append(t)
    return sorted(mp.items(), key=lambda x: x[0])

async def load_tasks():
    rows = await get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []

    schema = await get_tasks_schema(rows)
    today = datetime.now(IRAN_TZ).date()

    out = []
    for i, row in enumerate(rows[1:], start=2):
        if not isinstance(row, list):
            continue

        task_id = clean(row[schema["task_id"]]) if len(row) > schema["task_id"] else ""
        if not task_id:
            continue

        date_fa = clean(row[schema["date_fa"]]) if len(row) > schema["date_fa"] else ""
        date_en = parse_jalali_date(date_fa)
        if not date_en:
            continue

        title = clean(row[schema["title"]]) if len(row) > schema["title"] else ""
        if not title:
            log_error(f"Task title empty for task_id={task_id} row={i}")
            continue

        delay_days = (today - date_en).days

        reminders_str = clean(row[schema["reminders"]]) if len(row) > schema["reminders"] else "{}"
        try:
            reminders = json.loads(reminders_str) if reminders_str else {}
            if not isinstance(reminders, dict):
                reminders = {}
        except Exception:
            reminders = {}

        done_val = clean(row[schema["done"]]) if len(row) > schema["done"] else ""
        done = done_val.lower() in ["yes", "true", "1", "done", "تمام", "انجام شد"]

        out.append({
            "row_index": i,
            "task_id": task_id,
            "team": normalize_team(row[schema["team"]]) if len(row) > schema["team"] else "",
            "date_en": date_en,
            "day_fa": weekday_fa(date_en),
            "date_fa": date_fa,
            "time": clean(row[schema["time"]]) if len(row) > schema["time"] else "",
            "title": title,
            "type": clean(row[schema["type"]]) if len(row) > schema["type"] else "",
            "comment": clean(row[schema["comment"]]) if len(row) > schema["comment"] else "",
            "status": clean(row[schema["status"]]) if len(row) > schema["status"] else "In Progress",
            "done": done,
            "reminders": reminders,
            "delay_days": delay_days,
            "_schema": schema,
        })

    return out

async def get_tasks_today(team: str):
    tasks = await load_tasks()
    today = datetime.now(IRAN_TZ).date()
    tn = normalize_team(team)
    return [t for t in tasks if t["date_en"] == today and t["team"] == tn and not t["done"]]

async def get_tasks_next_7_days(team: str, start_date: date | None = None):
    tasks = await load_tasks()
    start = start_date or datetime.now(IRAN_TZ).date()
    end = start + timedelta(days=6)  # 7 روز شامل امروز
    tn = normalize_team(team)
    return [t for t in tasks if start <= t["date_en"] <= end and t["team"] == tn and not t["done"]]

async def get_tasks_not_done(team: str, ref_date: date | None = None):
    tasks = await load_tasks()
    today = ref_date or datetime.now(IRAN_TZ).date()
    tn = normalize_team(team)
    return [t for t in tasks if t["date_en"] < today and t["team"] == tn and not t["done"]]

async def update_task_status(task_id: str, new_status: str):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            schema = t.get("_schema") or {}
            col_status = int(schema.get("status", 9)) + 1
            col_done = int(schema.get("done", 17)) + 1

            ok1 = await update_cell(TASKS_SHEET, t["row_index"], col_status, new_status)

            ok2 = True
            if new_status.strip().lower() in ["done", "completed", "finish", "finished", "تمام", "دان", "انجام شد"]:
                ok2 = await update_cell(TASKS_SHEET, t["row_index"], col_done, "YES")

            if ok1 and ok2:
                invalidate(TASKS_SHEET)
                return True
            return False
    return False

async def set_task_reminders_json(task_id: str, reminders_dict: dict):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            schema = t.get("_schema") or {}
            col_rem = int(schema.get("reminders", 18)) + 1
            payload = json.dumps(reminders_dict or {}, ensure_ascii=False)
            ok = await update_cell(TASKS_SHEET, t["row_index"], col_rem, payload)
            if ok:
                invalidate(TASKS_SHEET)
            return ok
    return False

async def update_task_reminder(task_id: str, key: str, value):
    tasks = await load_tasks()
    for t in tasks:
        if t["task_id"] == task_id:
            reminders = t["reminders"] or {}
            reminders[key] = value
            return await set_task_reminders_json(task_id, reminders)
    return False
