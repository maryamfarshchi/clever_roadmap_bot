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


async def _safe_json(resp: aiohttp.ClientResponse):
    try:
        return await resp.json()
    except Exception:
        try:
            txt = await resp.text()
            return {"ok": False, "error": txt}
        except Exception:
            return {"ok": False, "error": "non-json response"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def get_sheet(sheet: str):
    k = _key(sheet)
    if k in cache:
        return cache[k]

    if not API:
        log_error("GOOGLE_API_URL not set")
        return []

    url = f"{API}?sheet={sheet}"
    try:
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as r:
                data = await _safe_json(r)
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
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                API,
                json={"action": "update_cell", "sheet": sheet, "row": row, "col": col, "value": value},
            ) as r:
                data = await _safe_json(r)
                ok = bool(data.get("ok"))
                if ok:
                    invalidate(sheet)
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
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                API,
                json={"action": "append_row", "sheet": sheet, "row": row_data},
            ) as r:
                data = await _safe_json(r)
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
        timeout = aiohttp.ClientTimeout(total=40)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(API, json={"action": "sync_tasks"}) as r:
                data = await _safe_json(r)
                ok = bool(data.get("ok"))
                if ok:
                    invalidate("Tasks")
                return ok
    except Exception as e:
        log_error(f"sync_tasks ERROR: {e}")
        return False
