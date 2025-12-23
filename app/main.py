# app/main.py
# -*- coding: utf-8 -*-

import os
import sys
from fastapi import FastAPI, Request, Header, HTTPException

APP_DIR = os.path.dirname(__file__)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from bot.handler import process_update
from scheduler.job import run_weekly_jobs, run_daily_jobs, check_reminders
from core.logging import log_error
from core.sheets import sync_tasks, invalidate

app = FastAPI()

TRIGGER_TOKEN = os.getenv("TRIGGER_TOKEN", "").strip()

def verify_trigger_token(x_trigger_token: str | None):
    # اگر TRIGGER_TOKEN ست نشده بود، چک رو رد می‌کنیم (برای توسعه)
    if TRIGGER_TOKEN and (x_trigger_token or "").strip() != TRIGGER_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/ping")
async def ping():
    return "OK"

@app.get("/")
async def root():
    return {"ok": True, "service": "clever-roadmap-bot"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
        await process_update(update)
        return {"ok": True}
    except Exception as e:
        log_error(f"Webhook ERROR: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/sync_tasks")
async def sync_tasks_endpoint(request: Request):
    body = await request.json() if request else {}
    body = body or {}
    from_google = bool(body.get("from_google", False))

    try:
        if not from_google:
            await sync_tasks()
        else:
            # وقتی خود Google خبر میده که sync شده
            invalidate("Tasks")
            invalidate("members")

        # بعد از هر sync یکبار reminders چک می‌کنیم
        await check_reminders()
        return {"ok": True}
    except Exception as e:
        log_error(f"SYNC ERROR: {e}")
        return {"ok": False, "error": str(e)}

# ---- کرون‌ها: GET/POST هر دو، چون بعضی سرویس‌ها test run رو GET میزنن ----
@app.api_route("/run/daily", methods=["GET", "POST"])
async def run_daily(x_trigger_token: str | None = Header(None)):
    verify_trigger_token(x_trigger_token)
    try:
        await run_daily_jobs()
        return {"ok": True, "job": "daily"}
    except Exception as e:
        log_error(f"DAILY JOB ERROR: {e}")
        return {"ok": False, "error": str(e)}

@app.api_route("/run/weekly", methods=["GET", "POST"])
async def run_weekly(x_trigger_token: str | None = Header(None)):
    verify_trigger_token(x_trigger_token)
    try:
        await run_weekly_jobs()
        return {"ok": True, "job": "weekly"}
    except Exception as e:
        log_error(f"WEEKLY JOB ERROR: {e}")
        return {"ok": False, "error": str(e)}

@app.api_route("/run/reminders", methods=["GET", "POST"])
async def run_reminders(x_trigger_token: str | None = Header(None)):
    verify_trigger_token(x_trigger_token)
    try:
        await check_reminders()
        return {"ok": True, "job": "reminders"}
    except Exception as e:
        log_error(f"REMINDERS JOB ERROR: {e}")
        return {"ok": False, "error": str(e)}
