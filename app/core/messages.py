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
        msg_type = row[0]
        msg_text = row[1]

        if msg_type and msg_text:
            messages.append({
                "type": msg_type,
                "text": msg_text
            })

    return messages


def get_random_message(msg_type, **kwargs):
    """
    msg_type = WEEK / PRE2 / DUE / OVR / ESC
    """
    all_msgs = load_messages()

    filtered = [m for m in all_msgs if m["type"] == msg_type]
    if not filtered:
        return "—"

    chosen = random.choice(filtered)["text"]

    # جایگزینی متغیرهای پویا در متن
    for key, val in kwargs.items():
        chosen = chosen.replace(f"{{{key}}}", str(val))

    return chosen
