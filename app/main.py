import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

import asyncio
from fastapi import FastAPI, Request

from bot.handler import process_update
from scheduler.job import scheduler_loop   # ←← اضافه شد


app = FastAPI()


# -------------------------------------------------
#   STARTUP → اجرای Scheduler
# -------------------------------------------------
@app.on_event("startup")
async def start_scheduler():
    print("⚡ Scheduler started…")
    asyncio.create_task(scheduler_loop())   # ← شیدولر را در پس‌زمینه اجرا کن


# -------------------------------------------------
#   TELEGRAM WEBHOOK ENDPOINT
# -------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        print("CHAT_ID =", data.get("message", {}).get("chat", {}).get("id"))

        # چون process_update async نیست → await نمی‌خواد
        process_update(data)

    except Exception as e:
        print("WEBHOOK ERROR:", str(e))

    return {"ok": True}


# -------------------------------------------------
#     ROOT CHECK
# -------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "Clever Roadmap Bot Running",
        "version": "1.0.0",
        "scheduler": "active"
    }
