# app/bot/helpers.py
# -*- coding: utf-8 -*-

import os
import aiohttp
from core.logging import log_error

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def _post(method: str, payload: dict):
    if not BOT_TOKEN:
        log_error("BOT_TOKEN not set")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=20) as r:
                if r.status != 200:
                    log_error(f"{method} failed: {await r.text()}")
                    return False
                return True
    except Exception as e:
        log_error(f"{method} ERROR: {e}")
        return False

async def send_message(chat_id, text):
    return await _post("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    })

async def send_buttons(chat_id, text, buttons):
    return await _post("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": buttons}
    })

async def send_reply_keyboard(chat_id, text, keyboard_rows):
    return await _post("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "keyboard": keyboard_rows,
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
    })
