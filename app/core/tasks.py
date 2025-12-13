# app/core/tasks.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from datetime import datetime, timedelta, date
import re
from core.sheets import get_sheet, update_cell

TASKS_SHEET = "Tasks"

# ----------------------------
# Helpers
# ----------------------------

_RTL_CHARS_RE = re.compile(r"[\u200f\u200e\u202a-\u202e]")

def _norm(s) -> str:
    return str(s or "").strip()

def _norm_lower(s) -> str:
    return _norm(s).lower()

def _clean_rtl(s) -> str:
    if s is None:
        return ""
    return _RTL_CHARS_RE.sub("", str(s)).strip()

def _safe_get(row, idx, default=""):
    try:
        return row[idx]
    except Exception:
        return default

def _normalize_team(team_raw: str) -> str:
    """
    Canonical teams:
      - production
      - ai production
      - digital
      - all
    """
    t = _clean_rtl(team_raw)
    t = re.sub(r"\s+", " ", t).strip().lower()
    t = t.replace("_", " ").replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()

    if not t:
        return ""

    if t == "all":
        return "all"

    # ai production variations: "aiproduction", "ai production", "ai  production"
    if "ai" in t and "production" in t:
        return "ai production"

    if "production" == t:
        return "production"

    if "digital" == t:
        return "digital"

    # sometimes they write "AiProduction" in strange forms
    if t.replace(" ", "") == "aiproduction":
        return "ai production"

    return t  # fallback (but usually one of above)

