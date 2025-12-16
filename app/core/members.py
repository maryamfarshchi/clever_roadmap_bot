# app/core/members.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet, append_row

def find_member(chat_id):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return None

    chat_id_str = str(chat_id).strip()
    for row in rows[1:]:
        if not row:
            continue
        row_chat_id = str(row[0]).strip() if len(row) > 0 else ""
        if row_chat_id == chat_id_str:
            return {
                "chat_id": row_chat_id,
                "name": row[1] if len(row) > 1 else "",
                "username": row[2] if len(row) > 2 else "",
                "team": row[3] if len(row) > 3 else "Digital",  # پیشفرض
                "customname": row[4] if len(row) > 4 else "",
                "welcomed": row[5] if len(row) > 5 else "Yes",
            }
    return None

def add_member_if_not_exists(chat_id, name, username):
    if find_member(chat_id):
        return  # قبلاً وجود داره
    row = [
        str(chat_id).strip(),
        name or "کاربر",
        username or "",
        "Digital",  # پیشفرض تیم Digital
        name or "",
        "Yes"
    ]
    append_row("members", row)

def get_members_by_team(team):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return []

    team_lower = team.lower()
    members = []
    for row in rows[1:]:
        if not row or len(row) < 4:
            continue
        row_team = str(row[3]).strip().lower()
        if row_team != team_lower:
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
            "team": row[3] if len(row) > 3 else "Digital",
            "customname": row[4] if len(row) > 4 else "",
            "welcomed": row[5] if len(row) > 5 else "Yes",
        })

    return members
