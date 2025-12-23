# app/bot/handler.py
# -*- coding: utf-8 -*-

from cachetools import TTLCache

from bot.helpers import send_message, send_buttons, send_reply_keyboard
from bot.keyboards import main_keyboard, team_inline_keyboard

from core.members import find_member, save_or_add_member
from core.tasks import (
    get_tasks_today,
    get_tasks_next_7_days,   # <-- جدید
    get_tasks_not_done,
    update_task_status,
    format_task_block,
    group_tasks_by_date,
)
from core.messages import get_welcome_message

processed_updates = TTLCache(maxsize=20000, ttl=600)

def _action_buttons(task_id: str):
    return [
        [{"text": "تحویل دادم ✅", "callback_data": f"done|{task_id}"}],
        [{"text": "تحویل ندادم ⏰", "callback_data": f"notyet|{task_id}"}],
    ]

async def send_daily(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return

    tasks = await get_tasks_today(member["team"])
    if not tasks:
        await send_message(chat_id, "✅ امروز تسکی نداری")
        return

    await send_message(chat_id, f"🌅 <b>کارهای امروز ({len(tasks)}):</b>")
    for t in tasks:
        await send_buttons(chat_id, format_task_block(t), _action_buttons(t["task_id"]))

async def send_week(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return

    tasks = await get_tasks_next_7_days(member["team"])  # از امروز تا ۷ روز آینده
    if not tasks:
        await send_message(chat_id, "برای ۷ روز آینده تسکی نداری 👌")
        return

    # گروه‌بندی بر اساس روز
    grouped = group_tasks_by_date(tasks)
    await send_message(chat_id, f"📅 <b>کارهای ۷ روز آینده ({len(tasks)}):</b>")

    for d, items in grouped:
        day = items[0].get("day_fa", "")
        date_fa = items[0].get("date_fa", "")
        await send_message(chat_id, f"🗓️ <b>{day} | {date_fa}</b>")
        for t in items:
            await send_buttons(chat_id, format_task_block(t), _action_buttons(t["task_id"]))

async def send_not_done(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return

    tasks = await get_tasks_not_done(member["team"])
    if not tasks:
        await send_message(chat_id, "✅🔥 تسک انجام نشده‌ای نداری")
        return

    await send_message(chat_id, f"⚠️ <b>تسک‌های انجام نشده ({len(tasks)}):</b>")
    for t in tasks:
        await send_buttons(chat_id, format_task_block(t, include_delay=True), _action_buttons(t["task_id"]))

async def process_update(update: dict):
    upd_id = update.get("update_id")
    if upd_id is not None:
        if upd_id in processed_updates:
            return
        processed_updates[upd_id] = True

    # ----- Inline callbacks -----
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]

        if data.startswith("done|"):
            task_id = data.split("|", 1)[1]
            ok = await update_task_status(task_id, "Done")
            await send_message(chat_id, "✅ ثبت شد (Done)" if ok else "❌ Task پیدا نشد")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

        if data.startswith("notyet|"):
            await send_message(chat_id, "باشه ⏰")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

        if data.startswith("team|"):
            team = data.split("|", 1)[1]
            await save_or_add_member(chat_id, team=team)
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

    msg = update.get("message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    text_l = text.lower()

    user = msg.get("from", {})
    name = user.get("first_name", "کاربر")
    username = user.get("username", "")

    await save_or_add_member(chat_id, name=name, username=username)
    member = await find_member(chat_id)

    if text_l == "/start":
        if member and not member.get("welcomed"):
            welcome = await get_welcome_message(member.get("customname") or name)
            await send_message(chat_id, welcome)

        if not member or not member.get("team"):
            await send_message(chat_id, "تیم خودت رو انتخاب کن:")
            await send_buttons(chat_id, "انتخاب تیم:", team_inline_keyboard())
        else:
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
        return

    if text == "لیست کارهای امروز":
        await send_daily(chat_id)
        return

    if text == "لیست کارهای هفته":
        await send_week(chat_id)
        return

    if text == "تسک های انجام نشده":
        await send_not_done(chat_id)
        return

    if member and member.get("team"):
        await send_reply_keyboard(chat_id, "از دکمه‌ها استفاده کن 🙂", main_keyboard())
    else:
        await send_message(chat_id, "اول /start رو بزن و تیم رو انتخاب کن 🙂")
