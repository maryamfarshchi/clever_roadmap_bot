# app/core/members.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet, append_row, update_cell

def _normalize(s):
    return str(s or "").strip()

def find_member(chat_id):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return None

    chat_id_str = _normalize(chat_id)
    for row in rows[1:]:
        if len(row) == 0:
            continue
        row_chat_id = _normalize(row[0])  # ستون chatid
        if row_chat_id == chat_id_str:
            team = _normalize(row[3]) if len(row) > 3 else "Digital"
            return {
                "chat_id": row_chat_id,
                "name": _normalize(row[1]) if len(row) > 1 else "",
                "username": _normalize(row[2]) if len(row) > 2 else "",
                "team": team,
                "customname": _normalize(row[4]) if len(row) > 4 else "",
                "welcomed": _normalize(row[5]) if len(row) > 5 else "",
            }
    return None

def add_member_if_not_exists(chat_id, name, username):
    if find_member(chat_id):
        return

    row = [
        str(chat_id).strip(),
        name or "",
        username or "",
        "Digital",  # تیم پیش‌فرض
        "",
        "No",
    ]

    append_row("members", row)

def mark_welcomed(chat_id):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return

    chat_str = str(chat_id).strip()
    for idx, row in enumerate(rows[1:]):
        if len(row) > 0 and _normalize(row[0]) == chat_str:
            row_index = idx + 2
            update_cell("members", row_index, 6, "Yes")
            break

def get_members_by_team(team):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return []

    team_norm = _normalize(team)
    members = []

    for row in rows[1:]:
        if len(row) < 4:
            continue

        row_team = _normalize(row[3])
        if row_team != team_norm:
            continue

        chat_id_raw = str(row[0]).strip()
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            chat_id = chat_id_raw

        members.append({
            "chat_id": chat_id,
            "name": _normalize(row[1]),
            "username": _normalize(row[2]),
            "team": row_team,
            "customname": _normalize(row[4]) if len(row) > 4 else "",
            "welcomed": _normalize(row[5]) if len(row) > 5 else "",
        })

    return members
