# app/core/sheets.py
# -*- coding: utf-8 -*-

import os
import aiohttp  # برای async
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache
from core.config import CACHE_TTL
from core.logging import log_error, log_info

API = os.getenv("GOOGLE_API_URL", "").rstrip("/")
cache = TTLCache(maxsize=10, ttl=CACHE_TTL)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def get_sheet(sheet):
    key = f"sheet_{sheet}"
    if key in cache:
        return cache[key]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API}?sheet={sheet}", timeout=10) as response:
                data = await response.json()
                if "error" in data or "rows" not in data:
                    log_error(f"Sheet Error: {data}")
                    return []
                cache[key] = data["rows"]
                return data["rows"]
    except Exception as e:
        log_error(f"get_sheet ERROR: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def update_cell(sheet, row, col, value):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API}?sheet={sheet}&row={row}&col={col}", json={"value": value}, timeout=10) as response:
                data = await response.json()
                return "error" not in data
    except Exception as e:
        log_error(f"update_cell ERROR: {e}")
        return False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def append_row(sheet, row_data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API}?sheet={sheet}", json={"row": row_data}, timeout=10) as response:
                data = await response.json()
                return "error" not in data
    except Exception as e:
        log_error(f"append_row ERROR: {e}")
        return False
