# app/core/sheets.py
# -*- coding: utf-8 -*-

import os
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache

from core.config import CACHE_TTL
from core.logging import log_error

API = os.getenv("GOOGLE_API_URL", "").rstrip("/")
cache = TTLCache(maxsize=200, ttl=CACHE_TTL)

def _key(sheet: str) -> str:
    return f"sheet::{sheet}"

def invalidate(sheet: str):
    k = _key(sheet)
    if k in cache:
        del cache[k]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def get_sheet(sheet: str):
    k = _key(sheet)
    if k in cache:
        return cache[k]

    if not API:
        log_error("GOOGLE_API_URL not set")
        return []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API}?sheet={sheet}", timeout=20) as r:
                data = await r.json()
                rows = data.get("rows", [])
                if not isinstance(rows, list):
                    log_error(f"Bad sheet response: {data}")
                    return []
                cache[k] = rows
                return rows
    except Exception as e:
        log_error(f"get_sheet ERROR: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def update_cell(sheet: str, row: int, col: int, value):
    if not API:
        log_error("GOOGLE_API_URL not set")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API}",
                json={"action": "update_cell", "sheet": sheet, "row": row, "col": col, "value": value},
                timeout=20
            ) as r:
                data = await r.json()
                ok = bool(data.get("ok"))
                if ok:
                    invalidate(sheet)  # جدید: بعد آپدیت، کش رو invalidate کن
                return ok
    except Exception as e:
        log_error(f"update_cell ERROR: {e}")
        return False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def append_row(sheet: str, row_data: list):
    if not API:
        log_error("GOOGLE_API_URL not set")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API}",
                json={"action": "append_row", "sheet": sheet, "row": row_data},
                timeout=20
            ) as r:
                data = await r.json()
                ok = bool(data.get("ok"))
                if ok:
                    invalidate(sheet)
                return ok
    except Exception as e:
        log_error(f"append_row ERROR: {e}")
        return False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def sync_tasks():
    if not API:
        log_error("GOOGLE_API_URL not set")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API, json={"action": "sync_tasks"}, timeout=30) as r:
                data = await r.json()
                ok = bool(data.get("ok"))
                if ok:
                    invalidate("Tasks")
                return ok
    except Exception as e:
        log_error(f"sync_tasks ERROR: {e}")
        return False
