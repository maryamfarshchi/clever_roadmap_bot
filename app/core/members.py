# app/core/members.py

from core.sheets import get_sheet, append_row, update_cell


# ----------------------------------------------------
# پیدا کردن کاربر در شیت members
# ----------------------------------------------------
def find_member(chat_id):
    rows = get_sheet("members")

    if not rows or len(rows) < 2:
        return None

    header = rows[0]
    table = rows[1:]

    for row in table:
        if not row:
            continue

        row_chat_id = str(row[0]).strip()

        if row_chat_id == str(chat_id).strip():
            return {
                "chat_id": row_chat_id,
                "name": row[1].strip() if len(row) > 1 and row[1] else "",
                "username": row[2].strip() if len(row) > 2 and row[2] else "",
                "team": row[3].strip() if len(row) > 3 and row[3] else "",
                "customname": row[4].strip() if len(row) > 4 and row[4] else "",
                "welcomed": row[5].strip() if len(row) > 5 and row[5] else "",
            }

    return None



# ----------------------------------------------------
# ثبت کاربر جدید در members اگر وجود نداشت
# ----------------------------------------------------
def add_member_if_not_exists(chat_id, name, username):
    user = find_member(chat_id)
    if user:
        return

    row = [
        str(chat_id),
        name if name else "",
        username if username else "",
        "",      # team
        "",      # customname
        "No"     # welcomed
    ]

    append_row("members", row)



# ----------------------------------------------------
# ست کردن welcomed = Yes فقط یکبار
# ----------------------------------------------------
def mark_welcomed(chat_id):
    rows = get_sheet("members")

    if not rows or len(rows) < 2:
        return

    header = rows[0]
    table = rows[1:]

    for idx, row in enumerate(table, start=1):
        if not row:
            continue

        if str(row[0]).strip() == str(chat_id):
            # ستون welcomed ستون 6 است → Index = 5
            update_cell("members", idx, 5, "Yes")
            return
