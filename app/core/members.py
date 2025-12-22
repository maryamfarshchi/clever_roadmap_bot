# app/core/members.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet, append_row, update_cell, invalidate

MEMBERS_SHEET = "members"

def clean(s):
    return str(s or "").strip()

def normalize_team(s: str) -> str:
    return clean(s).lower().replace("ai production", "aiproduction").replace(" ", "")

async def find_member(chat_id):
    rows = await get_sheet(MEMBERS_SHEET)
    if not rows or len(rows) < 2:
        return None

    cid = str(chat_id).strip()

    for i, row in enumerate(rows[1:], start=2):
        row_cid = clean(row[0]) if len(row) > 0 else ""
        if row_cid == cid:
            return {
                "row": i,
                "chat_id": row_cid,
                "name": clean(row[1]) if len(row) > 1 else "",
                "username": clean(row[2]) if len(row) > 2 else "",
                "team": clean(row[3]) if len(row) > 3 else "",
                "customname": clean(row[4]) if len(row) > 4 else "",
                "welcomed": (clean(row[5]).lower() == "yes") if len(row) > 5 else False
            }
    return None

async def save_or_add_member(chat_id, name=None, username=None, team=None):
    member = await find_member(chat_id)
    if member:
        # update basic fields if provided
        if name is not None and not member.get("name"):
            await update_cell(MEMBERS_SHEET, member["row"], 2, name)  # name col=2
        if username is not None and not member.get("username"):
            await update_cell(MEMBERS_SHEET, member["row"], 3, username)  # username col=3

        if team:
            ok = await update_cell(MEMBERS_SHEET, member["row"], 4, team)  # team col=4
            if ok:
                invalidate(MEMBERS_SHEET)
        return await find_member(chat_id)

    new_row = [chat_id, name or "", username or "", team or "", "", "No"]
    ok = await append_row(MEMBERS_SHEET, new_row)
    if ok:
        invalidate(MEMBERS_SHEET)
    return await find_member(chat_id)

async def set_member_welcomed(chat_id):
    member = await find_member(chat_id)
    if not member:
        return False
    ok = await update_cell(MEMBERS_SHEET, member["row"], 6, "YES")  # welcomed col=6
    if ok:
        invalidate(MEMBERS_SHEET)
    return ok

async def get_members_by_team(team: str):
    rows = await get_sheet(MEMBERS_SHEET)
    if not rows or len(rows) < 2:
        return []

    t = normalize_team(team)
    out = []
    for row in rows[1:]:
        row_team = normalize_team(row[3]) if len(row) > 3 else ""
        if row_team == t:
            out.append({
                "chat_id": clean(row[0]) if len(row) > 0 else "",
                "name": clean(row[1]) if len(row) > 1 else "",
                "username": clean(row[2]) if len(row) > 2 else "",
                "team": clean(row[3]) if len(row) > 3 else "",
                "customname": clean(row[4]) if len(row) > 4 else "",
            })
    return out
