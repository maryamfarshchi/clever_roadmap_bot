# app/core/tasks.py
from core.sheets import get_sheet
from datetime import datetime, timedelta


# -----------------------------
#  تمیز کردن نام تیم
# -----------------------------
def normalize_team(t):
    if not t:
        return ""
    return str(t).strip().lower()


# -----------------------------
#  تبدیل تاریخ میلادی شیت (ستون Date)
# -----------------------------
def parse_date(en):
    if not en:
        return None
    try:
        # فرمت تایم‌شیت:  12/5/2025
        return datetime.strptime(en, "%m/%d/%Y")
    except Exception:
        return None


# -----------------------------
#   گرفتن تسک‌ها برای یک تیم
#   mode:
#     - today
#     - week
#     - pending (بدون status)
#     - late   (گذشته از امروز)
#     - esc    (بیش از ۵ روز تأخیر)
# -----------------------------
def get_tasks_for(team, mode=None):
    rows = get_sheet("Time Sheet")
    if not rows or len(rows) < 2:
        return []

    # ردیف اول = هدر
    data = rows[1:]

    team_norm = normalize_team(team)
    today = datetime.today()
    week_limit = today + timedelta(days=7)

    tasks = []

    # ساختار ستون‌های تایم‌شیت (index صفرم):
    #
    #  0  Day
    #  1  Shamsi_Date
    #  2  Date (EN)
    #  3  Time
    #
    #  4  خالی/رزرو (اگر هست نادیده می‌گیریم)
    #
    #  5..9   Production   → title1, type1, comment1, status1, team1
    # 10..14  Ai Production→ title2, type2, comment2, status2, team2
    # 15..19  Digital      → title3, type3, comment3, status3, team3
    #
    #   در هر بلاک ۵ تایی:
    #   1: Title
    #   2: Content Type
    #   3: Comment
    #   4: Status
    #   5: Team
    #

    for row in data:
        if not row:
            continue

        day_name = row[0] if len(row) > 0 else ""
        date_fa = row[1] if len(row) > 1 else ""
        date_en = row[2] if len(row) > 2 else ""
        time = row[3] if len(row) > 3 else ""

        d = parse_date(date_en)

        # ---------- Production (بلاک ۵تایی اول بعد از ستون 4) ----------
        title1, type1, comment1, status1, team1 = ([""] * 5)
        if len(row) > 9:
            title1, type1, comment1, status1, team1 = row[5:10]

        # ---------- Ai Production ----------
        title2, type2, comment2, status2, team2 = ([""] * 5)
        if len(row) > 14:
            title2, type2, comment2, status2, team2 = row[10:15]

        # ---------- Digital ----------
        title3, type3, comment3, status3, team3 = ([""] * 5)
        if len(row) > 19:
            title3, type3, comment3, status3, team3 = row[15:20]

        # =====================================================
        #   Production
        # =====================================================
        if (
            team_norm == "production"
            and normalize_team(team1) == "production"
            and title1
        ):
            tasks.append(
                {
                    "team": "Production",
                    "title": title1,
                    "type": type1,
                    "comment": comment1,
                    "status": status1,
                    "date": date_en,
                    "date_fa": date_fa,
                    "day": day_name,
                    "time": time,
                    "datetime": d,
                }
            )

        # =====================================================
        #   Ai Production
        # =====================================================
        if (
            team_norm == "ai production"
            and normalize_team(team2) == "ai production"
            and title2
        ):
            tasks.append(
                {
                    "team": "Ai Production",
                    "title": title2,
                    "type": type2,
                    "comment": comment2,
                    "status": status2,
                    "date": date_en,
                    "date_fa": date_fa,
                    "day": day_name,
                    "time": time,
                    "datetime": d,
                }
            )

        # =====================================================
        #   Digital
        # =====================================================
        if (
            team_norm == "digital"
            and normalize_team(team3) == "digital"
            and title3
        ):
            tasks.append(
                {
                    "team": "Digital",
                    "title": title3,
                    "type": type3,
                    "comment": comment3,
                    "status": status3,
                    "date": date_en,
                    "date_fa": date_fa,
                    "day": day_name,
                    "time": time,
                    "datetime": d,
                }
            )

    # ===========================
    # فیلترها
    # ===========================
    if mode == "today":
        return [
            t
            for t in tasks
            if t["datetime"] and t["datetime"].date() == today.date()
        ]

    if mode == "week":
        return [
            t
            for t in tasks
            if t["datetime"] and today <= t["datetime"] <= week_limit
        ]

    if mode == "pending":
        # تسک‌هایی که status خالی دارند
        return [t for t in tasks if not t["status"]]

    if mode == "late":
        return [
            t
            for t in tasks
            if t["datetime"] and t["datetime"].date() < today.date()
        ]

    if mode == "esc":
        # بیشتر از ۵ روز تأخیر
        esc_list = []
        for t in tasks:
            dt = t["datetime"]
            if not dt:
                continue
            delay = (today.date() - dt.date()).days
            if delay > 5:
                t_copy = dict(t)
                t_copy["delay_days"] = delay
                esc_list.append(t_copy)
        return esc_list

    return tasks
