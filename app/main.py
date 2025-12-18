# app/main.py
# -*- coding: utf-8 -*-

import os
import pytz
from fastapi import FastAPI, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.handler import process_update
from scheduler.job import run_weekly_jobs, run_daily_jobs, check_reminders
from core.logging import log_error, log_info
from core.sheets import sync_tasks

app = FastAPI()
IRAN_TZ = pytz.timezone("Asia/Tehran")

scheduler = AsyncIOScheduler(timezone=IRAN_TZ)

def _setup_jobs():
    scheduler.add_job(
        run_daily_jobs,
        CronTrigger(hour=8, minute=0),
        id="daily_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )
    scheduler.add_job(
        run_weekly_jobs,
        CronTrigger(day_of_week="sat", hour=9, minute=0),
        id="weekly_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )
    scheduler.add_job(
        check_reminders,
        CronTrigger(hour=10, minute=0),
        id="reminders_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )

@app.on_event("startup")
async def on_startup():
    _setup_jobs()
    if not scheduler.running:
        scheduler.start()
        log_info("Scheduler started ✅")

@app.on_event("shutdown")
async def on_shutdown():
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        pass

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

# --- manual triggers ---
@app.post("/run/daily")
async def run_daily():
    try:
        await run_daily_jobs()
        return {"ok": True, "job": "daily"}
    except Exception as e:
        log_error(f"DAILY JOB ERROR: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/run/weekly")
async def run_weekly():
    try:
        await run_weekly_jobs()
        return {"ok": True, "job": "weekly"}
    except Exception as e:
        log_error(f"WEEKLY JOB ERROR: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/run/reminders")
async def run_reminders():
    try:
        await check_reminders()
        return {"ok": True, "job": "reminders"}
    except Exception as e:
        log_error(f"REMINDERS JOB ERROR: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/sync_tasks")
async def sync_tasks_endpoint():
    try:
        ok = await sync_tasks()
        return {"ok": bool(ok)}
    except Exception as e:
        log_error(f"SYNC ERROR: {e}")
        return {"ok": False, "error": str(e)}
