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
#  تبدیل تاریخ میلادی شیت
# -----------------------------
def parse_date(en):
    try:
        return datetime.strptime(en, "%m/%d/%Y")
    except:
        return None


# -----------------------------
#   گرفتن تسک‌ها
# -----------------------------
def get_tasks_for(team, mode=None):
    rows = get_sheet("Time Sheet")
    data = rows[1:]  # skip header

    team = normalize_team(team)
    today = datetime.today()
    week_limit = today + timedelta(days=7)

    tasks = []

    #   ستون‌های تایم‌شیت تو:
    #
    #   0  Day
    #   1  Shamsi
    #   2  Date (EN)
    #   3  Time
    #
    #   4-8   Production
    #   9-13  Ai Production
    #   14-18 Digital
    #

    for row in data:
        date_en = row[2]
        time = row[3]

        # --- Production
        (title1, type1, comment1, status1, team1) = row[4:9]

        # --- Ai Production
        (title2, type2, comment2, status2, team2) = row[9:14]

        # --- Digital
        (title3, type3, comment3, status3, team3) = row[14:19]

        d = parse_date(date_en)

        # -----------------------------
        #   Production
        # -----------------------------
        if team == "production" and normalize_team(team1) == "production" and title1:
            tasks.append({
                "title": title1,
                "type": type1,
                "comment": comment1,
                "status": status1,
                "date": date_en,
                "datetime": d,
                "time": time,
            })

        # -----------------------------
        #   Ai Production
        # -----------------------------
        if team == "ai production" and normalize_team(team2) == "ai production" and title2:
            tasks.append({
                "title": title2,
                "type": type2,
                "comment": comment2,
                "status": status2,
                "date": date_en,
                "datetime": d,
                "time": time,
            })

        # -----------------------------
        #   Digital
        # -----------------------------
        if team == "digital" and normalize_team(team3) == "digital" and title3:
            tasks.append({
                "title": title3,
                "type": type3,
                "comment": comment3,
                "status": status3,
                "date": date_en,
                "datetime": d,
                "time": time,
            })

    # -----------------------------
    #   فیلترهای کاربردی
    # -----------------------------
    if mode == "today":
        return [t for t in tasks if t["datetime"] and t["datetime"].date() == today.date()]

    if mode == "week":
        return [t for t in tasks if t["datetime"] and today <= t["datetime"] <= week_limit]

    if mode == "pending":
        return [t for t in tasks if not t["status"]]

    if mode == "late":
        return [t for t in tasks if t["datetime"] and t["datetime"] < today]

    if mode == "esc":
        return [t for t in tasks if t["datetime"] and (today - t["datetime"]).days > 5]

    return tasks
