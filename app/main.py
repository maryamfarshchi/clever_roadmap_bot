import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from bot.handler import process_update

app = FastAPI()

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    await process_update(data)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "Clever Roadmap Bot running"}
