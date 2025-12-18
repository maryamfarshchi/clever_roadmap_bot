# app/bot/helpers.py
# -*- coding: utf-8 -*-

import os
import aiohttp
from core.logging import log_error

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def send_message(chat_id, text):
    if not BOT_TOKEN:
        log_error("BOT_TOKEN not set in environment")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_error(f"Send message failed: {error_text}")
                    return False
                return True
    except Exception as e:
        log_error(f"Send message ERROR: {e}")
        return False

async def send_buttons(chat_id, text, buttons):
    if not BOT_TOKEN:
        log_error("BOT_TOKEN not set in environment")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": buttons}
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_error(f"Send buttons failed: {error_text}")
                    return False
                return True
    except Exception as e:
        log_error(f"Send buttons ERROR: {e}")
        return False
