# app/core/members.py

from core.sheets import get_sheet, append_row


# ----------------------------------------------------
#  خواندن کاربر از شیت members
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
#  ثبت کاربر جدید (نسخه پایه)
# ----------------------------------------------------
def add_member(chat_id, name, username):
    row = [
        str(chat_id),
        name if name else "",
        username if username else "",
        "",          # team (خالی)
        "",          # customname
        "No"         # welcomed
    ]

    append_row("members", row)



# ----------------------------------------------------
#  ثبت کاربر جدید فقط اگر در شیت وجود نداشته باشد
#  (تابع مورد نیاز handler.py)
# ----------------------------------------------------
def add_member_if_not_exists(chat_id, name="", username=""):
    user = find_member(chat_id)

    # اگر قبلاً وجود دارد همان را برگردان
    if user:
        return user

    # اگر وجود ندارد → اضافه کن
    row = [
        str(chat_id),
        name if name else "",
        username if username else "",
        "",        # team = تعیین نشده
        name,      # customname موقت = name
        "No"       # welcomed
    ]

    append_row("members", row)

    return {
        "chat_id": str(chat_id),
        "name": name,
        "username": username,
        "team": "",
        "customname": name,
        "welcomed": "No",
    }
