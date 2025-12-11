import re
from datetime import datetime

# -------------------------------------
#  Safe getter
# -------------------------------------
def getval(row, index, default=""):
    """Prevent index errors when reading sheet rows"""
    try:
        return row[index]
    except:
        return default


# -------------------------------------
#  Clean text
# -------------------------------------
def clean_text(t):
    """Remove extra spaces, tabs, None, etc."""
    if t is None:
        return ""
    return re.sub(r"\s+", " ", str(t)).strip()


# -------------------------------------
#  Task list formatting
# -------------------------------------
def format_task_list(tasks, title="لیست تسک‌ها"):
    """
    Convert list of tasks into nice readable output.
    expected input:
       [{"title": "...", "date": "...", "time": "...", "status": "..."}]
    """
    if not tasks:
        return "تسکی برای نمایش وجود ندارد."

    msg = f"📋 *{title}*\n\n"
    for t in tasks:
        line = f"• {clean_text(t['title'])}"

        if t.get("date"):
            line += f"  🗓 {t['date']}"

        if t.get("time"):
            line += f"  ⏰ {t['time']}"

        msg += line + "\n"

    return msg


# -------------------------------------
#  Jalali date diff (for reminders)
# -------------------------------------
def jalali_diff(shamsi_date, today_jalali):
    """
    Calculate difference between 2 Persian dates.
    format must be yyyy/mm/dd
    return int(days)
    """
    try:
        y1, m1, d1 = map(int, shamsi_date.split("/"))
        y2, m2, d2 = map(int, today_jalali.split("/"))

        dt1 = datetime(y1, m1, d1)
        dt2 = datetime(y2, m2, d2)

        return (dt1 - dt2).days
    except:
        return None
