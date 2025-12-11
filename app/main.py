import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from fastapi import FastAPI, Request
from bot.handler import process_update   # مهم: این تابع sync است، async نیست

app = FastAPI()


# -------------------------------------------------
#   TELEGRAM WEBHOOK ENDPOINT 100% SAFE & CLEAN
# -------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        print("CHAT_ID =", data.get("message", {}).get("chat", {}).get("id"))

        # چون تابع async نیست، await حذف شد
        process_update(data)

    except Exception as e:
        print("WEBHOOK ERROR:", str(e))

    # همیشه پاسخ موفق
    return {"ok": True}



# -------------------------------------------------
#     ROOT CHECK
# -------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "Clever Roadmap Bot Running",
        "version": "1.0.0",
        "mode": "production"
    }
