# app/main.py
# -*- coding: utf-8 -*-

import os
import sys
import pytz

from fastapi import FastAPI, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

APP_DIR = os.path.dirname(__file__)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from bot.handler import process_update
from scheduler.job import run_weekly_jobs, run_daily_jobs, check_reminders
from core.logging import log_error, log_info
from core.sheets import sync_tasks, invalidate

app = FastAPI()
IRAN_TZ = pytz.timezone("Asia/Tehran")
scheduler = AsyncIOScheduler(timezone=IRAN_TZ)

@app.get("/ping")
async def ping():
    return "OK"

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except:
        return default

def setup_jobs():
    # قابل تنظیم با env
    daily_hour = _env_int("DAILY_HOUR", 8)
    daily_min  = _env_int("DAILY_MINUTE", 0)

    weekly_hour = _env_int("WEEKLY_HOUR", 9)
    weekly_min  = _env_int("WEEKLY_MINUTE", 0)

    # Daily summary
    scheduler.add_job(
        run_daily_jobs,
        CronTrigger(hour=daily_hour, minute=daily_min),
        id="daily_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
    )

    # Weekly summary (Saturday)
    scheduler.add_job(
        run_weekly_jobs,
        CronTrigger(day_of_week="sat", hour=weekly_hour, minute=weekly_min),
        id="weekly_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
    )

    # Reminders: هر 10 دقیقه (برای فهمیدن تغییرات بعد از صبح)
    scheduler.add_job(
        check_reminders,
        CronTrigger(minute="*/10"),
        id="reminders_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
    )

@app.on_event("startup")
async def on_startup():
    setup_jobs()
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

@app.post("/sync_tasks")
async def sync_tasks_endpoint(request: Request):
    body = await request.json() or {}
    from_google = body.get("from_google", False)
    try:
        if not from_google:
            ok = await sync_tasks()
        else:
            invalidate("Tasks")
            invalidate("members")
        # بعد sync همون لحظه ریمایندرها رو هم چک کن
        await check_reminders()
        return {"ok": True}
    except Exception as e:
        log_error(f"SYNC ERROR: {e}")
        return {"ok": False, "error": str(e)}

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
