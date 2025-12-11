from core.sheets import get_sheet

def find_member(chat_id):
    # Read sheet safely
    rows = get_sheet("members")

    # If sheet empty or no header
    if not rows or len(rows) < 2:
        return None

    # Extract header + rows
    header = rows[0]
    table = rows[1:]

    for row in table:
        if not row or len(row) < 1:
            continue

        row_chat_id = str(row[0]).strip()
        if row_chat_id == str(chat_id).strip():
            # Build safe dictionary even if columns are missing
            return {
                "chat_id": row_chat_id,
                "name": row[1].strip() if len(row) > 1 and row[1] else "",
                "username": row[2].strip() if len(row) > 2 and row[2] else "",
                "team": row[3].strip() if len(row) > 3 and row[3] else "",
                "customname": row[4].strip() if len(row) > 4 and row[4] else "",
                "welcomed": row[5].strip() if len(row) > 5 and row[5] else ""
            }

    return None
