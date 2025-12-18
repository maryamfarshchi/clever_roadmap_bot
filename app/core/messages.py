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
    out = []
    for row in body:
        t = str(row[0]).strip() if len(row) > 0 else ""
        txt = str(row[1]) if len(row) > 1 else ""
        if t and txt:
            out.append({"type": t, "text": txt})
    return out

async def get_random_message(msg_type, **kwargs):
    msgs = await load_messages()
    pool = [m for m in msgs if m["type"] == msg_type]
    if not pool:
        log_error(f"No messages for type {msg_type}")
        return "—"
    text = random.choice(pool)["text"]
    for k, v in kwargs.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text

async def get_welcome_message(name):
    return await get_random_message("welcome", name=name)
