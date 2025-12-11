import os
import requests
from dotenv import load_dotenv

# ----------------------------------------
# Load environment variables
# ----------------------------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in environment variables.")

TG_SEND_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TG_EDIT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"


# ----------------------------------------
# Send Message (MAIN FUNCTION)
# ----------------------------------------
def send_message(chat_id, text, reply_markup=None):
    """
    Sends a Telegram message.
    Supports Markdown + Inline/Reply keyboards.
    """
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(TG_SEND_URL, json=payload)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ----------------------------------------
# Edit message (optional but useful)
# ----------------------------------------
def edit_message(chat_id, message_id, new_text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "Markdown"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(TG_EDIT_URL, json=payload)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ----------------------------------------
# Utility: log to console
# ----------------------------------------
def log(message: str):
    """Simple console log."""
    print(f"[LOG] {message}")


# ----------------------------------------
# Utility: extract chat_id & text safely
# ----------------------------------------
def extract_message(update: dict):
    """
    Safely extracts chat_id, text, message_id
    from any Telegram update (text, buttons, etc.)
    """
    if "message" in update:
        msg = update["message"]
        return msg["chat"]["id"], msg.get("text"), msg.get("message_id")

    if "callback_query" in update:
        cq = update["callback_query"]
        return cq["message"]["chat"]["id"], cq["data"], cq["message"]["message_id"]

    return None, None, None
