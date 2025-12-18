# app/core/messages.py
# -*- coding: utf-8 -*-

from core.sheets import get_sheet
from core.logging import log_error
import random

MESSAGES_SHEET = "Messages"

def load_messages():
    rows = get_sheet(MESSAGES_SHEET)
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
    all_msgs = load_messages()
    filtered = [m for m in all_msgs if m["type"] == msg_type]
    if not filtered:
        log_error(f"No messages for type {msg_type}")
        return "—"
    chosen = random.choice(filtered)["text"]
    for key, val in kwargs.items():
        chosen = chosen.replace(f"{{{key}}}", str(val))
    return chosen

def get_welcome_message(name):
    return get_random_message("welcome", name=name)  # type "welcome" در شیت داشته باش
