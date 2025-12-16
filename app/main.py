# app/main.py
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from fastapi import FastAPI, Request

from bot.handler import process_update
from scheduler.job import run_weekly_jobs, run_daily_jobs

app = FastAPI()

# WEBHOOK ENDPOINT (POST + GET برای تست)
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        process_update(data)
    except Exception as e:
        print("WEBHOOK ERROR:", str(e))
    return {"ok": True}

@app.get("/webhook")
async def webhook_get():
    return {"status": "Webhook endpoint active", "method": "GET"}

# JOB: اجرای هفتگی
@app.post("/run/weekly")
async def run_weekly():
    try:
        run_weekly_jobs()
        return {"ok": True, "job": "weekly"}
    except Exception as e:
        print("WEEKLY JOB ERROR:", e)
        return {"ok": False, "error": str(e)}

# JOB: اجرای روزانه
@app.post("/run/daily")
async def run_daily():
    try:
        run_daily_jobs()
        return {"ok": True, "job": "daily"}
    except Exception as e:
        print("DAILY JOB ERROR:", e)
        return {"ok": False, "error": str(e)}

# ROOT CHECK
@app.get("/")
async def root():
    return {
        "status": "Clever Roadmap Bot Running",
        "version": "1.0.0",
        "mode": "production",
    }
