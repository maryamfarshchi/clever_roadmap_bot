# app/core/tasks.py
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from core.sheets import get_sheet, update_cell

DATE_FMT = "%m/%d/%Y"


# -------------------------------------------------------------------
#  نرمال‌سازی نام تیم
# -------------------------------------------------------------------
def normalize_team(name):
    return str(name or "").strip().lower()


# -------------------------------------------------------------------
#  تبدیل تاریخ سریالی فرمولی گوگل‌شیت → تاریخ میلادی
# -------------------------------------------------------------------
def excel_serial_to_date(serial):
    try:
        serial = float(serial)
        origin = datetime(1899, 12, 30)         # استاندارد اکسل
        return origin + timedelta(days=serial)
    except:
        return None


# -------------------------------------------------------------------
#  تبدیل تاریخ میلادی (سریالی یا متنی)
# -------------------------------------------------------------------
def parse_date(en):
    """
    تاریخ میلادی را از شیت بخواند (چه فرمول، چه متن).
    اگر مقدار عددی باشد (تاریخ فرمولی), تبدیل اکسل انجام می‌شود.
    """
    if not en:
        return None

    # اگر تاریخ به صورت عدد سطح پایین اکسل آمده:
    if isinstance(en, (int, float)):
        try:
            base = datetime(1899, 12, 30)
            return base + timedelta(days=float(en))
        except:
            return None

    # اگر رشته باشد (MM/DD/YYYY)
    try:
        return datetime.strptime(str(en), DATE_FMT)
    except:
        return None



# -------------------------------------------------------------------
#  ساخت لیست کامل تسک‌ها از شیت
# -------------------------------------------------------------------
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
        date_en_raw = row[2] if len(row) > 2 else ""
        time_str = row[3] if len(row) > 3 else ""

        dt = parse_date(date_en_raw)
        deadline_date = dt.date() if dt else None

        # هر تیم یک بلوک 5 ستونه:
        # base = 4 + 5*k → title, type, comment, status, team
        groups = [
            (0, "production"),
            (1, "ai production"),
            (2, "digital"),
        ]

        for k, _logical_team in groups:
            base = 4 + 5 * k

            if len(row) <= base + 4:
                continue

            title = row[base]
            ctype = row[base + 1]
            comment = row[base + 2]
            status = row[base + 3]
            team_name_cell = row[base + 4]

            if not title or not team_name_cell:
                continue

            team_norm = normalize_team(team_name_cell)
            if team_norm not in ("production", "ai production", "digital"):
                continue

            # محاسبه تأخیر
            delay_days = None
            if deadline_date:
                delay_days = (today - deadline_date).days

            t = {
                "row_index": idx + 2,  # 2 یعنی ردیف واقعی در شیت (ردیف 1 هدر است)
                "group_index": k,      # 0/1/2
                "team": team_norm,
                "title": str(title),
                "type": ctype,
                "comment": comment,
                "status": str(status or "").strip().lower(),  # done / not yet / ""
                "date_en": date_en_raw,
                "date_fa": date_fa,
                "day_fa": day_fa,
                "time": time_str,
                "deadline_date": deadline_date,
                "delay_days": delay_days,
            }

            all_tasks.append(t)

    return all_tasks


# -------------------------------------------------------------------
#  فیلتر براساس تیم
# -------------------------------------------------------------------
def _filter_by_team(team):
    team_norm = normalize_team(team)
    return [t for t in _build_tasks() if t["team"] == team_norm]


# -------------------------------------------------------------------
#  تسک‌های امروز
# -------------------------------------------------------------------
def get_tasks_today(team):
    today = datetime.today().date()
    return [t for t in _filter_by_team(team)
            if t["deadline_date"] and t["deadline_date"] == today]


# -------------------------------------------------------------------
#  تسک‌های این هفته
# -------------------------------------------------------------------
def get_tasks_week(team):
    today = datetime.today().date()
    week_limit = today + timedelta(days=7)

    return [
        t for t in _filter_by_team(team)
        if t["deadline_date"] and today <= t["deadline_date"] <= week_limit
    ]


# -------------------------------------------------------------------
#  تسک‌های انجام نشده
# -------------------------------------------------------------------
def get_tasks_pending(team):
    tasks = []
    for t in _filter_by_team(team):
        if t["status"] == "done":
            continue
        if not t["deadline_date"]:
            continue
        tasks.append(t)
    return tasks


# -------------------------------------------------------------------
#  آپدیت status تسک
# -------------------------------------------------------------------
def update_task_status(title, team, new_status="done"):
    tasks = _filter_by_team(team)
    target = None

    for t in tasks:
        if str(t["title"]).strip() == str(title).strip():
            target = t
            break

    if not target:
        return False

    row_index = target["row_index"]
    k = target["group_index"]

    # ستون status = base + 3 (base = 4 + 5*k)
    base = 4 + 5 * k
    status_col = (base + 3) + 1   # تبدیل 0-based → 1-based

    update_cell("Time Sheet", row_index, status_col, new_status)
    return True