def _parse_date_en(v) -> date | None:
    """
    Accepts:
      - "12/4/2025"
      - "12/04/2025"
      - "12/4/2025 0:00:00"
      - "2025-12-04"
      - numeric serial (rare)
    """
    if v is None or v == "":
        return None

    # numeric serial (Google/Excel date)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        serial = float(v)
        # Excel/Google base: 1899-12-30 (works for Google-style serials)
        base = date(1899, 12, 30)
        try:
            return base + timedelta(days=int(serial))
        except Exception:
            return None

    s = _clean_rtl(v)
    if not s:
        return None

    # keep only date-part if time is attached
    s = s.split()[0].strip()

    fmts = [
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except Exception:
            pass

    # last resort: try manual split m/d/y
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
            m, d, y = [int(p.strip()) for p in parts]
            if 1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100:
                try:
                    return date(y, m, d)
                except Exception:
                    return None

    return None

def _is_done(status_val: str, done_val: str) -> bool:
    """
    Done if:
      - Status == "done"
      - or Done == "Yes"
    """
    s = _norm_lower(status_val)
    d = _norm_lower(done_val)
    if s == "done":
        return True
    if d == "yes":
        return True
    return False

def _header_key(x: str) -> str:
    # normalize header names to match even if spaces/underscores differ
    t = _clean_rtl(x).strip().lower()
    t = t.replace("_", "").replace(" ", "")
    return t

def _colmap_from_header(header_row) -> dict:
    """
    Build column index map from the header row.
    Works even if columns are moved a bit.
    """
    m = {}
    for i, h in enumerate(header_row or []):
        k = _header_key(h)
        if not k:
            continue
        m[k] = i
    return m

def _get_col(m, *names, default=None):
    for n in names:
        k = _header_key(n)
        if k in m:
            return m[k]
    return default

# ----------------------------
# Load tasks from "Tasks"
# ----------------------------

def _load_tasks():
    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return []

    header = rows[0]
    m = _colmap_from_header(header)

    # column indices (fallbacks are based on your Tasks template)
    c_taskid  = _get_col(m, "TaskID", default=0)
    c_team    = _get_col(m, "Team", default=1)
    c_date_en = _get_col(m, "Date_EN", "DateEN", default=2)
    c_date_fa = _get_col(m, "Date_FA", "DateFA", default=3)
    c_dayname = _get_col(m, "DayName", default=4)
    c_time    = _get_col(m, "Time", default=5)
    c_title   = _get_col(m, "Content Title", "ContentTitle", default=6)
    c_type    = _get_col(m, "Content Type", "ContentType", default=7)
    c_comment = _get_col(m, "Comment", default=8)
    c_status  = _get_col(m, "Status", default=9)
    c_done    = _get_col(m, "Done", default=18)

    today = datetime.now().date()
    all_tasks = []

    for r_idx, row in enumerate(rows[1:], start=2):  # sheet row index (1-based)
        if not row:
            continue

        task_id = _safe_get(row, c_taskid, "")
        team_raw = _safe_get(row, c_team, "")
        team = _normalize_team(team_raw)

        date_en_raw = _safe_get(row, c_date_en, "")
        deadline_date = _parse_date_en(date_en_raw)

        date_fa = _safe_get(row, c_date_fa, "")
        day_name = _safe_get(row, c_dayname, "")
        time_str = _safe_get(row, c_time, "")

        title = _safe_get(row, c_title, "")
        ctype = _safe_get(row, c_type, "")
        comment = _safe_get(row, c_comment, "")
        status = _safe_get(row, c_status, "")
        done_val = _safe_get(row, c_done, "")

        title_clean = _norm(title)

        # شرط شما: تایتل حتما باید داشته باشه
        if not title_clean:
            continue

        delay_days = None
        if deadline_date:
            delay_days = (today - deadline_date).days

        all_tasks.append(
            {
                "row_index": r_idx,                 # real sheet row index
                "task_id": _norm(task_id),
                "team": team,                       # canonical team
                "team_raw": _norm(team_raw),
                "title": title_clean,
                "type": _norm(ctype),
                "comment": _norm(comment),
                "status": _norm_lower(status),      # "done" / "not yet" / ""
                "done": _is_done(status, done_val), # boolean
                "date_en": _clean_rtl(date_en_raw), # keep original string
                "date_fa": _norm(date_fa),
                "day_fa": _norm(day_name),
                "time": _norm(time_str),
                "deadline_date": deadline_date,     # python date
                "delay_days": delay_days,           # int or None
            }
        )

    # sort by date then title (stable output)
    def _sort_key(t):
        d = t["deadline_date"] or date(2100, 1, 1)
        return (d, t["team"], t["title"])
    all_tasks.sort(key=_sort_key)

    return all_tasks

def _by_team(team: str):
    want = _normalize_team(team)
    tasks = _load_tasks()
    if want == "all":
        return tasks
    return [t for t in tasks if t["team"] == want]

# ----------------------------
# Public APIs used by bot
# ----------------------------

def get_tasks_today(team: str):
    today = datetime.now().date()
    out = []
    for t in _by_team(team):
        if t["deadline_date"] and t["deadline_date"] == today:
            out.append(t)
    return out

def get_tasks_week(team: str):
    today = datetime.now().date()
    week_limit = today + timedelta(days=7)
    out = []
    for t in _by_team(team):
        d = t["deadline_date"]
        if d and today <= d <= week_limit:
            out.append(t)
    return out

def get_tasks_pending(team: str):
    """
    "تسک های انجام نشده":
      هر چیزی که done نباشه و تایتل داشته باشه.
      اگر تاریخ داشت delay_days هم حساب میشه.
    """
    out = []
    for t in _by_team(team):
        if t["done"]:
            continue
        out.append(t)
    return out

# Compatibility for your old scheduler code (if you still use it somewhere)
def get_tasks_for(team: str, mode=None):
    if mode == "week":
        return get_tasks_week(team)
    if mode == "today":
        return get_tasks_today(team)
    if mode == "pending":
        return get_tasks_pending(team)
    return _by_team(team)

def update_task_status(task_id_or_title: str, team_or_new_status=None, new_status: str = "done"):
    """
    Supports:
      - update_task_status(title, team, "done")
      - update_task_status(task_id_or_title, "done")
    Updates column "Status" in Tasks sheet.
    """
    # detect call style
    team = None
    if team_or_new_status is not None:
        t = _norm_lower(team_or_new_status)
        if t in ("done", "not yet", "notyet", "not_yet", "notyet", "yes", "no"):
            # 2-arg style: (title, new_status)
            team = None
            new_status = team_or_new_status
        else:
            # 3-arg style: (title, team, new_status)
            team = team_or_new_status

    ns = _norm_lower(new_status)
    if ns in ("done", "yes"):
        ns = "done"
    elif ns in ("notyet", "not_yet", "not yet", "no"):
        ns = "not yet"
    else:
        # default to done if unknown (safer for your flow)
        ns = "done"

    rows = get_sheet(TASKS_SHEET)
    if not rows or len(rows) < 2:
        return False

    header = rows[0]
    m = _colmap_from_header(header)
    c_status = _get_col(m, "Status", default=9)
    c_team   = _get_col(m, "Team", default=1)
    c_taskid = _get_col(m, "TaskID", default=0)
    c_title  = _get_col(m, "Content Title", "ContentTitle", default=6)

    needle = _norm(task_id_or_title)
    needle_l = needle.strip().lower()

    want_team = _normalize_team(team) if team else None

    # search: 1) by TaskID exact  2) by Title (and team if provided)
    target_row_index = None

    for r_idx, row in enumerate(rows[1:], start=2):
        if not row:
            continue

        rid = _norm(_safe_get(row, c_taskid, ""))
        rteam = _normalize_team(_safe_get(row, c_team, ""))
        rtitle = _norm(_safe_get(row, c_title, ""))

        if rid and rid.strip().lower() == needle_l:
            if want_team and rteam != want_team:
                continue
            target_row_index = r_idx
            break

    if target_row_index is None:
        for r_idx, row in enumerate(rows[1:], start=2):
            if not row:
                continue
            rteam = _normalize_team(_safe_get(row, c_team, ""))
            rtitle = _norm(_safe_get(row, c_title, ""))
            if not rtitle:
                continue
            if rtitle.strip().lower() == needle_l:
                if want_team and rteam != want_team:
                    continue
                target_row_index = r_idx
                break

    if target_row_index is None:
        return False

    # update Status col (1-based for API)
    update_cell(TASKS_SHEET, target_row_index, c_status + 1, ns)
    return True
