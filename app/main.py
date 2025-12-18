# app/main.py
# -*- coding: utf-8 -*-

import sys
import os
import pytz
from fastapi import FastAPI, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# برای importهای داخلی پروژه
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from bot.handler import process_update
from scheduler.job import (
    run_daily_jobs,
    run_weekly_jobs,
    check_reminders
)
from core.logging import log_error, log_info

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI()

# --------------------------------------------------
# Timezone
# --------------------------------------------------
IRAN_TZ = pytz.timezone("Asia/Tehran")

# --------------------------------------------------
# Scheduler (APS)
# --------------------------------------------------
scheduler = AsyncIOScheduler(timezone=IRAN_TZ)

# هر روز ساعت 08:00 صبح → تسک‌های امروز
scheduler.add_job(
    run_daily_jobs,
    CronTrigger(hour=8, minute=0),
    id="daily_jobs",
    replace_existing=True
)

# شنبه هر هفته ساعت 09:00 صبح → تسک‌های هفته
scheduler.add_job(
    run_weekly_jobs,
    CronTrigger(day_of_week="sat", hour=9, minute=0),
    id="weekly_jobs",
    replace_existing=True
)

# هر روز ساعت 10:00 → ریمایندرها (۲ روز مونده، ددلاین، تاخیر، هشدار مدیر)
scheduler.add_job(
    check_reminders,
    CronTrigger(hour=10, minute=0),
    id="reminders",
    replace_existing=True
)

# مهم: جلوگیری از start شدن چندباره روی Render
if not scheduler.running:
    scheduler.start()
    log_info("Scheduler started successfully")

# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
async def root():
    return {"ok": True, "service": "clever-roadmap-bot"}

@app.post("/webhook")
async def webhook(request: Request):
    """
    Telegram webhook endpoint
    """
    try:
        update = await request.json()
        await process_update(update)
        return {"ok": True}
    except Exception as e:
        log_error(f"Webhook ERROR: {e}")
        return {"ok": False, "error": str(e)}

# --------------------------------------------------
# Manual trigger endpoints (for debug / admin)
# --------------------------------------------------

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
async def sync_tasks():
    """
    Manual sync trigger for Google Sheet → Tasks
    """
    try:
        google_api = os.getenv("GOOGLE_API_URL")
        if not google_api:
            return {"ok": False, "error": "GOOGLE_API_URL not set"}

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                google_api,
                json={"action": "sync_tasks"},
                timeout=30
            ) as response:
                if response.status == 200:
                    return {"ok": True}

        return {"ok": False, "error": "Sync failed"}
    except Exception as e:
        log_error(f"SYNC ERROR: {e}")
        return {"ok": False, "error": str(e)}
