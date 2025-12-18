# app/core/sheets.py
# -*- coding: utf-8 -*-

import os
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache
from core.config import CACHE_TTL
from core.logging import log_error

API = os.getenv("GOOGLE_API_URL", "").rstrip("/")
cache = TTLCache(maxsize=50, ttl=CACHE_TTL)

def _key(sheet: str) -> str:
    return f"sheet::{sheet}"

def _invalidate(sheet: str):
    k = _key(sheet)
    if k in cache:
        del cache[k]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def get_sheet(sheet: str):
    k = _key(sheet)
    if k in cache:
        return cache[k]

    if not API:
        log_error("GOOGLE_API_URL not set")
        return []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API}?sheet={sheet}", timeout=20) as response:
                data = await response.json()
                rows = data.get("rows", [])
                if not isinstance(rows, list):
                    log_error(f"Sheet bad response: {data}")
                    return []
                cache[k] = rows
                return rows
    except Exception as e:
        log_error(f"get_sheet ERROR: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def update_cell(sheet: str, row: int, col: int, value):
    if not API:
        log_error("GOOGLE_API_URL not set")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API}?sheet={sheet}&row={row}&col={col}",
                json={"value": value},
                timeout=20
            ) as response:
                data = await response.json()
                ok = "error" not in data
                if ok:
                    _invalidate(sheet)
                return ok
    except Exception as e:
        log_error(f"update_cell ERROR: {e}")
        return False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def append_row(sheet: str, row_data: list):
    if not API:
        log_error("GOOGLE_API_URL not set")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API}?sheet={sheet}",
                json={"row": row_data},
                timeout=20
            ) as response:
                data = await response.json()
                ok = "error" not in data
                if ok:
                    _invalidate(sheet)
                return ok
    except Exception as e:
        log_error(f"append_row ERROR: {e}")
        return False
