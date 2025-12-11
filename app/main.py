# app/main.py

import sys
import os

# اضافه کردن دایرکتوری فعلی به PATH
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from fastapi import FastAPI, Request
from bot.handler import process_update

app = FastAPI()


# ---------------------------------------------------
#                  WEBHOOK FROM TELEGRAM
# ---------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    # process_update تابع sync است، پس نباید await شود
    process_update(data)

    return {"ok": True}


# ---------------------------------------------------
#                     HEALTH CHECK
# ---------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "Clever Roadmap Bot Running",
        "version": "1.0.0"
    }
