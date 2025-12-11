# app/core/members.py

from core.sheets import get_sheet, append_row

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

        # تبدیل به متن برای جلوگیری از mismatch
        row_chat_id = str(row[0]).strip()
        chat_id_str = str(chat_id).strip()

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
        "",        # team
        "",        # customname
        "No"       # welcomed
    ]

    append_row("members", row)


# ----------------------------------------------------
# تغییر welcomed به Yes
# ----------------------------------------------------
def mark_welcomed(chat_id):
    rows = get_sheet("members")

    if not rows or len(rows) < 2:
        return

    header = rows[0]
    table = rows[1:]

    updated = False
    new_rows = [header]

    for row in table:
        if not row:
            continue

        row_chat_id = str(row[0]).strip()
        chat_id_str = str(chat_id).strip()

        if row_chat_id == chat_id_str:
            row[5] = "Yes"
            updated = True

        new_rows.append(row)

    if updated:
        # بازنویسی کامل شیت
        from core.sheets import overwrite_sheet
        overwrite_sheet("members", new_rows)
