from fastapi import FastAPI, Request, BackgroundTasks
from bot.handler import process_update

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    update = await request.json()
    background.add_task(process_update, update)
    return {"ok": True}
