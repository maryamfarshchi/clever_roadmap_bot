# app/core/messages.py
# -*- coding: utf-8 -*-

import random
from core.sheets import get_sheet
from core.logging import log_error

MESSAGES_SHEET = "Messages"

async def load_messages():
    rows = await get_sheet(MESSAGES_SHEET)
    if not rows or len(rows) < 2:
        return []
    body = rows[1:]
    messages = []
    for row in body:
        msg_type = (row[0] if len(row) > 0 else "")
        msg_text = (row[1] if len(row) > 1 else "")
        if msg_type and msg_text:
            messages.append({"type": str(msg_type).strip(), "text": str(msg_text)})
    return messages

async def get_random_message(msg_type, **kwargs):
    all_msgs = await load_messages()
    filtered = [m for m in all_msgs if m["type"] == msg_type]
    if not filtered:
        log_error(f"No messages for type {msg_type}")
        return "—"
    chosen = random.choice(filtered)["text"]
    for k, v in kwargs.items():
        chosen = chosen.replace(f"{{{k}}}", str(v))
    return chosen

async def get_welcome_message(name):
    return await get_random_message("welcome", name=name)
