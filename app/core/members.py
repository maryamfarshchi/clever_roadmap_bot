# app/core/members.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet, append_row, update_cell
from core.logging import log_error

MEMBERS_SHEET = "members"

def clean(s):
    return str(s or "").strip()

def _normalize(s):
    return clean(s).lower()

def find_member(chat_id):
    rows = get_sheet(MEMBERS_SHEET)
    if not rows or len(rows) < 2:
        return None

    chat_id_str = str(chat_id).strip()

    for i, row in enumerate(rows[1:], start=2):
        row_chat_id = clean(row[0])
        if row_chat_id == chat_id_str:
            return {
                "row": i,
                "chat_id": row_chat_id,
                "name": clean(row[1]),
                "username": clean(row[2]),
                "team": clean(row[3]),
                "customname": clean(row[4]),
                "welcomed": clean(row[5]) == "Yes"
            }
    return None

def save_or_add_member(chat_id, name=None, username=None, team=None):
    member = find_member(chat_id)
    if member:
        if team:
            update_cell(MEMBERS_SHEET, member["row"], 4, team)  # update team
        return member
    else:
        new_row = [chat_id, name, username, team or '', '', 'No']
        append_row(MEMBERS_SHEET, new_row)
        return find_member(chat_id)  # reload to get row

# Alias for compatibility (if original was add_member_if_not_exists)
add_member_if_not_exists = save_or_add_member

def get_members_by_team(team):
    rows = get_sheet(MEMBERS_SHEET)
    team_norm = _normalize(team)
    members = []
    for row in rows[1:]:
        row_team = _normalize(row[3])
        if row_team == team_norm:
            members.append({
                "chat_id": clean(row[0]),
                "name": clean(row[1]),
                "username": clean(row[2]),
                "team": row[3],
                "customname": clean(row[4]),
                "welcomed": clean(row[5]) == "Yes"
            })
    return members
