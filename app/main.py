# app/main.py
# -*- coding: utf-8 -*-

import sys
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from fastapi import FastAPI, Request
from bot.handler import process_update  # async
from scheduler.job import run_weekly_jobs, run_daily_jobs, check_reminders  # async
from core.logging import log_error, log_info

app = FastAPI()

IRAN_TZ = pytz.timezone("Asia/Tehran")

scheduler = AsyncIOScheduler(timezone=IRAN_TZ)
scheduler.add_job(run_daily_jobs, CronTrigger(hour=8, minute=0))
scheduler.add_job(run_weekly_jobs, CronTrigger(day_of_week='sat', hour=9, minute=0))
scheduler.add_job(check_reminders, CronTrigger(hour=10, minute=0))
scheduler.start()

@app.get("/")
async def root():
    return {"ok": True}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
        await process_update(update)
        return {"ok": True}
    except Exception as e:
        log_error(f"Webhook ERROR: {e}")
        return {"ok": False}

@app.post("/run/weekly")
async def run_weekly():
    try:
        await run_weekly_jobs()
        return {"ok": True, "job": "weekly"}
    except Exception as e:
        log_error(f"WEEKLY JOB ERROR: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/run/daily")
async def run_daily():
    try:
        await run_daily_jobs()
        return {"ok": True, "job": "daily"}
    except Exception as e:
        log_error(f"DAILY JOB ERROR: {e}")
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
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(os.getenv("GOOGLE_API_URL"), json={"action": "sync_tasks"}) as response:
                if response.status == 200:
                    return {"ok": True}
        return {"ok": False}
    except Exception as e:
        log_error(f"SYNC ERROR: {e}")
        return {"ok": False, "error": str(e)}
