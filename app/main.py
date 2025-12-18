# app/main.py
# -*- coding: utf-8 -*-

import sys
import os
import pytz

from fastapi import FastAPI, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# برای import درست ماژول‌های داخلی
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from bot.handler import process_update  # async
from scheduler.job import run_weekly_jobs, run_daily_jobs, check_reminders  # async
from core.logging import log_error, log_info

# --------------------------------------------------
# FastAPI App
# --------------------------------------------------
app = FastAPI()

# --------------------------------------------------
# Timezone
# --------------------------------------------------
IRAN_TZ = pytz.timezone("Asia/Tehran")

# --------------------------------------------------
# Scheduler
# --------------------------------------------------
scheduler = AsyncIOScheduler(timezone=IRAN_TZ)

# روزانه 08:00 → برای همه اعضا بر اساس تیم: تسک‌های امروز
scheduler.add_job(
    run_daily_jobs,
    CronTrigger(hour=8, minute=0),
    id="daily_jobs",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=300
)

# شنبه 09:00 → برای همه اعضا بر اساس تیم: تسک‌های ۷ روز آینده
scheduler.add_job(
    run_weekly_jobs,
    CronTrigger(day_of_week="sat", hour=9, minute=0),
    id="weekly_jobs",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=300
)

# روزانه 10:00 → یادآوری‌ها (2 روز مانده، ددلاین، تاخیر، هشدار مدیر)
scheduler.add_job(
    check_reminders,
    CronTrigger(hour=10, minute=0),
    id="reminders_jobs",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=300
)

# ✅ جلوگیری از دوبار start شدن روی Render (multi import / multi worker)
if not scheduler.running:
    scheduler.start()
    log_info("Scheduler started ✅")

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
# Manual triggers (Debug/Admin)
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
    Manual trigger to sync Time Sheet -> Tasks (Google Apps Script action=sync_tasks)
    """
    try:
        google_api = os.getenv("GOOGLE_API_URL", "").strip()
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
                return {"ok": False, "error": f"sync failed: {response.status}"}
    except Exception as e:
        log_error(f"SYNC ERROR: {e}")
        return {"ok": False, "error": str(e)}
