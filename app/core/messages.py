# app/core/messages.py
from core.sheets import get_sheet
import random

def load_messages():
    rows = get_sheet("Messages")
    if not rows:
        return []

    header = rows[0]
    body = rows[1:]

    messages = []
    for row in body:
        if len(row) < 2:
            continue

        msg_type = row[0]
        msg_text = row[1]

        if msg_type and msg_text:
            messages.append({"type": msg_type, "text": msg_text})

    return messages


def get_random_message(msg_type, **kwargs):
    all_msgs = load_messages()
    filtered = [m for m in all_msgs if m["type"] == msg_type]

    if not filtered:
        return f"[پیام یافت نشد: {msg_type}]"

    chosen = random.choice(filtered)["text"]

    # جایگذاری متغیرها
    for key, val in kwargs.items():
        chosen = chosen.replace(f"{{{key}}}", str(val))

    return chosen
