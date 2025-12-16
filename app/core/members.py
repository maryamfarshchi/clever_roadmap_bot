# app/core/members.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet, append_row, update_cell

def _normalize(s):
    return str(s or "").strip().lower()

# پیدا کردن عضو (اصلاح‌شده برای پیدا کردن درست chat_id)
def find_member(chat_id):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return None

    chat_id_str = str(chat_id).strip()  # همیشه str کن
    for row in rows[1:]:
        if len(row) < 1:
            continue
        row_chat_id = str(row[0]).strip()
        if row_chat_id == chat_id_str:
            team = row[3].strip() if len(row) > 3 else ""
            if not team:  # اگر تیم خالی بود، fallback
                team = "Digital"  # یا تیم پیش‌فرض، بعداً تغییر بده
            return {
                "chat_id": row_chat_id,
                "name": row[1].strip() if len(row) > 1 else "",
                "username": row[2].strip() if len(row) > 2 else "",
                "team": team,
                "customname": row[4].strip() if len(row) > 4 else "",
                "welcomed": row[5].strip() if len(row) > 5 else "",
            }
    return None

# ثبت کاربر جدید
def add_member_if_not_exists(chat_id, name, username):
    if find_member(chat_id):
        return

    row = [
        str(chat_id),
        name or "",
        username or "",
        "",   # team
        "",   # customname
        "No", # welcomed
    ]

    append_row("members", row)

# علامت‌گذاری welcomed
def mark_welcomed(chat_id):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return

    chat_str = str(chat_id).strip()
    for idx, row in enumerate(rows[1:]):
        if len(row) > 0 and str(row[0]).strip() == chat_str:
            row_index = idx + 2
            update_cell("members", row_index, 6, "Yes")
            break

# گرفتن اعضای تیم
def get_members_by_team(team):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return []

    team_norm = _normalize(team)
    members = []

    for row in rows[1:]:
        if len(row) < 4:
            continue

        row_team = row[3]
        if _normalize(row_team) != team_norm:
            continue

        chat_id_raw = str(row[0]).strip()
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            chat_id = chat_id_raw

        members.append({
            "chat_id": chat_id,
            "name": row[1] if len(row) > 1 else "",
            "username": row[2] if len(row) > 2 else "",
            "team": row_team,
            "customname": row[4] if len(row) > 4 else "",
            "welcomed": row[5] if len(row) > 5 else "",
        })

    return members
