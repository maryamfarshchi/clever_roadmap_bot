import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from fastapi import FastAPI, Request
from bot.handler import process_update

app = FastAPI()

# -----------------------------
#   TELEGRAM WEBHOOK ENDPOINT
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    await process_update(data)
    return {"ok": True}


# -----------------------------
#        ROOT CHECK
# -----------------------------
@app.get("/")
async def root():
    return {"status": "Clever Roadmap Bot Running", "version": "1.0.0"}
