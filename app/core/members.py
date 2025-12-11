# app/core/members.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet, append_row, update_cell


def _normalize(s):
    return str(s or "").strip().lower()


# ----------------------------------------------------
# پیدا کردن کاربر در شیت members
# ----------------------------------------------------
def find_member(chat_id):
    rows = get_sheet("members")

    if not rows or len(rows) < 2:
        return None

    body = rows[1:]
    chat_id_str = str(chat_id).strip()

    for row in body:
        if not row:
            continue

        row_chat_id = str(row[0]).strip()
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


# ----------------------------------------------------
# اگر کاربر نبود، ثبت کن
# ----------------------------------------------------
def add_member_if_not_exists(chat_id, name, username):
    user = find_member(chat_id)
    if user:
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


# ----------------------------------------------------
# تغییر welcomed به Yes (فقط همان سلول)
# ----------------------------------------------------
def mark_welcomed(chat_id):
    rows = get_sheet("members")
    if not rows or len(rows) < 2:
        return

    body = rows[1:]
    chat_str = str(chat_id).strip()

    for idx, row in enumerate(body):
        if not row:
            continue
        if str(row[0]).strip() == chat_str:
            # ردیف واقعی در شیت (با احتساب هدر)
            row_index = idx + 2
            # ستون welcomed = ستون ششم = F = index=6
            col_index = 6
            update_cell("members", row_index, col_index, "Yes")
            break


# ----------------------------------------------------
# گرفتن همه اعضای یک تیم مشخص
# ----------------------------------------------------
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
