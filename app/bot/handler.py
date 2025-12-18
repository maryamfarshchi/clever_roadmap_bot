# app/bot/handler.py
# -*- coding: utf-8 -*-

from datetime import datetime
import pytz
from cachetools import TTLCache

from bot.helpers import send_message, send_buttons, send_reply_keyboard
from bot.keyboards import main_keyboard, team_inline_keyboard
from core.members import find_member, save_or_add_member
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_overdue, update_task_status
from core.messages import get_welcome_message
from core.logging import log_error

IRAN_TZ = pytz.timezone("Asia/Tehran")

# ✅ جلوگیری از پردازش دوباره یک update (retry تلگرام/مشکلات شبکه)
processed_updates = TTLCache(maxsize=10000, ttl=600)  # 10 دقیقه

def _pretty_task(t, show_delay=False):
    s = f"<b>{t['title']}</b>\n📅 {t['date_fa']} ⏰ {t['time'] or ''}"
    if show_delay and t.get("delay_days", 0) > 0:
        s += f" ({t['delay_days']} روز تاخیر)"
    return s

async def send_week(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return
    tasks = await get_tasks_week(member["team"])
    if not tasks:
        await send_message(chat_id, "برای ۷ روز آینده تسکی نداری 😎")
        return

    await send_message(chat_id, f"📅 <b>کارهای ۷ روز آینده ({len(tasks)} تسک):</b>")
    for t in tasks:
        days_left = (t["deadline"] - datetime.now(IRAN_TZ).date()).days
        days_text = " (امروز)" if days_left == 0 else f" ({days_left} روز آینده)"
        await send_message(chat_id, _pretty_task(t) + days_text)

async def send_daily(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return
    tasks = await get_tasks_today(member["team"])
    if not tasks:
        await send_message(chat_id, "امروز تسکی نداری 👍")
        return

    await send_message(chat_id, f"🌅 <b>کارهای امروز ({len(tasks)} تسک):</b>")
    for t in tasks:
        buttons = [
            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
            [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
        ]
        await send_buttons(chat_id, _pretty_task(t), buttons)

async def send_pending(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return
    tasks = await get_tasks_overdue(member["team"])
    if not tasks:
        await send_message(chat_id, "تسک انجام نشده‌ای نداری 🔥✅")
        return

    await send_message(chat_id, f"⚠️ <b>تسک‌های انجام نشده ({len(tasks)} تسک):</b>")
    for t in tasks:
        buttons = [
            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
            [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
        ]
        await send_buttons(chat_id, _pretty_task(t, show_delay=True), buttons)

async def process_update(update: dict):
    # ✅ update_id dedupe
    upd_id = update.get("update_id")
    if upd_id is not None:
        if upd_id in processed_updates:
            return
        processed_updates[upd_id] = True

    # callback query
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]

        if data.startswith("done|"):
            task_id = data.split("|", 1)[1]
            ok = await update_task_status(task_id, "Done")
            await send_message(chat_id, "عالی! تسک انجام شد ✅" if ok else "تسک پیدا نشد! ❌")
            return

        if data.startswith("notyet|"):
            await send_message(chat_id, "اوکی ⏰")
            return

        if data.startswith("team|"):
            team = data.split("|", 1)[1]
            await save_or_add_member(chat_id, team=team)
            await send_message(chat_id, f"ثبت شد ✅ تیم شما: <b>{team}</b>")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

    # message
    if "message" not in update:
        return

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    user = msg.get("from", {})
    name = user.get("first_name", "کاربر")
    username = user.get("username", "")

    await save_or_add_member(chat_id, name=name, username=username)
    member = await find_member(chat_id)

    if text == "/start":
        if member and not member.get("welcomed"):
            welcome = await get_welcome_message(member.get("customname") or name)
            await send_message(chat_id, welcome)
        if not member or not member.get("team"):
            await send_message(chat_id, "به کدوم تیم تعلق دارید؟")
            await send_buttons(chat_id, "انتخاب تیم:", team_inline_keyboard())
        else:
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
        return

    # ✅ قانون ۲: هر کلیک => یک بار ارسال (بدون تکرار پردازش)
    if text == "لیست کارهای امروز":
        await send_daily(chat_id)
    elif text == "لیست کارهای هفته":
        await send_week(chat_id)
    elif text == "تسک های انجام نشده":
        await send_pending(chat_id)
    else:
        await send_message(chat_id, "از دکمه‌ها استفاده کن 🙂")
