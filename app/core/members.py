from core.sheets import get_sheet

def find_member(chat_id):
    rows = get_sheet("members")
    header = rows[0]
    table = rows[1:]
    for row in table:
        if str(row[0]) == str(chat_id):
            return {
                "chat_id": row[0],
                "name": row[1],
                "username": row[2],
                "team": row[3],
                "customname": row[4]
            }
    return None
