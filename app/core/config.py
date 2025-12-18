# app/core/config.py
# -*- coding: utf-8 -*-

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_URL = os.getenv("GOOGLE_API_URL").rstrip("/") if os.getenv("GOOGLE_API_URL") else ""
CACHE_TTL = 300  # زمان انقضای کش در ثانیه
