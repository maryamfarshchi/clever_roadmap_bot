# app/core/members.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet, append_row, update_cell

def _normalize(s):
    return str(s or "").strip().lower()

# پیدا کردن کاربر در شیت members
def find_member(chat_id):
    rows = get_sheet("members")

    if not rows or len(rows) < 2:
        return None

    body = rows[1:]
    chat_id_str = str(chat_id).strip()  # همیشه str

    for row in body:
        if not row:
            continue

        row_chat_id = str(row[0]).strip() if len(row) > 0 else ""
        if row_chat_id == chat_id_str:
            return {
                "chat_id": row_chat_id,
                "name": row[1] if len(row) > 1 else "",
                "username": row[2] if len(row) > 2 else "",
                "team": row[3] if len(row) > 3 else "",
                "customname": row[4] if len(row) > 4 else "",
                "welcomed": row[5] if len(row) > 5 else "",
            }
    return None

def get_members_by_team(team):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return []

    body = rows[1:]
    team_norm = _normalize(team)
    members = []

    for row in body:
        if not row or len(row) < 4:
            continue

        row_team = row[3]
        if _normalize(row_team) != team_norm:
            continue

        chat_id_raw = str(row[0]).strip()
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            chat_id = chat_id_raw

        members.append(
            {
                "chat_id": chat_id,
                "name": row[1] if len(row) > 1 else "",
                "username": row[2] if len(row) > 2 else "",
                "team": row_team,
                "customname": row[4] if len(row) > 4 else "",
                "welcomed": row[5] if len(row) > 5 else "",
            }
        )

    return members
